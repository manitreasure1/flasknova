from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel, ValidationError
from typing import Any
from .status import status
from .exceptions import HTTPException


class Serializer:
    """
    **response dispatcher** class for serializing objects,
    support `pydantic`, `dataclass`, and class with :attr: `to_dict`
    """

    def __init__(self, result: Any, response: dict[str, type | str]) -> None:
        self.result = result
        self.response = response

    def _base_model(self) -> dict[str, Any]:
        if isinstance(self.result, dict):
            v: BaseModel = self.response["object"](**self.result)  # type: ignore[operator]
        else:
            v = self.response["object"](**self.result.model_dump())  # type: ignore[operator]
        rv = v.model_validate(self.result).model_dump()

        return rv

    def _dataclass(self) -> dict[str, Any]:
        if isinstance(self.result, dict):
            result = self.response["object"](**self.result)  # type: ignore[operator]
        else:
            result = self._serializer_checker(self.response["object"], asdict(self.result))  # type: ignore
        return result

    def _custom_class(self) -> dict[str, Any]:
        if isinstance(self.result, dict):
            result = self.response["object"](**self.result)  # type: ignore[operator]
        else:
            result = self._serializer_checker(
                self.response["object"],  # type: ignore[arg-type]
                self.result.__result_values__,  # type: ignore[attr-defined]
            )
        return result

    def serialize(self) -> dict[str, Any] | None: # type: ignore[return]
        try:
            match self.response["type"]:
                case "basemodel":
                    return self._base_model()
                case "dataclass":
                    return self._dataclass()
                case "customclass":
                    return self._custom_class()
        except ValidationError as e:
            raise HTTPException(
                status_code=status.INTERNAL_SERVER_ERROR,
                detail=f"Serialization failed: {e.errors(include_url=False)}",
                title="Internal Server Error",
            )
        except (AttributeError, TypeError, ValueError) as e:
            raise HTTPException(
                status_code=status.UNPROCESSABLE_ENTITY,
                detail=f"Serialization failed: {e}",
                title="Internal Server Error",
            )

    def _serializer_checker(self, cls: type, result: dict) -> dict[str, Any]:
        """
        This return the fields in the :param:`cls` given a :param:`result`
        and will raise `ValueError` if field is not found in :param:`result`

        """
        keys = cls.__annotations__.items()
        return_odj: dict[str, Any] = {}
        for field_name, _ in keys:
            if field_name not in result.keys():
                raise ValueError(f"{cls.__name__} expect {field_name} field")
            return_odj[field_name] = result[field_name]
        return return_odj
