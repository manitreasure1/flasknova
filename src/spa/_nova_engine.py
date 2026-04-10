import os
import platform
import threading
import time
import urllib.request
import tarfile
from typing import Annotated, Any, Callable, Literal, final, Union
from typing_extensions import Doc
from flask_nova.logger import get_flasknova_logger
import asyncio
import json

try:
    from flask import Flask, render_template
except ImportError:
    Flask = None
    current_app = None
    render_template = None

logger = get_flasknova_logger()


SPA_TEMPLATE_NAME = "index.py"


class EsbuildWrapper:
    def __init__(
        self,
        esbuild_path: Annotated[
            str,
            Doc(
                """
                Path to the esbuild executable.
                Defaults to './bin/esbuild.exe'
                """
            ),
        ] = "./bin/esbuild.exe",
        bundle: Annotated[
            bool,
            Doc(
                """
                Whether to bundle output. Defaults to True.
                """
            ),
        ] = True,
        format: Annotated[
            Literal["iife", "cjs", "esm"],
            Doc(
                """
                Output format (iife, cjs, esm). Defaults to iife for browser compatibility.
                """
            ),
        ] = "iife",
        platform_target: Annotated[
            str,
            Doc(
                """
                Target platform (browser/node)
                """
            ),
        ] = "browser",
        loaders: Annotated[
            dict[str, str] | None,
            Doc(
                """
                Loader mapping for extensions. eg.{ '.png': 'file' }
                """
            ),
        ] = None,
        resolve_extensions: Annotated[
            list[str],
            Doc(
                """
                Extension list for resolution
                """
            ),
        ] = None,
        jsx_factory: Annotated[
            str,
            Doc(
                """
                JSX factory function
                """
            ),
        ] = "React.createElement",
        jsx_fragment: Annotated[
            str,
            Doc(
                """
                JSX fragment function
                """
            ),
        ] = "React.Fragment",
        target: Annotated[
            str,
            Doc(
                """
                JavaScript target version
                """
            ),
        ] = "es6",
        tree_shaking: Annotated[
            bool,
            Doc(
                """
                Enable tree shaking
                """
            ),
        ] = True,
        source_map: Annotated[
            bool,
            Doc(
                """
                Generate source maps
                """
            ),
        ] = False,
        banner: Annotated[
            str | None,
            Doc(
                """
                Banner to add to output
                """
            ),
        ] = None,
        footer: Annotated[
            str | None,
            Doc(
                """
                Footer to add to output
                """
            ),
        ] = None,
        asset_names: Annotated[
            str,
            Doc(
                """
                Asset naming pattern
                """
            ),
        ] = "assets/[name]-[hash]",
        external: Annotated[
            list[str] | None,
            Doc(
                """
                List of module names to exclude from bundling (mark as external).
                Defaults to ['react', 'react-dom'] for SPA use cases.
                """
            ),
        ] = None,
    ) -> None:
        self.esbuild_path = os.path.abspath(esbuild_path)
        self.bundle = bundle
        self.format = format
        self.platform_target = platform_target
        self.loaders = loaders or {}
        self.resolve_extensions = resolve_extensions or [".jsx", ".js", ".tsx", ".ts"]
        self.jsx_factory = jsx_factory
        self.jsx_fragment = jsx_fragment
        self.target = target
        self.tree_shaking = tree_shaking
        self.source_map = source_map
        self.banner = banner
        self.footer = footer
        self.asset_names = asset_names
        # Default to marking react and react-dom as external for SPAs loaded from CDN
        self.external = external if external is not None else ["react", "react-dom"]

    async def transform(
        self,
        entry_file: Annotated[
            str,
            Doc(
                """
                The path to the source file (e.g., .jsx, .tsx, .js) that
                serves as the entry point for the bundle.
                """
            ),
        ],
        output_file: Annotated[
            str,
            Doc(
                """
                The destination path where the generated bundle and
                its associated files will be saved.
                """
            ),
        ] = ".dist/",
        minify: Annotated[
            bool,
            Doc(
                """
                If True, enables code minification (removes whitespace,
                shortens identifiers, and optimizes syntax).
                """
            ),
        ] = False,
        extra_args: Annotated[
            list[str] | None,
            Doc(
                """
                Additional CLI flags to pass to esbuild.
                """
            ),
        ] = None,
    ):
        """
        Converts JSX/TSX to browser-ready JS using esbuild.

        This method uses esbuild's build API, handling
        dependency resolution and transformation.
        """

        command = [self.esbuild_path, entry_file, f"--outfile={output_file}"]

        if self.bundle:
            command.append("--bundle")

        command.extend(
            [
                f"--format={self.format}",
                f"--platform={self.platform_target}",
                f"--target={self.target}",
                f"--jsx-factory={self.jsx_factory}",
                f"--jsx-fragment={self.jsx_fragment}",
            ]
        )

        # Add loaders
        for ext, loader in self.loaders.items():
            command.append(f"--loader:{ext}={loader}")

        # Add resolve extensions
        if self.resolve_extensions:
            extensions = ",".join(
                f".{ext}" if not ext.startswith(".") else ext
                for ext in self.resolve_extensions
            )
            command.append(f"--resolve-extensions={extensions}")

        if self.tree_shaking:
            command.append("--tree-shaking=true")

        if self.source_map:
            command.append("--sourcemap")

        if self.banner:
            command.append(f"--banner:js={self.banner}")

        if self.footer:
            command.append(f"--footer:js={self.footer}")

        command.append(f"--asset-names={self.asset_names}")

        # Add external modules (not bundled)
        if self.external:
            for module in self.external:
                command.append(f"--external:{module}")

        if minify:
            command.append("--minify")

        if extra_args:
            command.extend(extra_args)

        try:
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"✓ Nova Engine: Compiled {entry_file} -> {output_file}")
                return True
            else:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"✗ Esbuild Error:n{error_msg}")
                return False

        except Exception as e:
            logger.error(f"✗ Nova Engine Error: {str(e)}")
            return False


def get_esbuild_binary(version: str = "0.27.4", target_dir: str = "./bin"):
    system = platform.system().lower()
    arch = platform.machine().lower()
    pkg_map = {
        ("windows", "amd64"): "win32-x64",
        ("windows", "x86_64"): "win32-x64",
        ("darwin", "arm64"): "darwin-arm64",
        ("darwin", "x86_64"): "darwin-x64",
        ("linux", "x86_64"): "linux-x64",
        ("linux", "aarch64"): "linux-arm64",
        ("linux", "armv7l"): "linux-arm",
    }

    pkg_suffix = pkg_map.get((system, arch))
    if not pkg_suffix:
        raise RuntimeError(f"Unsupported platform: {system} {arch}")
    # Format: https://registry.npmjs.org/@esbuild/{platform}/-/{platform}-{version}.tgz
    url = (
        f"https://registry.npmjs.org/@esbuild/{pkg_suffix}/-/{pkg_suffix}-{version}.tgz"
    )

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    tar_path = os.path.join(target_dir, "esbuild.tgz")
    exe_name = "esbuild.exe" if system == "windows" else "esbuild"
    final_exe_path = os.path.join(target_dir, exe_name)

    # Check if binary already exists
    if os.path.exists(final_exe_path):
        logger.debug(f"✓ Esbuild binary already available at: {final_exe_path}")
        return final_exe_path

    logger.debug(f"Downloading esbuild v{version} for {pkg_suffix}...")
    urllib.request.urlretrieve(url, tar_path)

    with tarfile.open(tar_path, "r:gz") as tar:
        member_name = f"package/{exe_name}"
        try:
            member = tar.getmember(member_name)
            member.name = os.path.basename(member.name)  # Flatten path
            tar.extract(member, path=target_dir)
        except KeyError:
            logger.critical(
                "Could not find binary in expected tar path. Extracting all..."
            )
            tar.extractall(path=target_dir)

    # Cleanup
    os.remove(tar_path)
    if system != "windows":
        os.chmod(final_exe_path, 0o755)
    logger.info(f"Success! Binary located at: {final_exe_path}")
    return final_exe_path


def _render_spa_html(
    compiled_js: str,
    state_json: str,
    template_vars: dict[str, Any],
    compiled_file: str,
    template_name: str = SPA_TEMPLATE_NAME,
) -> str:
    context: dict[str, Any] = {
        "title": template_vars.get("title", "Flask Nova SPA"),
        "head_extra": template_vars.get("head_extra", ""),
        "body_extra": template_vars.get("body_extra", ""),
        "state_json": state_json,
        "compiled_js": compiled_js,
        "compiled_file": compiled_file,
        "template_vars": template_vars,
    }

    if render_template is not None:
        try:
            return render_template(template_name, **context)
        except Exception:
            logger.debug(
                f"SPA template '{template_name}' not found or failed to render, falling back to inline HTML."
            )

    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
            <title>{context['title']}</title>
            <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
            <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
            {context['head_extra']}
        </head>
        <body>
            <div id="root">
                <div style="padding: 2rem; color: #666;">
                    <h2>Loading React...</h2>
                    <p>If you see this, JavaScript may not be executing.</p>
                </div>
            </div>
            <script>window.NOVA_STATE = {context['state_json']};</script>
            <script>
                // Debug: Check if React loaded
                console.log('React loaded:', typeof window.React);
                console.log('ReactDOM loaded:', typeof window.ReactDOM);
                console.log('NOVA_STATE:', window.NOVA_STATE);

                {context['compiled_js']}
            </script>
            {context['body_extra']}
        </body>
    </html>
    """


def _run_async_in_new_loop(coro):
    """Run a coroutine in a new event loop, handling cases where a loop is already running."""
    try:
        # Check if there's already a running event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        return asyncio.run(coro)
    else:
        # There's already a running loop, we need to run in a new thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()


def render_spa_template(
    file: Annotated[str, Doc("SPA file with extension .jsx or .tsx")],
    context: dict[str, Any] | None = None,
    output_dir: str = ".dist",
    template_vars: dict[str, Any] | None = None,
    esbuild_path: str | None = None,
    compiler: EsbuildWrapper | None = None,
) -> str:
    """
    Render a SPA template using NovaEngine.

    This is the route-facing helper. It compiles the source file and
    returns a full HTML payload for rendering in Flask-Nova routes.
    """
    if not file.endswith((".jsx", ".tsx", ".js", ".ts")):
        raise ValueError("File must end with .jsx, .tsx, .js, or .ts")

    if not os.path.exists(file):
        raise FileNotFoundError(f"File not found: {file}")

    context = context or {}
    template_vars = template_vars or {}

    if compiler is None:
        esbuild_path = esbuild_path or get_esbuild_binary()
        compiler = EsbuildWrapper(esbuild_path=esbuild_path)

    NovaEngine.set_compiler(compiler)

    return _run_async_in_new_loop(
        NovaEngine.render(
            file_path=file,
            context=context,
            output_dir=output_dir,
            template_vars=template_vars,
        )
    )


def _collect_spa_files(paths: str | list[str]) -> dict[str, float]:
    if isinstance(paths, str):
        paths = [paths]

    files: dict[str, float] = {}
    for candidate in paths:
        if os.path.isdir(candidate):
            for root, _, filenames in os.walk(candidate):
                for name in filenames:
                    if name.endswith((".jsx", ".tsx", ".js", ".ts")):
                        path = os.path.join(root, name)
                        files[path] = os.path.getmtime(path)
        elif os.path.isfile(candidate) and candidate.endswith(
            (".jsx", ".tsx", ".js", ".ts")
        ):
            files[candidate] = os.path.getmtime(candidate)
    return files


class SpaHotReloader:
    def __init__(
        self,
        paths: str | list[str],
        output_dir: str = ".dist",
        interval: float = 1.0,
        compiler: EsbuildWrapper | None = None,
        on_rebuild: Callable[[str, str], None] | None = None,
    ):
        self.paths = paths
        self.output_dir = output_dir
        self.interval = interval
        self.compiler = compiler or EsbuildWrapper(esbuild_path=get_esbuild_binary())
        self.on_rebuild = on_rebuild
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._mtimes = _collect_spa_files(paths)

    def start(self) -> "SpaHotReloader":
        if not self._thread.is_alive():
            self._thread.start()
        return self

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=self.interval * 2)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(self.interval)
            current = _collect_spa_files(self.paths)
            for path, mtime in current.items():
                if path not in self._mtimes or mtime > self._mtimes[path]:
                    self._rebuild(path)
            self._mtimes = current

    def _rebuild(self, source_path: str) -> None:
        try:
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            output_file = os.path.join(self.output_dir, f"{base_name}.js")
            os.makedirs(self.output_dir, exist_ok=True)
            success = asyncio.run(self.compiler.transform(source_path, output_file))
            if success and self.on_rebuild:
                self.on_rebuild(source_path, output_file)
        except Exception as exc:
            logger.error(f"Failed to rebuild SPA source {source_path}: {exc}")


def watch_spa(
    paths: str | list[str],
    output_dir: str = ".dist",
    interval: float = 1.0,
    compiler: EsbuildWrapper | None = None,
    on_rebuild: Callable[[str, str], None] | None = None,
) -> SpaHotReloader:
    """Start a background watcher that recompiles SPA files when they change."""
    return SpaHotReloader(
        paths=paths,
        output_dir=output_dir,
        interval=interval,
        compiler=compiler,
        on_rebuild=on_rebuild,
    ).start()


class SpaHotReloadExtension:
    """
    Flask extension for automatic SPA hot-reloading during development.

    Automatically starts the SPA watcher when the Flask app is in debug mode.
    Can be configured via app config or constructor parameters.
    """

    def __init__(
        self,
        app: Union["Flask", None] = None,
        paths: Union[str, list[str], None] = None,
        output_dir: str = ".dist",
        interval: float = 1.0,
        compiler: Union[EsbuildWrapper, None] = None,
        on_rebuild: Union[Callable[[str, str], None], None] = None,
        auto_start: bool = True,
    ):
        if Flask is None:
            raise ImportError("Flask is required for SpaHotReloadExtension")

        self.app = app
        self.paths = paths
        self.output_dir = output_dir
        self.interval = interval
        self.compiler = compiler
        self.on_rebuild = on_rebuild
        self.auto_start = auto_start
        self._reloader: SpaHotReloader | None = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app: "Flask") -> None:
        """Initialize the extension with a Flask app."""
        # Get config from app.config, with defaults
        config_paths = app.config.get("SPA_HOT_RELOAD_PATHS", self.paths)
        config_output_dir = app.config.get("SPA_HOT_RELOAD_OUTPUT_DIR", self.output_dir)
        config_interval = app.config.get("SPA_HOT_RELOAD_INTERVAL", self.interval)
        config_auto_start = app.config.get("SPA_HOT_RELOAD_AUTO_START", self.auto_start)

        # Use constructor values if not None, else config
        paths = self.paths if self.paths is not None else config_paths
        output_dir = (
            self.output_dir if self.output_dir != ".dist" else config_output_dir
        )
        interval = self.interval if self.interval != 1.0 else config_interval
        auto_start = self.auto_start if not self.auto_start else config_auto_start

        if paths is None:
            if getattr(app, "template_folder", None):
                paths = [app.template_folder]
            else:
                paths = ["templates", "scripts"]

        if auto_start and app.debug:
            # Start watching automatically in debug mode
            self._reloader = watch_spa(
                paths=paths,
                output_dir=output_dir,
                interval=interval,
                compiler=self.compiler,
                on_rebuild=self.on_rebuild,
            )
            logger.info(f"✓ SPA Hot Reload started watching: {paths}")

        # Store on app for access
        app.spa_hot_reloader = self

        # Register teardown to stop watcher
        @app.teardown_appcontext
        def teardown_spa_watcher(exception=None):
            if self._reloader:
                self._reloader.stop()
                logger.info("✓ SPA Hot Reload stopped")

    def start_watching(self) -> None:
        """Manually start the watcher."""
        if self._reloader is None and self.app:
            paths = self.paths or self.app.config.get("SPA_HOT_RELOAD_PATHS")
            if paths is None:
                paths = (
                    [self.app.template_folder]
                    if getattr(self.app, "template_folder", None)
                    else ["src", "spa", "frontend", "client"]
                )
            self._reloader = watch_spa(
                paths=paths,
                output_dir=self.output_dir,
                interval=self.interval,
                compiler=self.compiler,
                on_rebuild=self.on_rebuild,
            )
            logger.info(f"✓ SPA Hot Reload started watching: {paths}")

    def stop_watching(self) -> None:
        """Stop the watcher."""
        if self._reloader:
            self._reloader.stop()
            self._reloader = None
            logger.info("✓ SPA Hot Reload stopped")


@final
class NovaEngine:
    """
    The main engine for rendering SPA files as bundled JavaScript.
    Provides caching and HTML generation for Flask templates.
    """

    _cache: dict[str, str] = {}
    _compiler: EsbuildWrapper | None = None

    @classmethod
    def set_compiler(cls, compiler: EsbuildWrapper) -> None:
        """Set the esbuild compiler instance to use."""
        cls._compiler = compiler

    @classmethod
    async def compile_file(cls, file_path: str, output_dir: str = ".dist") -> str:
        """
        Compile a JSX/TSX file and cache the result.

        Args:
            file_path: Path to the source file
            output_dir: Directory to output compiled files

        Returns:
            Path to the compiled JavaScript file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")

        # Check if file has been modified since last compile
        file_mtime = os.path.getmtime(file_path)
        cache_key = f"{file_path}:{file_mtime}"

        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # Compile the file
        compiler = cls._compiler or EsbuildWrapper()
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_file = os.path.join(output_dir, f"{base_name}.js")

        os.makedirs(output_dir, exist_ok=True)

        success = await compiler.transform(file_path, output_file)
        if not success:
            raise RuntimeError(f"Failed to compile {file_path}")

        # Cache the result
        cls._cache[cache_key] = output_file
        return output_file

    @classmethod
    async def render(
        cls,
        file_path: str,
        context: dict[str, Any] | None = None,
        output_dir: str = ".dist",
        template_vars: dict[str, Any] | None = None,
    ) -> str:
        """
        Render a SPA template with context data.

        Args:
            file_path: Path to the JSX/TSX file
            context: Data to pass to the React component
            output_dir: Directory for compiled files
            template_vars: Additional template variables

        Returns:
            HTML string with embedded JavaScript
        """
        context = context or {}
        template_vars = template_vars or {}

        # Compile the file
        compiled_file = await cls.compile_file(file_path, output_dir)

        # Read the compiled JavaScript
        try:
            with open(compiled_file, "r", encoding="utf-8") as f:
                compiled_js = f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read compiled file {compiled_file}: {e}")

        # Generate state JSON
        state_json = json.dumps(context)

        template_name = template_vars.get("template_name", SPA_TEMPLATE_NAME)
        return _render_spa_html(
            compiled_js=compiled_js,
            state_json=state_json,
            template_vars=template_vars,
            compiled_file=compiled_file,
            template_name=template_name,
        )
