from __future__ import annotations

import typing as t
from jinja2 import Template
from flask.templating import _render
from flask.globals import current_app
from pydantic import BaseModel, ValidationError


def render_template(
    template_name_or_list: str | Template | list[str | Template],
    **context: t.Any,
) -> str:
    """:cls:`Flask` :meth:`flask.templating.render_template` with context serializer"""
    app = current_app._get_current_object()  # type: ignore[attr-defined]

    _method_graph: dict[str, dict[str, t.Any]] = app._compiled_validators.get(
        app._method, {}
    )
    serializer_obj = _method_graph.get(app._rule)
    response_obj = None
    ctx = context
    if (
        serializer_obj
        and context
        and serializer_obj.get("response")
        and serializer_obj["response"].get("type")
        and serializer_obj["response"]["type"] != "any"
    ):
        response_obj = serializer_obj["response"]
    if response_obj:
        ctx = app._serializer(context, response_obj).serialize()
    template = app.jinja_env.get_or_select_template(template_name_or_list)
    return _render(app, template, ctx)
