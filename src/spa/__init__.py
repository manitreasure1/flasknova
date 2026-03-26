"""Optional SPA support for Flask Nova.

This package is intended to be installed as an optional extra:

    pip install flask-nova[spa]

Then in `flask_nova` you can access SPA helpers as `flask_nova.spa`.
"""

from ._nova_egine import EsbuildWrapper, get_esbuild_binary, render_spa_template

__all__ = ["EsbuildWrapper", "get_esbuild_binary", "render_spa_template"]


def ensure_esbuild_binary(version="0.27.4", target_dir="./bin"):
    return get_esbuild_binary(version=version, target_dir=target_dir)
