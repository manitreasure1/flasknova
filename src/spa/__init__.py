"""Optional SPA support for Flask Nova.

This package is intended to be installed as an optional extra:

    pip install flask-nova[spa]

Then import SPA helpers directly from this package.
"""

from ._nova_engine import (
    EsbuildWrapper,
    get_esbuild_binary,
    render_spa_template,
    watch_spa,
    SpaHotReloader,
    SpaHotReloadExtension,
    NovaEngine
)

__all__ = [
    "EsbuildWrapper",
    "get_esbuild_binary",
    "render_spa_template",
    "watch_spa",
    "SpaHotReloader",
    "SpaHotReloadExtension",
    "NovaEngine"
]


def ensure_esbuild_binary(version="0.27.4", target_dir="./bin"):
    return get_esbuild_binary(version=version, target_dir=target_dir)
