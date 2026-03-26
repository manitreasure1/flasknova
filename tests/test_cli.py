
def test_nova_generate_cli_all(runner, tmp_path):
    with tmp_path.as_cwd():
        result = runner.invoke(["flask-nova" "gen" "--app" "main:app" "--format all"])
        assert result.exit_code == 0
        assert "Generated HTTP requests in" in result.output
        assert "Generated Python requests in" in result.output

        generated_file = tmp_path / "app_request.py" / "app_request.http"
        assert generated_file.exists()
        content = generated_file.read_text()
        assert "http://127.0.0.1:5000" in content


def test_nova_generate_cli_py_(runner, tmp_path):
    with tmp_path.as_cwd():
        result = runner.invoke(["flask-nova" "gen" "--app" "main:app" "--format py"])
        assert result.exit_code == 0
        assert "Generated Python requests in" in result.output

        generated_file = tmp_path / "app_request.py"
        assert generated_file.exists()
        content = generated_file.read_text()
        assert "http://127.0.0.1:5000" in content


def test_nova_generate_cli_http(runner, tmp_path):
    with tmp_path.as_cwd():
        result = runner.invoke(["flask-nova" "gen" "--app main:app" "--base-url http://127.0.0.1:5001" "--format http"])
        assert result.exit_code == 0
        assert "Generated HTTP requests in" in result.output

        generated_file = tmp_path / "app_request.http"
        assert generated_file.exists()
        content = generated_file.read_text()
        assert "http://127.0.0.1:5001" in content
