class ParamBase:
    """
    Base class for parameter descriptors like Query, Header, etc.

    Args:
        default (Any): The default value if the parameter is missing.
        alias (str, optional): Alternative name to extract the value from the request.
        in_ (str, optional): Source of the parameter. Must be one of: 'query', 'header', 'cookie', 'form', 'file'.
        required (bool, optional): Whether the parameter is required. Defaults to True unless a default is provided.
        description (str, optional): Human-readable description, used in Swagger or other docs.
        examples (dict or list, optional): Example values to aid documentation or validation.
        type_ (type, optional): The expected type (if not inferred from annotation).
    """
    ...

class Query(ParamBase):
    """
    Describes a query parameter in the request URL.

    Typically used via `Annotated`:
        name: Annotated[str, Query(description="User name")]

    All parameters are inherited from ParamBase.
    """


class Form(ParamBase):
    """
    Describes a form field submitted via multipart/form-data or application/x-www-form-urlencoded.

    Can also support file uploads if `type_` is set to `UploadFile`.

    Used with Annotated:
        username: Annotated[str, Form(description="Login username")]

    Inherits all parameters from ParamBase.
    """


class Header(ParamBase):
    """
    Describes a parameter extracted from the HTTP headers.

    Header names are case-insensitive. If `alias` is not set, the variable name is used.

    Example:
        token: Annotated[str, Header(description="Auth token")]

    Inherits all parameters from ParamBase.
    """

class Cookie(ParamBase):
    """
    Describes a parameter extracted from HTTP cookies.

    Example:
        session_id: Annotated[str, Cookie(description="User session cookie")]

    Inherits all parameters from ParamBase.
    """
class File(ParamBase):
    """
    Describes an uploaded file field in a multipart/form-data request.

    You can optionally specify:
        - type_: to be a file-like type or UploadFile.
        - description: to show in docs.

    Example:
        file: Annotated[UploadFile, File(description="Upload document")]

    Inherits all parameters from ParamBase.
    """
class Param(ParamBase):
    """
    Flexible parameter descriptor for any kind of request input.

    Behaves like a smart dispatcher that can extract from query, header, form, cookie, or file based on `in_`.

    Example:
        id: Annotated[int, Param(in_="query", description="User ID")]

    Inherits all parameters from ParamBase.
    """

class ParamModel:
    """
    Base class for defining grouped request parameters via models.

    Accepts models defined using:
        - `pydantic.BaseModel`
        - `dataclasses`
        - Plain Python classes with type hints and `to_dict()`.

    Each attribute can use `Annotated[type, Query/Form/Header/etc]` to explicitly control source.

    Example:
        class AuthForm:
            username: Annotated[str, Form()]
            password: Annotated[str, Form()]
            token: Annotated[str, Header()]
            debug: Annotated[bool, Query(default=False)]

    Used as:
        def login(data: Annotated[AuthForm, ParamModel()]): ...
    """
