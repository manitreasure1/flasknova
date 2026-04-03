from pathlib import Path
from pytest import MonkeyPatch
from flask.testing import FlaskCliRunner
from flask_nova.cli import cli as nova_cli


def test_nova_generate_cli_all(runner: FlaskCliRunner, tmp_path: Path, monkeypatch: MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text(
        """
from flask_nova import FlaskNova

app = FlaskNova(__name__)

@app.route('/', methods=['GET'])
def index():
    return {'message': 'ok'}
""",
        encoding='utf-8',
    )

    result = runner.invoke(nova_cli, args=["gen", "--app", "main:app", "--format", "all"])
    assert result.exit_code == 0
    assert "Generated HTTP requests in" in result.output
    assert "Generated Python requests in" in result.output
    generated_http = tmp_path / "app_request.http"
    generated_py = tmp_path / "app_request.py"
    assert generated_http.exists()
    assert generated_py.exists()
    content = generated_http.read_text()
    assert "http://127.0.0.1:5000" in content


def test_nova_generate_cli_py_(runner: FlaskCliRunner, tmp_path: Path, monkeypatch: MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text(
        """
from flask_nova import FlaskNova

app = FlaskNova(__name__)

@app.route('/', methods=['GET'])
def index():
    return {'message': 'ok'}
""",
        encoding='utf-8',
    )

    result = runner.invoke(nova_cli, args=["gen", "--app", "main:app", "--format", "py"])
    assert result.exit_code == 0
    assert "Generated Python requests in" in result.output

    generated_file = tmp_path / "app_request.py"
    assert generated_file.exists()
    content = generated_file.read_text()
    assert "http://127.0.0.1:5000" in content


def test_nova_generate_cli_http(runner: FlaskCliRunner, tmp_path: Path, monkeypatch: MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "main.py").write_text(
        """
from flask_nova import FlaskNova

app = FlaskNova(__name__)

@app.route('/', methods=['GET'])
def index():
    return {'message': 'ok'}
""",
        encoding='utf-8',
    )

    result = runner.invoke(nova_cli, args=["gen", "--app", "main:app", "--base-url", "http://127.0.0.1:5001", "--format", "http"])
    assert result.exit_code == 0
    assert "Generated HTTP requests in" in result.output
    generated_file = tmp_path / "app_request.http"
    assert generated_file.exists()
    content = generated_file.read_text()
    assert "http://127.0.0.1:5001" in content
