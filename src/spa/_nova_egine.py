import os
import platform
import urllib.request
import tarfile
import subprocess
import os
from typing import Annotated, Literal, final
from typing_extensions import Doc
from flask_nova.logger import get_flasknova_logger

logger = get_flasknova_logger()

# js_meta_injector = """
# var meta = document.createElement('meta');
# meta.name = 'nova-version';
# meta.content = '1.0.0';
# document.head.appendChild(meta);
# """


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
                Output format (iife, cjs, esm)
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
            Literal["jsx", "js", "tsx", "ts"],
            Doc(
                """
                Extension list for resolution
                """
            ),
        ] = "jsx",
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
            Literal["es6", "es5", "esnext", "es2015"],
            Doc(
                """
                """
            ),
        ] = "es6",
        tree_shaking: Annotated[
            bool,
            Doc(
                """
                """
            ),
        ] = True,
        source_map: Annotated[
            bool,
            Doc(
                """
                """
            ),
        ] = False,
        banner: Annotated[
            str,
            Doc(
                """
                """
            ),
        ] = "js={js_meta_injector}",
        footer: Annotated[
            str,
            Doc(
                """
                """
            ),
        ] = "js={js_}",
        assetNames: Annotated[
            str,
            Doc(
                """
                """
            ),
        ] = "assets/[name]-[hash]",
    ) -> None:

        self.esbuild = os.path.abspath(esbuild_path)

    def transform(
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
                Common options include:
                - `--sourcemap`: Generates a source map file.
                - `--target=es6`: Sets the JS language target (e.g., esnext, es2015).
                - `--external:package`: Excludes a specific package from the bundle.
                - `--define:process.env.NODE_ENV=\\"production\\"`: Replaces global constants.
                - `--tree-shaking=true`: Forces removal of unused code.
                "--banner:js={js_meta_injector}", Add meta and script tag ```js var meta = document.createElement('meta'); \n meta.name = 'nova-version'; \nmeta.content = '1.0.0'; \ndocument.head.appendChild(meta);
                """
            ),
        ] = None,
    ):
        """
        Converts JSX/TSX to browser-ready JS using a bundled IIFE format.

        This method uses esbuild's 'Build' API under the hood, handling
        dependency resolution and transformation in a single pass.
        """

        command = [
            self.esbuild,
            entry_file,
            f"--outfile={output_file}",
            "--bundle",
            "--format=iife",
            "--platform=browser",
            "--loader:.jsx=jsx",
            "--loader:.tsx=tsx",
            "--resolve-extensions=.jsx,.js,.tsx,.ts",
            "--jsx-factory=React.createElement",
            "--jsx-fragment=React.Fragment",
        ]

        if minify:
            command.append("--minify")

        if extra_args:
            command.extend(extra_args)
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            if result.returncode == 0:
                logger.info(f"✓ Nova Engine: Compiled  {entry_file} -> {output_file}")
            else:
                logger.error(f"✗ Error:\n{result.stderr}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Nova Engine Error:\n{e.stderr}")
            return False


def get_esbuild_binary(version="0.27.4", target_dir="./bin"):
    system = platform.system().lower()
    arch = platform.machine().lower()
    pkg_map = {
        ("windows", "amd64"): "win32-x64",
        ("windows", "x86_64"): "win32-x64",
        ("darwin", "arm64"): "darwin-arm64",
        ("darwin", "x86_64"): "darwin-x64",
        ("linux", "x86_64"): "linux-x64",
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


def render_spa_template(
    file: Annotated[str, Doc("""spa file by extention .jsx or .tsx""")],
):
    if not file.endswith((".js", ".tsx")):
        raise


@final
class NovaEngine:
    """
    the main engine for rendering all files as bundle.js
    js file will be used by render_template_string from flask

    must be able to know when to render a specific page with its data when user visits
    """

# Example execution
# if __name__ == "__main__":
#     bin_path = get_esbuild_binary()

# if __name__ == "__main__":
#     compiler = EsbuildWrapper()
#     compiler.transform("src/App.jsx", "static/dist/bundle.js")
