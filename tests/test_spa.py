from typing import Any

import pytest
import os
import tempfile
import time

from spa import (
    EsbuildWrapper,
    NovaEngine,
    get_esbuild_binary,
    render_spa_template,
    watch_spa,
    SpaHotReloader,
)


class TestEsbuildWrapper:
    def test_init_defaults(self):
        """Test EsbuildWrapper initialization with defaults."""
        wrapper = EsbuildWrapper()
        assert wrapper.bundle is True
        assert wrapper.format == "iife"
        assert wrapper.platform_target == "browser"
        assert wrapper.jsx_factory == "React.createElement"

    def test_init_custom(self):
        """Test EsbuildWrapper initialization with custom values."""
        wrapper = EsbuildWrapper(
            bundle=False,
            format="esm",
            platform_target="node",
            jsx_factory="h"
        )
        assert wrapper.bundle is False
        assert wrapper.format == "esm"
        assert wrapper.platform_target == "node"
        assert wrapper.jsx_factory == "h"


class TestNovaEngine:
    @pytest.mark.asyncio
    async def test_compile_file_not_found(self):
        """Test that compile_file raises error for missing files."""
        with pytest.raises(FileNotFoundError):
            await NovaEngine.compile_file("nonexistent.jsx")


class TestRenderSpaTemplate:
    def test_render_spa_template_with_fake_compiler(self):
        """Test render_spa_template with a custom compiler implementation."""
        jsx_content = '''
import React from 'react';

function App() {
    return React.createElement('div', null, 'Hello ' + window.NOVA_STATE.user);
}

export default App;
'''

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, 'App.jsx')
            output_dir = os.path.join(tmpdir, 'dist')
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(jsx_content)

            class FakeCompiler:
                async def transform(self, entry_file: str, output_file: str, minify: bool=False, extra_args=None):
                    with open(output_file, 'w', encoding='utf-8') as out:
                        out.write('console.log("compiled");')
                    return True

            html = render_spa_template(
                source_path,
                {'user': 'World'},
                output_dir=output_dir,
                compiler=FakeCompiler(),
            )

            assert '<div id="root"></div>' in html
            assert 'window.NOVA_STATE = {"user": "World"}' in html
            assert os.path.exists(os.path.join(output_dir, 'App.js'))

    def test_render_spa_template_file_not_found(self):
        """Test render_spa_template reports missing files."""
        with pytest.raises(FileNotFoundError):
            render_spa_template('missing.jsx')


class TestSpaHotReloader:
    def test_spa_hot_reloader_init(self):
        """Test SpaHotReloader initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, 'App.jsx')
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write('console.log("test")')

            reloader = SpaHotReloader(paths=source_path, output_dir=tmpdir, interval=0.5)
            assert reloader.paths == source_path
            assert reloader.output_dir == tmpdir
            assert reloader.interval == 0.5
            assert not reloader._thread.is_alive()

    def test_spa_hot_reloader_start_stop(self):
        """Test starting and stopping the reloader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, 'App.jsx')
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write('console.log("test")')

            reloader = SpaHotReloader(paths=source_path, output_dir=tmpdir)
            reloader.start()
            assert reloader._thread.is_alive()
            reloader.stop()
            assert not reloader._thread.is_alive()

    def test_watch_spa_rebuilds_changed_files(self):
        """The watcher should rebuild changed source files."""
        jsx_content = 'console.log("hello")'

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, 'App.jsx')
            output_dir = os.path.join(tmpdir, 'dist')
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write(jsx_content)

            class FakeCompiler:
                async def transform(self, entry_file: str, output_file: str, minify: bool=False, extra_args=None):
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, 'w', encoding='utf-8') as out:
                        out.write('compiled:' + entry_file)
                    return True

            built_paths: list[tuple[Any, Any]] = []

            watcher = watch_spa(
                source_path,
                output_dir=output_dir,
                interval=0.1,
                compiler=FakeCompiler(),
                on_rebuild=lambda src, out: built_paths.append((src, out)),
            )

            try:
                time.sleep(0.15)
                with open(source_path, 'w', encoding='utf-8') as f:
                    f.write('console.log("updated")')
                time.sleep(0.3)
            finally:
                watcher.stop()

            assert built_paths, "Expected watcher to rebuild modified file"
            assert built_paths[-1][0] == source_path
            assert os.path.exists(os.path.join(output_dir, 'App.js'))


class TestSpaHotReloadExtension:
    def test_extension_init_without_app(self):
        """Test SpaHotReloadExtension initialization without app."""
        from spa import SpaHotReloadExtension
        ext = SpaHotReloadExtension(paths="src", output_dir=".dist")
        assert ext.paths == "src"
        assert ext.output_dir == ".dist"
        assert ext._reloader is None

    def test_extension_init_with_app_debug(self):
        """Test extension automatically starts in debug mode."""
        pytest.importorskip("flask")
        from flask import Flask
        from spa import SpaHotReloadExtension

        app = Flask(__name__)
        app.debug = True

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, 'App.jsx')
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write('console.log("test")')

            ext = SpaHotReloadExtension(app, paths=source_path, output_dir=tmpdir, interval=0.1)
            assert hasattr(app, 'spa_hot_reloader')
            assert ext._reloader is not None
            assert ext._reloader._thread.is_alive()

            # Clean up
            ext.stop_watching()

    def test_extension_init_with_app_no_debug(self):
        """Test extension does not start automatically when not in debug mode."""
        pytest.importorskip("flask")
        from flask import Flask
        from spa import SpaHotReloadExtension

        app = Flask(__name__)
        app.debug = False

        ext = SpaHotReloadExtension(app, paths="src")
        assert ext._reloader is None

    def test_extension_manual_start_stop(self):
        """Test manual start and stop of the extension."""
        pytest.importorskip("flask")
        from flask import Flask
        from spa import SpaHotReloadExtension

        app = Flask(__name__)
        app.debug = False

        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, 'App.jsx')
            with open(source_path, 'w', encoding='utf-8') as f:
                f.write('console.log("test")')

            ext = SpaHotReloadExtension(app, paths=source_path, output_dir=tmpdir, interval=0.1, auto_start=False)
            assert ext._reloader is None

            ext.start_watching()
            assert ext._reloader is not None
            assert ext._reloader._thread.is_alive()

            ext.stop_watching()
            assert ext._reloader is None


def test_get_esbuild_binary():
    """Test esbuild binary download (may be slow)."""
    # This test might be skipped in CI due to network requirements
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = get_esbuild_binary(target_dir=temp_dir)
            assert os.path.exists(path)
            assert os.access(path, os.X_OK)
    except Exception as e:
        pytest.skip(f"Binary download failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])