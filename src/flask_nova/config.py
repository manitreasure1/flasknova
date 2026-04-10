from typing import Any, TypedDict


class SPA_CONFIG_DEV(TypedDict, total=False):
    minify: bool
    source_map: bool
    watch: bool


class SPA_CONFIG_PROD(TypedDict, total=False):
    minify: bool
    source_map: bool
    watch: bool


class SPA_HOT_RELOAD_CONFIG(TypedDict, total=False):
    paths: str | list[str]
    output_dir: str
    interval: float
    auto_start: bool


class OPENAPI_INFO_CONFIG(TypedDict, total=False):
    title: str
    version: str
    description: str
    termsOfService: str
    contact: dict[str, str]
    license: dict[str, str]


class EXTERNAL_DOCS_CONFIG(TypedDict, total=False):
    description: str
    url: str


class SERVER_VARIABLE_CONFIG(TypedDict, total=False):
    default: str
    description: str
    enum: list[str]


class SERVER_CONFIG(TypedDict, total=False):
    url: str
    description: str
    variables: dict[str, SERVER_VARIABLE_CONFIG]


class SECURITY_SCHEME_CONFIG(TypedDict, total=False):
    type: str
    description: str
    name: str
    scheme: str
    bearerFormat: str
    openIdConnectUrl: str
    flows: dict[str, Any]


class OPENAPI_CONFIG(TypedDict, total=False):
    openapi_info: OPENAPI_INFO_CONFIG
    json_schema_dialect: str
    external_docs: EXTERNAL_DOCS_CONFIG
    servers: list[SERVER_CONFIG]
    security_schemes: dict[str, SECURITY_SCHEME_CONFIG]
    global_security: list[dict[str, list[str]]]


__all__ = [
    "SPA_CONFIG_DEV",
    "SPA_CONFIG_PROD",
    "SPA_HOT_RELOAD_CONFIG",
    "OPENAPI_INFO_CONFIG",
    "EXTERNAL_DOCS_CONFIG",
    "SERVER_VARIABLE_CONFIG",
    "SERVER_CONFIG",
    "SECURITY_SCHEME_CONFIG",
    "OPENAPI_CONFIG",
]