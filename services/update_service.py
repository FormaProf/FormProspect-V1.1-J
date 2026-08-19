from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import os
import re
import subprocess
import tempfile
from typing import Callable
from urllib.parse import urlparse

import requests

from core.update_config import (
    UPDATE_CONNECT_TIMEOUT,
    UPDATE_MANIFEST_URL,
    UPDATE_READ_TIMEOUT,
)


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    installer_url: str
    sha256: str
    mandatory: bool = False
    notes: tuple[str, ...] = ()
    published_at: str = ""


def _version_key(value: str) -> tuple:
    """
    Comparateur tolérant les versions actuelles de Form@Prospect :
    1.1-E.1, V1.1-E.2, 1.2.0, etc.
    """
    cleaned = str(value or "").strip().lstrip("vV")
    tokens = re.findall(r"\d+|[A-Za-z]+", cleaned)
    key: list[tuple[int, object]] = []
    for token in tokens:
        if token.isdigit():
            key.append((2, int(token)))
        else:
            key.append((1, token.lower()))
    return tuple(key)


class UpdateService:
    def __init__(
        self,
        current_version: str,
        manifest_url: str = UPDATE_MANIFEST_URL,
    ) -> None:
        self.current_version = str(current_version or "").strip()
        self.manifest_url = str(manifest_url or "").strip()

    def check_for_update(self) -> UpdateInfo | None:
        if not self.manifest_url:
            return None

        try:
            response = requests.get(
                self.manifest_url,
                timeout=(UPDATE_CONNECT_TIMEOUT, UPDATE_READ_TIMEOUT),
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"Form@Prospect/{self.current_version}",
                    "Cache-Control": "no-cache",
                },
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise UpdateError(
                "Impossible de vérifier les mises à jour pour le moment."
            ) from exc

        version = str(payload.get("version") or "").strip()
        installer_url = str(payload.get("installer_url") or "").strip()
        expected_hash = str(payload.get("sha256") or "").strip().lower()

        if not version or not installer_url or not expected_hash:
            raise UpdateError("Le manifeste de mise à jour est incomplet.")

        parsed = urlparse(installer_url)
        if parsed.scheme.lower() != "https":
            raise UpdateError(
                "La mise à jour a été refusée : l'installateur doit être téléchargé en HTTPS."
            )

        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise UpdateError("L'empreinte SHA-256 publiée est invalide.")

        if _version_key(version) <= _version_key(self.current_version):
            return None

        notes = payload.get("notes") or []
        if isinstance(notes, str):
            notes = [notes]
        clean_notes = tuple(
            str(item).strip() for item in notes if str(item).strip()
        )

        return UpdateInfo(
            version=version,
            installer_url=installer_url,
            sha256=expected_hash,
            mandatory=bool(payload.get("mandatory", False)),
            notes=clean_notes,
            published_at=str(payload.get("published_at") or "").strip(),
        )

    def download_installer(
        self,
        info: UpdateInfo,
        progress_callback: Callable[[int, int], bool | None] | None = None,
    ) -> Path:
        update_dir = Path(
            os.getenv(
                "LOCALAPPDATA",
                tempfile.gettempdir(),
            )
        ) / "Form@Prospect" / "Updates"
        update_dir.mkdir(parents=True, exist_ok=True)

        safe_version = re.sub(r"[^0-9A-Za-z._-]+", "_", info.version)
        final_path = update_dir / f"Form@Prospect_Setup_{safe_version}.exe"
        partial_path = final_path.with_suffix(".download")

        digest = sha256()
        downloaded = 0

        try:
            with requests.get(
                info.installer_url,
                stream=True,
                timeout=(UPDATE_CONNECT_TIMEOUT, 60),
                headers={
                    "User-Agent": f"Form@Prospect/{self.current_version}",
                    "Cache-Control": "no-cache",
                },
            ) as response:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length") or 0)

                with partial_path.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)

                        if progress_callback is not None:
                            keep_going = progress_callback(downloaded, total)
                            if keep_going is False:
                                raise UpdateError("Téléchargement annulé.")

            actual_hash = digest.hexdigest().lower()
            if actual_hash != info.sha256.lower():
                raise UpdateError(
                    "La mise à jour téléchargée ne correspond pas à l'empreinte "
                    "de sécurité publiée. Installation annulée."
                )

            if final_path.exists():
                final_path.unlink()
            partial_path.replace(final_path)
            return final_path

        except UpdateError:
            partial_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            partial_path.unlink(missing_ok=True)
            raise UpdateError(
                "Le téléchargement de la mise à jour a échoué."
            ) from exc

    @staticmethod
    def launch_installer(installer_path: Path) -> None:
        installer_path = Path(installer_path)
        if not installer_path.is_file():
            raise UpdateError("L'installateur téléchargé est introuvable.")

        try:
            subprocess.Popen(
                [
                    str(installer_path),
                    "/CLOSEAPPLICATIONS",
                    "/RESTARTAPPLICATIONS",
                ],
                cwd=str(installer_path.parent),
                close_fds=True,
            )
        except Exception as exc:
            raise UpdateError(
                "Impossible de lancer l'installateur de mise à jour."
            ) from exc
