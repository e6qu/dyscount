import subprocess
import sys

def test_cli_version():
    """Test CLI version flag"""
    result = subprocess.run(
        [sys.executable, "-m", "dyscount_cli", "--version"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Dyscount" in result.stdout

def test_cli_help():
    """Test CLI help"""
    result = subprocess.run(
        [sys.executable, "-m", "dyscount_cli", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Dyscount" in result.stdout

def test_serve_help():
    """Test serve command help"""
    result = subprocess.run(
        [sys.executable, "-m", "dyscount_cli", "serve", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Start" in result.stdout

def test_config_help():
    """Test config command help"""
    result = subprocess.run(
        [sys.executable, "-m", "dyscount_cli", "config", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
