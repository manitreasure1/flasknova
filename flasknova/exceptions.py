from typing import Optional

ERROR_STATUS_TYPE_MAP = {
    400: ("https://httpstatuses.com/400", "Bad Request"),
    401: ("https://httpstatuses.com/401", "Unauthorized"),
    403: ("https://httpstatuses.com/403", "Forbidden"),
    404: ("https://httpstatuses.com/404", "Not Found"),
    405: ("https://httpstatuses.com/405", "Method Not Allowed"),
    409: ("https://httpstatuses.com/409", "Conflict"),
    422: ("https://httpstatuses.com/422", "Unprocessable Entity"),
    500: ("https://httpstatuses.com/500", "Internal Server Error"),
    501: ("https://httpstatuses.com/501", "Not Implemented"),
    502: ("https://httpstatuses.com/502", "Bad Gateway"),
    503: ("https://httpstatuses.com/503", "Service Unavailable"),
}


class HTTPException(Exception):
    def __init__(
        self,
        status_code: int,
        detail: str,
        title: Optional[str] = None,
        type_: Optional[str] = None,
        instance: Optional[str] = None
    ):
        self.status_code = status_code
        self.detail = detail
        default_type, default_title = ERROR_STATUS_TYPE_MAP.get(status_code, ("about:blank", "HTTP Error"))
        self.type = type_ or default_type
        self.title = title or default_title
        self.instance = instance



class ResponseValidationError(HTTPException):
    def __init__(self, detail, original_exception=None, instance: Optional[str] = None):
        super().__init__(
            status_code=500,
            detail=detail,
            title="Response Validation Error",
            type_="https://httpstatuses.com/500",
            instance=instance,
        )
        self.original_exception = original_exception
