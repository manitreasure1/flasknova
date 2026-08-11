import http


class HTTPException(Exception):
    """Application exception rendered as an RFC 7807 problem response.

    Args:
        status_code: HTTP status code returned to the client.
        detail: Human-readable explanation of the specific error.
        title: Short, human-readable summary. Defaults to the HTTP status phrase.
        type_: URI identifying the problem type.
        instance: URI identifying the specific occurrence of the problem.
        extensions: Additional problem fields included in the JSON response.
    """

    def __init__(
        self,
        status_code: int,
        detail: None | str | list = None,
        title: str | None = None,
        type_: None | str = None,
        instance: str | None = None,
        **extensions: dict | None,
    ) -> None:
        _status = http.HTTPStatus(status_code)

        self.status_code = status_code
        self.detail = detail
        self.title: str = title or _status.phrase
        self.type: str = type_ or f"https://httpstatuses.com/{status_code}"
        self.instance: str | None = instance
        self.extensions = extensions

    def __str__(self) -> str:
        return f"{self.status_code}: {self.detail}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code})"
