"""Unit tests for the CLI adapter."""

from click.testing import CliRunner

from adapters.inbound.cli import cli


def test_cli_help() -> None:
    """Verify that --help renders options correctly and exits 0."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Log Normalizer" in result.output
    assert "--port" in result.output
    assert "--output" in result.output
    assert "--tls-cert" in result.output


def test_cli_invalid_tls_pairs(tmp_path) -> None:  # noqa: ANN001
    """Verify that providing only cert or key but not both exits 1."""
    runner = CliRunner()
    cert_file = tmp_path / "cert.pem"
    cert_file.write_text("dummy cert")
    result = runner.invoke(cli, ["--tls-cert", str(cert_file)])
    assert result.exit_code == 1
    assert "Error: Both --tls-cert and --tls-key must be provided for TLS." in result.output


def test_cli_invalid_path() -> None:
    """Verify that providing a non-existent TLS path exits 2."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--tls-cert", "does_not_exist.pem"])
    assert result.exit_code == 2
    assert "does not exist" in result.output.lower()
