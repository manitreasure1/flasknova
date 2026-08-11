from __future__ import annotations

from functools import wraps
import inspect as ip
import typing as t

from .exceptions import HTTPException
from .status import status
from .di import Depend

from werkzeug.exceptions import UnsupportedMediaType, BadRequest
from werkzeug.datastructures import FileStorage
from pydantic import ValidationError
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
    ):
        kind: str = self.field_obj["type"]
        obj: type = self.field_obj["object"]
        default: type | None = self.field_obj.get("default")

        try:
            match kind:
                case "dataclass":
                    return obj(**self._json_request())
                case "customclass":
                    return self.__make_attr(self._json_request())
                case "basemodel":
                    return obj(self._json_request())
                case "query":
                    return self._query_request()
                case "path":
                    return self._path_request()
                case "dataclassform":
                    return obj(**self._form_request())
                case "basemodelform":
                    return obj.model_validate(self._form_request())
                case "customclassform":
                    return self.__make_attr(self._form_request())
                case "file":
                    return self._file_request()
                case "form":
                    return self._form_request()
                case "dependency":
                    return self.resolve_dependencies(default)
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

    def _query_request(self) -> str | None:
        return self.request.args.get(self.field_name)

    def _path_request(self):
        return self.request.view_args.get(self.field_name)

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
        if self.field_obj["default"].multiple:
            file_obj = self.request.files.getlist(self.field_obj["default"].name)
        else:
            file_obj = self.request.files.get(self.field_obj["default"].name)  # type: ignore[assignment]
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

        @wraps(dep_func)
        def resolver():
            if ip.iscoroutinefunction(dep_func):
                raise AttributeError(
                    f"Depend: cannot execute awaitable function `{dep_func.__name__}`"
                )
            return dep_func()

        return resolver()
