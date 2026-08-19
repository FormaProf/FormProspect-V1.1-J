from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import json
import re
import shutil


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--installer", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--notes-file", default="")
    parser.add_argument("--mandatory", action="store_true")
    parser.add_argument("--output-dir", default="release_publish")
    args = parser.parse_args()

    installer = Path(args.installer).resolve()
    if not installer.is_file():
        raise SystemExit(f"Installateur introuvable : {installer}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_version = re.sub(r"[^0-9A-Za-z._-]+", "_", args.version)
    published_name = f"Form@Prospect_Setup_v{safe_version}.exe"
    published_installer = output_dir / published_name
    shutil.copy2(installer, published_installer)

    notes = []
    notes_path = Path(args.notes_file) if args.notes_file else None
    if notes_path and notes_path.is_file():
        notes = [
            line.strip().lstrip("-• ").strip()
            for line in notes_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if not notes:
        notes = [f"Mise à jour Form@Prospect {args.version}"]

    base_url = args.base_url.rstrip("/")
    payload = {
        "version": args.version,
        "mandatory": bool(args.mandatory),
        "installer_url": f"{base_url}/{published_name}",
        "sha256": file_sha256(published_installer),
        "published_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "notes": notes,
    }

    (output_dir / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{published_name}.sha256").write_text(
        payload["sha256"] + "  " + published_name + "\n",
        encoding="utf-8",
    )

    print(f"Publication prête : {output_dir}")
    print(f"Installateur : {published_installer.name}")
    print("Manifeste : latest.json")
    print(f"SHA-256 : {payload['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
