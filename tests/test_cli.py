from pathlib import Path

# http : Generated HTTP requests in {http_file}
# py : "Generated Python requests in {py_file}
"""
@click.option("--app", required=True, help="Your Flask app import path, e.g. 'examples.form_ex:app'.")
@click.option("--base-url", default="http://127.0.0.1:5000", help="Base URL for requests.")
@click.option("--output", default=".", type=click.Path(path_type=Path), help="Output directory.")
@click.option("--format", type=click.Choice(["http", "py", "all"]), default="all")

"""
def test_nova_generate_cli_all(runner, tmp_path: Path):
    with tmp_path.cwd():
        result = runner.invoke(["flask-nova" "gen" "--app" "main:app" "--format all"])
        assert result.exit_code == 0
        assert "Generated HTTP requests in" in result.output
        assert "Generated Python requests in" in result.output

        # 2. Verify the file actually exists in the temp directory
        generated_file = tmp_path / "expected_file.py"
        assert generated_file.exists()
        content = generated_file.read_text()
        assert "class NovaResource" in content

