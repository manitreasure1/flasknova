from __future__ import annotations

from dataclasses import asdict

from pydantic import BaseModel
from typing import Any


class Serializer:
    """
    return the shape the obj based on
    fields provide, if extra it will be ignored,
    if field not found ValidationError or ValueError will be raise
    """

    def __init__(self, result: Any, response: dict[str, Any]) -> None:
        self.result = result
        self.response = response

    def _base_model(self) -> dict[str, Any]:
        v: BaseModel = self.response["object"](**self.result.model_dump())  # type: ignore[attr-defined]
        rv: dict[str, Any] = v.model_validate(self.result).model_dump()
        return rv

    def _dataclass(self) -> dict[str, Any]:
        result = self._serializer_checker(self.response["object"], asdict(self.result))  # type: ignore
        return result

    def _custom_class(self) -> dict[str, Any]:
        result = self._serializer_checker(
            self.response["object"],
            self.result.__result_values__,  # type: ignore[attr-defined]
        )
        return result

    def serialize(self) -> dict[str, Any] | None:
        match self.response["type"]:
            case "basemodel":
                return self._base_model()
            case "dataclass":
                return self._dataclass()
            case "customclass":
                return self._custom_class()
            case _:
                return None

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
