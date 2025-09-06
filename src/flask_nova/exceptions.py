from typing import Optional
import http


class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: Optional[str|list]= None,
        title: Optional[str] = None,
        type_: Optional[str] = None,
        instance: Optional[str] = None
    ):
        
        http_status = http.HTTPStatus(status_code)
        self.status_code = status_code
        self.detail = detail or http_status.phrase
        self.title = title or http_status.phrase
        self.type = type_ or f"https://httpstatuses.com/{status_code}"
        self.instance = instance

    def __str__(self) -> str:
           return f"{self.status_code}: {self.detail}"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code!r}, detail={self.detail!r})"



class ResponseValidationError(HTTPException):
    def __init__(self, detail, original_exception=None, instance: Optional[str] = None):
        super().__init__(
            status_code=500,
            detail=detail,
            instance=instance,
            title="Response Validation Error",
            type_="https://httpstatuses.com/500",
        )
        self.original_exception = original_exception



