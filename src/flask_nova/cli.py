
import click
import inspect
import json
import importlib
from pathlib import Path
from flask import Flask
from pydantic import BaseModel
from typing import get_type_hints
import typing

@click.group()
def cli():
    """Flask-Nova CLI utilities."""
    pass


def _example_from_type(py_type):
    if py_type is int:
        return 1
    if py_type is float:
        return 1.0
    if py_type is bool:
        return True
    if py_type is str:
        return "string"
    origin = typing.get_origin(py_type)
    args = typing.get_args(py_type)
    if origin in (list, typing.List):
        return [_example_from_type(args[0]) if args else "string"]
    if origin in (dict, typing.Dict):
        return {"key": "value"}
    return "string"


def _is_form_default(default) -> bool:
    """Detect a Flask-Nova Form default (duck-typing)."""
    if default is inspect._empty:
        return False
    cls = getattr(default, "__class__", None)
    if cls is None:
        return False
    name = getattr(cls, "__name__", "").lower()
    if "form" in name:
        return True
    if hasattr(default, "model") and inspect.isclass(default.model):
        return True
    return False


def _example_from_model(model_cls):
    """Generate example from a Pydantic BaseModel using model_json_schema."""
    if model_cls is None:
        return {}
    try:
        if inspect.isclass(model_cls) and issubclass(model_cls, BaseModel):
            schema = model_cls.model_json_schema()
            props = schema.get("properties", {})
            out = {}
            for k, v in props.items():
                ex = v.get("example") or (v.get("examples") and (v.get("examples")[0] if isinstance(v.get("examples"), list) else v.get("examples")))
                if ex:
                    out[k] = ex
                else:
                    out[k] = _example_from_type(v.get("type", str))
            return out
    except Exception:
        pass
    return {}


def _build_example_from_signature(func):
    """
    Return (example_obj, uses_form:bool).
    - example_obj for JSON routes: dict of fields
    - for Form routes: flat dict of form field -> example value
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    json_body = {}
    form_body = {}
    uses_form = False

    for name, param in sig.parameters.items():
        anno = type_hints.get(name, inspect._empty)
        default = param.default

        if _is_form_default(default):
            uses_form = True
            model_cls = getattr(default, "model", None)
            if inspect.isclass(model_cls):
                form_body.update(_example_from_model(model_cls))
            else:
                if inspect.isclass(anno) and issubclass(anno, BaseModel):
                    form_body.update(_example_from_model(anno))
                else:
                    form_body[name] = _example_from_type(anno if anno is not inspect._empty else str)
            continue

        if inspect.isclass(anno) and issubclass(anno, BaseModel):
            json_body.update(_example_from_model(anno))
            continue

        if anno is not inspect._empty:
            json_body[name] = _example_from_type(anno)
        else:
            json_body[name] = _example_from_type(str)

    if uses_form:
        form_body.update(json_body)
        return form_body, True
    return json_body, False


def _render_multipart_http(fields: dict) -> str:
    """Render a simple multipart body for .http file (with boundary)."""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    parts = []
    for k, v in fields.items():
        parts.append(f"--{boundary}")
        parts.append(f'Content-Disposition: form-data; name="{k}"')
        parts.append("")
        parts.append(str(v))
    parts.append(f"--{boundary}--")
    return "\n".join(parts)


def _generate_http_file(app: Flask, output: Path, base_url: str, app_name: str):
    http_file = output / f"{app_name}_request.http"
    lines = [f"@baseUrl = {base_url}", ""]

    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        view_func = app.view_functions[rule.endpoint]
        example, uses_form = _build_example_from_signature(view_func)
        methods = [m for m in rule.methods if m not in ("HEAD", "OPTIONS")]
        for method in methods:
            lines.append(f"### {rule.endpoint}")
            lines.append(f"{method} {{baseUrl}}{rule.rule}")
            if uses_form:
                lines.append("Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW")
                lines.append("")
                lines.append(_render_multipart_http(example))
            else:
                lines.append("Content-Type: application/json")
                lines.append("")
                lines.append(json.dumps(example, indent=2))
            lines.append("")

    http_file.write_text("\n".join(lines), encoding="utf-8")
    click.echo(f"Generated HTTP requests in {http_file}")


def _generate_py_file(app: Flask, output: Path, base_url: str, app_name: str):
    py_file = output / f"{app_name}_request.py"
    out_lines = ["import requests", "", f"BASE_URL = \"{base_url}\"", ""]

    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        view_func = app.view_functions[rule.endpoint]
        example, uses_form = _build_example_from_signature(view_func)
        methods = [m for m in rule.methods if m not in ("HEAD", "OPTIONS")]
        for method in methods:
            func_name = f"test_{rule.endpoint}".replace(".", "_")
            out_lines.append(f"def {func_name}():")
            if uses_form:
                out_lines.append(f"    data = {json.dumps(example, indent=4)}")
                out_lines.append(f"    resp = requests.{method.lower()}(BASE_URL + \"{rule.rule}\", data=data)")
            else:
                out_lines.append(f"    payload = {json.dumps(example, indent=4)}")
                out_lines.append(f"    resp = requests.{method.lower()}(BASE_URL + \"{rule.rule}\", json=payload)")
            out_lines.append("    print(resp.status_code, resp.text)")
            out_lines.append("")

    py_file.write_text("\n".join(out_lines), encoding="utf-8")
    click.echo(f"Generated Python requests in {py_file}")


@cli.command()
@click.option("--app", required=True, help="Your Flask app import path, e.g. 'examples.form_ex:app'.")
@click.option("--base-url", default="http://127.0.0.1:5000", help="Base URL for requests.")
@click.option("--output", default=".", type=click.Path(path_type=Path), help="Output directory.")
@click.option("--format", type=click.Choice(["http", "py", "all"]), default="all")
def gen(app, base_url, output, format):
    """Generate .http and/or .py files for testing routes."""
    module_name, app_name = app.split(":")
    mod = importlib.import_module(module_name)
    app_obj = getattr(mod, app_name)

    if callable(app_obj) and not isinstance(app_obj, Flask):
        app_obj = app_obj()

    if not isinstance(app_obj, Flask):
        raise click.ClickException("The provided app is not a Flask instance.")

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    if format in ("http", "all"):
        _generate_http_file(app_obj, output_path, base_url, app_name)

    if format in ("py", "all"):
        _generate_py_file(app_obj, output_path, base_url, app_name)


if __name__ == "__main__":
    cli()
