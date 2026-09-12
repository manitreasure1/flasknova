from __future__ import annotations

from functools import wraps
import inspect as ip
import typing as t

from .exceptions import HTTPException
from .status import status
from .di import Depend

from werkzeug.exceptions import UnsupportedMediaType, BadRequest
from werkzeug.datastructures import FileStorage
from pydantic import ValidationError, TypeAdapter
from pydantic.fields import FieldInfo
from flask import Request


class Binder:
    def __init__(
        self, field_name: str, field_obj: dict[str, t.Any], request: Request
    ) -> None:
        self.field_name = field_name
        self.field_obj = field_obj
        self.request = request

    def make_request(
        self,
    ) -> type | str | list[FileStorage] | FileStorage | dict[str, str] | None:

        kind: str = self.field_obj["type"]
        obj: type | None = self.field_obj.get("object")
        default: type | None = self.field_obj.get("default")

        try:
            match kind:
                case "dataclass":
                    return obj(**self._json_request())  # type: ignore[misc]
                case "customclass":
                    return self.__make_attr(self._json_request())
                case "basemodel":
                    return obj(**self._json_request())  # type: ignore[misc]
                case "query":
                    return self._query_request(obj, default)
                case "path":
                    return self._path_request(obj, default)
                case "dataclassform":
                    return obj(**self._form_request())  # type: ignore[misc]
                case "basemodelform":
                    return obj.model_validate(self._form_request())  # type: ignore[union-attr]
                case "customclassform":
                    return self.__make_attr(self._form_request())
                case "file":
                    return self._file_request()
                case "form":
                    return self._form_request()
                case "dependency":
                    return self.resolve_dependencies(default)  # type: ignore[arg-type]
                case _:
                    return None
        except TypeError as e:
            raise HTTPException(
                status_code=status.UNPROCESSABLE_ENTITY,
                detail=f"Binding failed: {e}",
                title="Form Validation Error",
            )
        except ValidationError as e:
            raise HTTPException(
                status_code=status.UNPROCESSABLE_ENTITY,
                detail=f"Binding failed: {e.errors(include_url=False)}",
                title="Form Validation Error",
            )

    def _query_request(self, obj: type | None, default: type | None) -> str | None:
        query = self.request.args.get(self.field_name)
        return self._validate_param(obj, default, query)

    def _path_request(self, obj: type | None, default: type | None):
        if self.request.view_args:
            path = self.request.view_args.get(self.field_name)
            return self._validate_param(obj, default, path)

    def _json_request(self) -> dict[t.Any, t.Any]:
        # ! `force=True` handle content type validation
        json_data: dict[t.Any, t.Any] = {}
        try:
            json_data = self.request.get_json(force=True)
        except UnsupportedMediaType:
            raise HTTPException(
                status_code=status.UNSUPPORTED_MEDIA_TYPE,
                title="UNSUPPORTED_MEDIA_TYPE",
                detail="Expected JSON for this model, but received unsupported content type.",
            )
        except BadRequest as e:
            raise HTTPException(
                status_code=status.BAD_REQUEST,
                title="Cannot handle Request",
                detail=str(e),
            )

        return json_data

    def _form_request(self) -> dict[str, str]:
        if not self.request.content_type or not any(
            self.request.content_type.startswith(t)
            for t in [
                "multipart/form-data",
                "application/x-www-form-urlencoded",
            ]
        ):
            raise HTTPException(
                title="Unsupported Media Type",
                status_code=status.UNSUPPORTED_MEDIA_TYPE,
                detail="The endpoint expects form data, but the request has an incorrect content type.",
            )
        form_data = self.request.form.to_dict(flat=True)
        if not form_data:
            raise HTTPException(
                status_code=status.UNPROCESSABLE_ENTITY,
                detail="Empty form data. Ensure the request includes fields and uses the correct Content-Type.",
                title="Empty Form Submission",
            )
        return form_data

    def _file_request(
        self,
    ) -> list[FileStorage] | FileStorage | None:

        name: str = self.field_obj["default"].name or self.field_name
        content_type: str = self.field_obj["default"].content_type
        file_obj: list[FileStorage] | FileStorage | None = None

        if content_type:
            if not self.request.content_type.startswith(content_type):
                raise HTTPException(
                    status_code=status.UNSUPPORTED_MEDIA_TYPE,
                    detail=f"The endpoint expects `{content_type}` Content-Type, but the request has an incorrect content type.",
                )
        elif not self.request.content_type or not any(
            self.request.content_type.startswith(t)
            for t in [
                "multipart/form-data",
                "application/octet-stream",
            ]
        ):
            raise HTTPException(
                status_code=status.UNSUPPORTED_MEDIA_TYPE,
                detail="The endpoint expects binary file data, but the request has an incorrect content type.",
            )
        if self.field_obj["default"].multiple:
            file_obj = self.request.files.getlist(name)
        else:
            file_obj = self.request.files.get(name)
        if not file_obj:
            raise HTTPException(
                status_code=status.UNPROCESSABLE_ENTITY,
                title="Empty File Submission",
            )
        return file_obj

    def __make_attr(self, obj_dict: dict) -> type:
        def app_int(*args, **kwags): ...

        _items = {}
        self.field_obj["object"].__init__ = app_int  # type: ignore[misc]
        fields = tuple(self.field_obj["object"].__annotations__.keys())
        for f in fields:
            _items[f] = obj_dict[f]
            setattr(self.field_obj["object"], f, obj_dict[f])
        self.field_obj["object"].__result_values__ = _items
        return self.field_obj["object"]

    def resolve_dependencies(self, dependency: Depend):
        dep_func = dependency.dependency

        if ip.iscoroutinefunction(dep_func):

            @wraps(dep_func)
            async def resolve_async():
                return await dep_func()

            return resolve_async()
        else:

            @wraps(dep_func)
            def resolve_sync():
                return dep_func()

            return resolve_sync()

    def _validate_param(self, obj: type | None, default: type | None, raw_input: t.Any):

        if obj and isinstance(default, FieldInfo):
            annotated_type = t.Annotated[obj, default] #type: ignore[valid-type]
            validator = TypeAdapter(annotated_type)
            try:
                return validator.validate_python(raw_input)
            except ValidationError as err:
                raise HTTPException(
                    status_code=status.UNPROCESSABLE_ENTITY,
                    detail=f"Validation Error: {err.errors(include_url=False)}",
                    title="Parameter Validation Error",
                )
        else:
            return raw_input
