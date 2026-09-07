from click.testing import CliRunner

from flask_nova.cli import _load_app, cli


def test_cli_help() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "gen" in result.output
    assert "info" in result.output


def test_load_app_imports_module_from_current_directory(tmp_path, monkeypatch) -> None:
    (tmp_path / "model_name.py").write_text("app = object()", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert _load_app("model_name:app") is not None