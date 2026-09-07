"""Helpful Cli to simplify wrokflow
.http and .py file generator
detail info renderer
"""

from __future__ import annotations

from datetime import timedelta
import typing as t

from urllib.parse import urlencode
from uuid import UUID, uuid4
import importlib.metadata
from pathlib import Path
import collections
import webbrowser
import importlib
import tempfile
import random
import click
import types
import json
import sys
import re


def map_obj_data(
    obj,
):
    """takes :param:`obj` of python type and return random object value"""

    origin = t.get_origin(obj)
    args = t.get_args(obj)

    if obj is int:
        return random.randint(1000, 9999)
    if obj is float:
        return random.random()
    if obj is bool:
        return True
    if obj is UUID:
        return str(uuid4())
    if origin is dict:
        return {"key": "value"}

    if origin in (list, t.Union, types.UnionType):
        return map_obj_data(args[0]) if args else "string"
    return random.choice(["string", "value", "str-obj"])


def _generate(
    app_obj,
):
    requests = []

    for method, meta_obj in app_obj._compiled_validators.items():
        for original_url, url_obj in meta_obj.items():

            body: dict | str | None = None
            content_type: str = ""
            url = url = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"", original_url)

            query_param = {}
            _static_url_path: str = (
                app_obj.static_url_path if app_obj.static_url_path else "static"
            )

            docs_url = ["/docs", "/openapi", "/redoc", "/swagger", _static_url_path]
            swagger_url = app_obj.config.get("FLASKNOVA_SWAGGWER_ROUTE", None)
            redoc_url = app_obj.config.get("FLASKNOVA_REDOC_ROUTE", None)
            scalar_url = app_obj.config.get("FLASKNOVA_SCALAR_ROUTE", None)
            if swagger_url:
                docs_url.append(swagger_url)
            if redoc_url:
                docs_url.append(redoc_url)
            if scalar_url:
                docs_url.append(scalar_url)

            if not original_url in docs_url:
                for name, req_obj in (url_obj.get("request") or {}).items():
                    _obj_ = req_obj.get("object")
                    _type_: str = req_obj["type"]

                    if _type_ == "query":
                        query_param[name] = map_obj_data(_obj_)

                    if hasattr(_obj_, "__annotations__"):
                        body = {}
                        body.update(
                            {
                                field_name: map_obj_data(field_type)
                                for field_name, field_type in _obj_.__annotations__.items()
                            }
                        )

                        if _type_ in ("basemodel", "dataclass", "customclass"):
                            content_type = "application/json"

                        elif _type_ in (
                            "basemodelform",
                            "dataclassform",
                            "customclassform",
                            "form",
                        ):
                            content_type = "application/x-www-form-urlencoded"
                    if _type_ == "file":
                        content_type = f"multipart/form-data"

                        body = f"--WebkitFormBoundary\n Content-Disposition: form-data; name='{req_obj['default'].name or name}' filename= ''\n Content-type: {content_type}\n\n < ./../.\n --WebkitFormBoundary--"
                if query_param:
                    url = url + "?" + urlencode(query_param)
                requests.append(
                    {
                        "method": method,
                        "body": body,
                        "url": url.replace("//", "/"),
                        "content_type": content_type,
                        "endpoint": f"{method.lower()}_{re.sub(r"[/{} -]", '_', url.strip('/'))}",
                    }
                )
    return requests


def _generate_http_file(
    app_obj,
    app_name: str,
    base_url: str,
    output_path: Path,
):
    """takes and build each route meta, and write to http file"""

    _file = output_path / f"{app_name}_request.http"
    lines = [f"@base_url = {base_url}", "\n\n###"]

    requests = _generate(app_obj)
    for request in requests:
        url = "{{base_url}}" + request["url"]
        lines.append(f"{request['method']} {url}")

        if request["content_type"]:
            lines.append(f"Content-Type: {request["content_type"]}\n")

        if type(request["body"]) is str:
            lines.append(request["body"])
        else:
            if request["content_type"] == "application/x-www-form-urlencoded":
                lines.append(urlencode(request["body"]))
            else:
                lines.append(json.dumps(request["body"], indent=4))
        lines.append("\n###")
    _file.write_text("\n".join(lines), encoding="utf_8")
    click.echo(f"Generated HTTP requests in {_file}")


def _generate_py_file(
    app_obj,
    app_name: str,
    base_url: str,
    output_path: Path,
):
    """takes and build each route meta, and write to python file"""
    _file = output_path / f"{app_name}_request.py"

    requests = _generate(app_obj)
    lines: list[str] = [
        "import json",
        "import urllib.request\n\n",
        f"base_url = {base_url!r}",
        "",
    ]

    for request in requests:
        endpoint = (
            request["endpoint"].split("?")[0]
            if "?" in request["endpoint"]
            else request["endpoint"]
        )

        lines.append(f"def test_{endpoint}() -> None:")
        lines.append(f"\turl = base_url + {request['url']!r}")

        if request["body"] and type(request["body"]) is not str:
            lines.append(f"\tdata = json.dumps({request['body']!r}).encode()")
            lines.append(
                f"\trequest = urllib.request.Request(url, data=data, method={request['method']!r})"
            )
            lines.append(
                f"\trequest.add_header('Content-Type', {request['content_type']!r})"
            )
        else:
            lines.append(
                f"\trequest = urllib.request.Request(url, method={request['method']!r})"
            )
            lines.append(
                f"\trequest.add_header('Content-Type', {request['content_type']!r})"
            )
        lines.append("\twith urllib.request.urlopen(request) as response: ...")

        lines.append("")
    _file.write_text("\n".join(lines), encoding="utf_8")
    click.echo(f"Generated Python requests in {_file}")


def _load_app(app: str):
    """Load an app from a ``module:attribute`` import path."""

    module_name, separator, app_name = app.partition(":")
    if not separator or not module_name or not app_name:
        raise click.UsageError(
            "--app must use the form 'module_name:app_name', "
            "for example 'model_name:app'."
        )

    current_directory = str(Path.cwd())
    if current_directory not in sys.path:
        sys.path.insert(0, current_directory)

    mod = importlib.import_module(module_name)
    try:
        return getattr(mod, app_name)
    except AttributeError as exc:
        raise click.UsageError(
            f"Application attribute {app_name!r} was not found in {module_name!r}."
        ) from exc


@click.group()
def cli() -> None:
    """
    FlaskNova Cli utilities.
    """


@cli.command()
@click.option(
    "--app",
    required=True,
    help="Your Flask app import path, e.g. 'examples.form_ex:app'.",
)
@click.option(
    "--base-url", default="http://127.0.0.1:5000", help="Base URL for requests."
)
@click.option(
    "--output", default=".", type=click.Path(path_type=Path), help="Output directory."
)
@click.option("--format", type=click.Choice(["http", "py", "all"]), default="all")
def gen(app: str, base_url: str, output: str, format: str) -> None:
    """
    Generate .http/.py request file including it request payload
    """
    app_obj = _load_app(app)
    app_name = app.rsplit(":", 1)[1]

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    if format in ("http", "all"):
        _generate_http_file(app_obj, app_name, base_url, output_path)
    if format in ("py", "all"):
        _generate_py_file(app_obj, app_name, base_url, output_path)


def _sys_info(app):
    """System info render

    versionadded 0.2.0
    """

    versions = {
        d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
    }

    safe_config = {}
    for key, value in app.config.items():
        if any(
            secret in key.upper() for secret in ["SECRET", "PASSWORD", "KEY", "TOKEN"]
        ):
            safe_config[key] = "***********"
        elif isinstance(value, timedelta):
            safe_config[key] = str(value)
        else:
            safe_config[key] = value

    blueprints = collections.deque()
    for _, blueprint in app.blueprints.items():
        if hasattr(blueprint, "_compiled_validators"):
            bp = {}
            openapi = getattr(blueprint, "openapi")

            bp["title"] = blueprint.name
            bp["urlPrefix"] = blueprint.url_prefix or ""
            bp["tags"] = openapi.get("tags") or []
            bp["paths"] = json.dumps(openapi.get("paths"))
            bp["components"] = (
                json.dumps(openapi["components"]) if openapi.get("components") else "{}"
            )
            blueprints.append(bp)
    return {
        "versions": versions,
        "config": json.dumps(safe_config),
        "blueprints": blueprints,
    }


@cli.command()
@click.option(
    "--app",
    required=True,
    help="Your Flask app import path, e.g. 'nova2.src:app'.",
)
def info(app) -> None:
    """Retrive all buleprint info and render it in your default web browser

    _**Note:**_ This provides detail info \n
    using :attr:`~NovaBlueprint._openapi`.

    versionadded 0.2.0
    """

    app_obj = _load_app(app)

    sys_info = _sys_info(app_obj)

    blueprints = list(sys_info["blueprints"])
    versions = sys_info["versions"]
    config = sys_info["config"]

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>FlaskNova Engine Diagnostics</title>

            <style>

                :root {{
                    /* System Light Palette */
                    --bg-system: #f8fafc;
                    --bg-surface: #ffffff;
                    --bg-surface-elevated: #f1f5f9;
                    --border-spec: #cbd5e1;
                    --border-focus: #64748b;

                    /* Technical Typography */
                    --text-primary: #0f172a;
                    --text-secondary: #334155;
                    --text-muted: #64748b;

                    /* HTTP Verb Badges (High Contrast Light) */
                    --http-get: #047857;
                    --http-post: #1d4ed8;
                    --http-put: #b45309;
                    --http-delete: #b91c1c;

                    /* Token & Data Type Accents */
                    --token-bool: #be123c;
                    --token-num: #0284c7;
                    --token-str: #047857;
                    --token-obj: #6b21a8;
                }}

                * {{
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }}

                body {{
                    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
                    background-color: var(--bg-system);
                    color: var(--text-primary);
                    font-size: 0.875rem;
                    line-height: 1.5;
                    letter-spacing: -0.01em;
                }}

                .container {{
                    width: 100%;
                    max-width: 1280px;
                    margin: 0 auto;
                    padding: 0 16px;
                }}

                /* Header & System Toolbar */
                .engine-header {{
                    background-color: var(--bg-surface);
                    border-bottom: 1px solid var(--border-spec);
                    position: sticky;
                    top: 0;
                    z-index: 1000;
                }}

                .navbar-core {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 10px 0;
                }}

                .engine-id {{
                    font-weight: 700;
                    color: var(--text-primary);
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}

                .engine-id span {{
                    color: var(--text-muted);
                    font-weight: 400;
                }}

                .tab-engine {{
                    display: flex;
                    gap: 4px;
                }}

                .tab-engine button {{
                    background: var(--bg-surface);
                    border: 1px solid var(--border-spec);
                    color: var(--text-secondary);
                    font-family: inherit;
                    font-size: 11px;
                    padding: 5px 12px;
                    cursor: pointer;
                    text-transform: uppercase;
                    font-weight: 600;
                    transition: all 0.1s ease;
                }}

                .tab-engine button:hover {{
                    background-color: var(--bg-surface-elevated);
                    border-color: var(--border-focus);
                    color: var(--text-primary);
                }}

                .tab-engine button.active-tab {{
                    background-color: var(--bg-surface-elevated);
                    border-color: var(--border-focus);
                    color: var(--text-primary);
                    box-shadow: inset 0 -2px 0 var(--http-post);
                }}

                .sys-matrix {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 1px;
                    background-color: var(--border-spec);
                    border-top: 1px solid var(--border-spec);
                }}

                .sys-matrix span {{
                    background-color: var(--bg-surface);
                    color: var(--text-secondary);
                    padding: 4px 10px;
                    font-size: 11px;
                    text-align: center;
                    flex: 1;
                }}

                .view-frame {{
                    padding: 24px 0;
                }}

                .hero-telemetry {{
                    margin-bottom: 20px;
                    border-left: 3px solid var(--border-focus);
                    padding-left: 12px;
                }}

                .hero-telemetry h1 {{
                    font-size: 16px;
                    font-weight: 700;
                    text-transform: uppercase;
                    margin-bottom: 2px;
                }}

                .hero-telemetry p {{
                    color: var(--text-muted);
                    font-size: 12px;
                }}

                /* Modules & Components */
                .bp-module {{
                    background-color: var(--bg-surface);
                    border: 1px solid var(--border-spec);
                    margin-bottom: 20px;
                }}

                .bp-meta-header {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    align-items: center;
                    background-color: var(--bg-surface-elevated);
                    padding: 8px 14px;
                    border-bottom: 1px solid var(--border-spec);
                }}

                .bp-title {{
                    font-size: 12px;
                    font-weight: 700;
                    letter-spacing: 0.03em;
                }}

                .prefix-token {{
                    background-color: #eff6ff;
                    color: var(--http-post);
                    border: 1px solid #bfdbfe;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-weight: 600;
                }}

                .scope-tags {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 6px;
                    padding: 8px 14px;
                    background-color: var(--bg-system);
                    border-bottom: 1px solid var(--border-spec);
                }}

                .scope-node {{
                    font-size: 11px;
                    color: var(--text-muted);
                    border: 1px dashed var(--border-spec);
                    background: var(--bg-surface);
                    padding: 1px 6px;
                }}

                .route-registry {{
                    padding: 12px;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }}

                .route-node {{
                    border: 1px solid var(--border-spec);
                    background-color: var(--bg-surface);
                }}

                .route-wireframe {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-between;
                    align-items: center;
                    padding: 8px 12px;
                    background-color: var(--bg-surface-elevated);
                    border-bottom: 1px solid var(--border-spec);
                }}

                .method-block {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }}

                .http-verb {{
                    font-size: 10px;
                    font-weight: 700;
                    padding: 2px 6px;
                    color: #ffffff;
                    min-width: 52px;
                    text-align: center;
                    letter-spacing: 0.05em;
                }}

                .http-verb.get {{ background-color: var(--http-get); }}
                .http-verb.post {{ background-color: var(--http-post); }}
                .http-verb.put {{ background-color: var(--http-put); }}
                .http-verb.delete {{ background-color: var(--http-delete); }}

                .uri-path {{
                    font-weight: 700;
                    color: var(--text-primary);
                }}

                .dns-endpoint {{
                    font-size: 11px;
                    color: var(--text-muted);
                }}

                .payload-manifest {{
                    padding: 10px 12px;
                    background-color: var(--bg-system);
                }}

                .manifest-row {{
                    margin-bottom: 4px;
                    color: var(--text-secondary);
                    display: flex;
                    font-size: 12px;
                }}

                .manifest-row:last-child {{
                    margin-bottom: 0;
                }}

                .schema-info {{
                    display: none;
                }}

                .schema-info-hover {{
                    cursor: pointer;
                    display: block;
                    position: absolute;
                    z-index: 10;
                    background-color: var(--bg-surface);
                    border: 1px solid var(--border-focus);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                    width: 50%;
                    color: var(--text-primary);
                    padding: 12px;
                }}

                .manifest-key {{
                    font-weight: 600;
                    width: 140px;
                    text-transform: uppercase;
                    color: var(--text-muted);
                    font-size: 11px;
                }}

                .manifest-data {{
                    width: 100%;
                }}

                .nd {{
                    margin-top: 8px;
                }}

                .nd div {{
                    display: flex;
                    justify-content: space-around;
                }}

                .nd span {{
                    border: 1px solid var(--border-spec);
                    background: var(--bg-surface);
                    flex: 1;
                    padding: 4px;
                }}

                .config-schema {{
                    background-color: var(--bg-surface);
                    border: 1px solid var(--border-spec);
                }}

                .schema-header {{
                    background-color: var(--bg-surface-elevated);
                    padding: 8px 14px;
                    border-bottom: 1px solid var(--border-spec);
                    font-weight: 700;
                    font-size: 11px;
                    color: var(--text-muted);
                    text-transform: uppercase;
                }}

                .schema-grid {{
                    display: flex;
                    flex-direction: column;
                }}
                .schema-row {{
                    display: flex;
                    justify-content: space-between;
                    flex-wrap: wrap;
                    border-bottom: 1px solid var(--border-spec);
                    padding: 8px 14px;
                    align-items: center;
                    font-size: 12px;
                }}
                .schema-row:last-child {{
                    border-bottom: none;
                }}

                .param-key {{
                    font-weight: 600;
                    color: var(--text-primary);
                }}

                .token-boolean {{
                    color: var(--token-bool);
                    font-weight: 700;
                }}

                .token-object {{
                    color: var(--token-obj);
                    background: #f3e8ff;
                    border: 1px solid #e9d5ff;
                    padding: 1px 4px;
                }}

                .token-string {{
                    color: var(--token-str);
                }}

                .token-number {{
                    color: var(--token-num);
                }}

                .pane-state {{
                    display: none;
                }}

                .pane-state.active-frame {{
                    display: block;
                }}
            </style>
        </head>

        <body>
            <header class="engine-header">
                <div class="container navbar-core">
                    <div class="engine-id">FlaskNova <span>// Core Engine Diagnostic v0.2.0</span></div>
                    <nav class="tab-engine">
                        <button id="tab-bp" class="active-tab"
                            onclick="toggleEnginePane('blueprint')">Route_Registry</button>
                        <button id="tab-cfg" onclick="toggleEnginePane('config')">Sys_Config</button>
                    </nav>
                </div>
                <div id="sys-matx" class="sys-matrix">
                </div>
            </header>

            <main class="container view-frame">
                <section class="hero-telemetry">
                    <h1>Engine Environment Telemetry</h1>
                    <p>Runtime mapping execution data pipelines and blueprint interface definitions.</p>
                </section>

                <!-- ROUTE DICTIONARY VIEW PANEL -->
                <div id="pane-blueprint" class="pane-state active-frame">

                </div>

                <!-- CONFIG DATA MAP VIEW PANEL -->
                <div id="pane-config" class="pane-state">
                    <section class="config-schema">
                        <div class="schema-header">Application Runtime Environments Schema Mapping</div>
                        <div id="runtime-config-target" class="schema-grid">
                            <!-- Virtual injection of configuration structures via app.js -->
                        </div>
                    </section>
                </div>

            </main>

            <!-- <script src="./t.js"></script> -->

            <script>
                function toggleEnginePane(targetPane) {{
                    document.querySelectorAll('.pane-state').forEach(el => el.classList.remove('active-frame'));
                    document.querySelectorAll('.tab-engine button').forEach(el => el.classList.remove('active-tab'));

                    if (targetPane === 'blueprint') {{
                        document.getElementById('pane-blueprint').classList.add('active-frame');
                        document.getElementById('tab-bp').classList.add('active-tab');
                    }} else {{
                        document.getElementById('pane-config').classList.add('active-frame');
                        document.getElementById('tab-cfg').classList.add('active-tab');
                    }}
                }}


                const BuildSchemaRow = (key, val) => {{
                    const row = document.createElement('div');
                    row.classList.add("schema-row");

                    const keyContainer = document.createElement('span');
                    keyContainer.classList.add("param-key");
                    keyContainer.textContent = key;

                    const valContainer = document.createElement('span');

                    if (typeof val === "boolean") {{
                        valContainer.classList.add("token-boolean");
                    }} else if (typeof val === "object" && val !== null) {{
                        valContainer.classList.add("token-object");
                    }} else if (typeof val === "string") {{
                        valContainer.classList.add("token-string");
                    }} else if (typeof val === "number") {{
                        valContainer.classList.add("token-number");
                    }}

                    valContainer.textContent = typeof val === "object" ? JSON.stringify(val) : val;

                    row.appendChild(keyContainer);
                    row.appendChild(valContainer);
                    return row;
                }};

                const manifestNode = (key, data) => {{
                    const node = document.createElement('div')
                    node.classList.add('manifest-row')

                    const nodeKey = document.createElement('span')
                    nodeKey.classList.add('manifest-key')
                    nodeKey.textContent = key

                    const nodeData = document.createElement('span')
                    nodeData.textContent = data

                    node.appendChild(nodeKey)
                    node.appendChild(nodeData)
                    return node
                }}

                const schemaInfoNode = (schemaName, schema) => {{
                    const schemaInfo = document.createElement('div')
                    schemaInfo.classList.add('schema-info')

                    const infoHeader = document.createElement('header')
                    infoHeader.style.textAlign = 'center'
                    const schemaHeader = document.createElement('h2')

                    const infoBody = document.createElement('div')

                    schemaHeader.textContent = schemaName
                    infoHeader.appendChild(schemaHeader)

                    if (Object.hasOwn(schema, 'description')) {{
                        const schemaDes = document.createElement('p')
                        schemaDes.textContent = schema.description
                        infoHeader.appendChild(schemaDes)
                    }}

                    Object.entries(schema).forEach(([i, j]) => {{
                        const infoDiv = document.createElement('div')
                        infoDiv.classList.add("schema-row")

                        if (i != 'description' && i != 'title' && j !== null) {{

                            const schemaKey = document.createElement('div')
                            const schemaData = document.createElement('div')
                            schemaKey.textContent = i

                            if (Array.isArray(j)) {{
                                schemaData.classList.add("token-object");
                                schemaData.textContent = j
                            }}
                            else if (typeof j === "object") {{
                                Object.entries(j).forEach(([y, z]) => {{
                                    const yz = document.createElement('div')
                                    yz.classList.add("schema-row")

                                    const ky = document.createElement('span')
                                    const kz = document.createElement('span')
                                    kz.classList.add("token-object")
                                    ky.textContent = y
                                    kz.textContent = JSON.stringify(z)
                                    yz.appendChild(ky)
                                    yz.appendChild(kz)
                                    schemaData.appendChild(yz)
                                }})

                            }} else if (typeof j === "string") {{
                                schemaData.classList.add("token-string");
                                schemaData.textContent = j
                            }}
                            infoDiv.appendChild(schemaKey)
                            infoDiv.appendChild(schemaData)
                        }}
                        infoBody.appendChild(infoDiv)
                    }})
                    schemaInfo.appendChild(infoHeader)
                    schemaInfo.appendChild(infoBody)
                return schemaInfo
                }}


                const BuildRouteNode = (url, urlMeta, components) => {{
                    const node = document.createElement('div');
                    node.classList.add("route-node");
                    const wireframe = document.createElement('div');
                    wireframe.classList.add("route-wireframe");

                    Object.entries(urlMeta).forEach(([method, methodMeta]) => {{

                        const manifestArea = document.createElement('div');
                        manifestArea.classList.add("payload-manifest");

                        manifestArea.appendChild(manifestNode("Operation_ID:", methodMeta.operationId))

                        const hasDescription = Object.hasOwn(methodMeta, 'description')
                        const hasRequestBody = Object.hasOwn(methodMeta, 'requestBody')
                        const hasParameter = Object.hasOwn(methodMeta, 'parameters')

                        hasDescription && manifestArea.appendChild(manifestNode('Description:', methodMeta.description))

                        if (hasRequestBody) {{
                            const content = methodMeta.requestBody.content

                            Object.entries(content).forEach(([contentType, contentObj]) => {{
                                const hasSchema = Object.hasOwn(contentObj, 'schema')

                                manifestArea.appendChild(manifestNode("Content-Type:", contentType))

                                if (hasSchema && Object.hasOwn(contentObj['schema'], '$ref')) {{
                                    const schemaName = contentObj['schema']['$ref'].split('/')[3]
                                    const cmpn = JSON.parse(components)

                                    const schema = cmpn.schemas[schemaName]

                                    const node = document.createElement('div')
                                    node.classList.add('manifest-row')
                                    const schemaInfo = document.createElement('div')
                                    schemaInfo.classList.add('schema-info')

                                    const nk = document.createElement('span')
                                    nk.classList.add('manifest-key')
                                    nk.textContent = "Request Body:"

                                    const nd = document.createElement('span')
                                    nd.textContent = schemaName

                                    schemaInfo.innerHTML = schemaInfoNode(schemaName, schema).getHTML()
                                    node.appendChild(nk)
                                    node.appendChild(nd)
                                    node.appendChild(schemaInfo)

                                    nd.addEventListener('mouseenter', () => {{
                                        schemaInfo.className = 'schema-info-hover'
                                    }})
                                    schemaInfo.addEventListener('mouseleave', () => {{
                                        schemaInfo.className = 'schema-info'
                                    }})
                                    manifestArea.appendChild(node)

                                }}
                            }})


                        }}
                        if (hasParameter) {{
                            const node = document.createElement('div')
                            node.classList.add('manifest-row')

                            const nodeKey = document.createElement('span')
                            nodeKey.classList.add('manifest-key')
                            nodeKey.textContent = "Paramters"


                            const prop = methodMeta.parameters

                            node.appendChild(nodeKey)

                            const nodeData = document.createElement('span')
                            nodeData.classList.add('manifest-data')

                            prop.forEach(path => {{
                                const nd = document.createElement('div')
                                nd.classList.add("nd")
                                nd.textContent = path.name

                                Object.entries(path).forEach(([k, v]) => {{
                                    const kd = document.createElement('div')
                                    const rk = document.createElement('span')
                                    const rd = document.createElement('span')

                                    if (k != 'name') {{
                                        rk.textContent = k
                                        if (typeof v === 'object') {{
                                            const sn = document.createElement('div')
                                            Object.entries(v).forEach(([k, v]) => {{
                                                const ss = document.createElement('span')
                                                ss.textContent = k
                                                const sd = document.createElement('span')
                                                sd.textContent = v

                                                sn.appendChild(ss)
                                                sn.appendChild(sd)
                                            }})

                                            rd.appendChild(sn)
                                        }} else {{
                                            rd.textContent = v
                                        }}
                                    }}

                                    kd.appendChild(rk)
                                    kd.appendChild(rd)
                                    nd.appendChild(kd)
                                }})

                                nodeData.appendChild(nd)
                                node.appendChild(nodeData)
                                manifestArea.appendChild(node)

                            }})
                        }}
                        // todo: response schema

                        const methodBlock = document.createElement('div');
                        methodBlock.classList.add("method-block");

                        const httpVerbBadge = document.createElement('span');
                        httpVerbBadge.classList.add("http-verb", method.toLowerCase());
                        httpVerbBadge.textContent = method.toUpperCase();

                        const pathText = document.createElement('span');
                        pathText.classList.add("uri-path");
                        pathText.textContent = url;

                        methodBlock.appendChild(httpVerbBadge);
                        methodBlock.appendChild(pathText);

                        const dnsEndpointCode = document.createElement('span');
                        dnsEndpointCode.classList.add("dns-endpoint");
                        dnsEndpointCode.textContent = url;

                        wireframe.appendChild(methodBlock);
                        wireframe.appendChild(dnsEndpointCode);

                        node.appendChild(wireframe);
                        node.appendChild(manifestArea);

                    }})

                    return node;
                }};

                const BPModule = (title, urlPrefix, tags, strPath, components) => {{
                    const paths = JSON.parse(strPath)
                    const sec = document.createElement('section')
                    sec.classList.add("bp-module")

                    const scope = document.createElement('div')
                    scope.classList.add("scope-tags")

                    const metaHead = document.createElement('div')
                    metaHead.classList.add("bp-meta-header")

                    const routeRegistry = document.createElement('div')
                    routeRegistry.classList.add('route-registry')

                    metaHead.innerHTML = `
                    <div class="bp-title">${{title.toUpperCase()}}_BLUEPRINT_CONTEXT</div>
                    <span>Endpoints: ${{Object.keys(paths).length}}</span>
                    <span class="prefix-token">url_prefix: "${{urlPrefix}}"</span>
                    `
                    tags.forEach(tag => {{
                        const scopeNode = document.createElement('span')
                        scopeNode.classList.add('scope-node')
                        scopeNode.textContent = tag
                        scope.appendChild(scopeNode)
                    }})
                    sec.appendChild(metaHead)
                    sec.appendChild(scope)


                    Object.entries(paths).forEach(([url, urlMeta]) => {{
                        routeRegistry.appendChild(BuildRouteNode(url, urlMeta, components))
                    }})
                    sec.appendChild(routeRegistry)

                    return sec
                }}
                window.addEventListener('DOMContentLoaded', () => {{

                    const configTarget = document.getElementById('runtime-config-target');
                    const sysMatx = document.getElementById('sys-matx');

                    Object.entries({0}).forEach(([k, v]) => configTarget.appendChild(BuildSchemaRow(k, v)));

                    Object.entries({1}).forEach(([k, v]) => {{
                        const spn = document.createElement('span')
                        spn.textContent = `${{k}}_${{v}}`
                        sysMatx.appendChild(spn)
                    }})
                    const panBlueprint = document.getElementById('pane-blueprint');

                    {2}.forEach(bp => {{
                        panBlueprint.appendChild(BPModule(bp.title, bp.urlPrefix, bp.tags, bp.paths, bp.components))
                    }})
                }});
            </script>
        </body>
    </html>
    """

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".html") as temp_file:
        temp_file.write(
            html_content.format(
                config, json.dumps(versions), json.dumps(list(blueprints))
            )
        )
        file_url = "file://" + temp_file.name
    click.echo(file_url)
    webbrowser.open(file_url)


if __name__ == "__main__":
    cli()
