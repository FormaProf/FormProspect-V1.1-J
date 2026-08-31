import json
import subprocess
import sys
from pathlib import Path


def test_build_update_manifest_includes_version(tmp_path):
    project_root = Path(__file__).resolve().parents[1]

    installer = tmp_path / "Form@Prospect_Setup.exe"
    installer.write_bytes(b"fake installer for test")

    output_dir = tmp_path / "release_publish"

    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "tools" / "build_update_manifest.py"),
            "--version",
            "V1.1-E.5",
            "--installer",
            str(installer),
            "--base-url",
            "https://example.test/releases",
            "--output-dir",
            str(output_dir),
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    manifest_path = output_dir / "latest.json"
    assert manifest_path.is_file()

    payload = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    assert payload["version"] == "V1.1-E.5"
    assert payload["installer_url"].startswith(
        "https://example.test/releases/"
    )
    assert len(payload["sha256"]) == 64