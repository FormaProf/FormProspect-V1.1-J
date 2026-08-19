from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as SyncPlaywrightError
from playwright.async_api import Error as AsyncPlaywrightError


class BrowserLaunchError(RuntimeError):
    """Erreur lisible lorsqu'aucun navigateur compatible ne peut être lancé."""


@dataclass(frozen=True)
class BrowserCandidate:
    name: str
    channel: str
    executable_paths: tuple[Path, ...]


class BrowserManager:
    """Lance un navigateur Chromium déjà installé sur Windows.

    L'ordre de préférence est Microsoft Edge, puis Google Chrome.
    La méthode ``launch`` conserve la compatibilité historique Sync.
    La méthode ``launch_async`` est utilisée par l'enrichisseur V2.2.
    """

    @staticmethod
    def _windows_candidates() -> tuple[BrowserCandidate, ...]:
        program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        program_files_x86 = Path(
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        )
        local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))

        return (
            BrowserCandidate(
                name="Microsoft Edge",
                channel="msedge",
                executable_paths=(
                    program_files_x86 / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    program_files / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                    local_app_data / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                ),
            ),
            BrowserCandidate(
                name="Google Chrome",
                channel="chrome",
                executable_paths=(
                    program_files / "Google" / "Chrome" / "Application" / "chrome.exe",
                    program_files_x86 / "Google" / "Chrome" / "Application" / "chrome.exe",
                    local_app_data / "Google" / "Chrome" / "Application" / "chrome.exe",
                ),
            ),
        )

    @classmethod
    def launch(cls, playwright: Any, headless: bool = False):
        """Compatibilité Sync pour les autres modules historiques."""
        errors: list[str] = []

        for candidate in cls._windows_candidates():
            try:
                return playwright.chromium.launch(
                    channel=candidate.channel,
                    headless=headless,
                )
            except SyncPlaywrightError as exc:
                errors.append(f"{candidate.name} (canal) : {exc}")

            for executable_path in candidate.executable_paths:
                if not executable_path.is_file():
                    continue
                try:
                    return playwright.chromium.launch(
                        executable_path=str(executable_path),
                        headless=headless,
                    )
                except SyncPlaywrightError as exc:
                    errors.append(
                        f"{candidate.name} ({executable_path}) : {exc}"
                    )

        details = "\n".join(errors[-4:]) if errors else "Aucun exécutable détecté."
        raise BrowserLaunchError(
            "Impossible de démarrer l'enrichissement.\n\n"
            "Form@Prospect nécessite Microsoft Edge ou Google Chrome. "
            "Installez ou mettez à jour l'un de ces navigateurs, puis réessayez.\n\n"
            f"Détails techniques :\n{details}"
        )

    @classmethod
    async def launch_async(cls, playwright: Any, headless: bool = False):
        """Version Async utilisée par Google Maps / PagesJaunes V2.2."""
        errors: list[str] = []

        for candidate in cls._windows_candidates():
            try:
                return await playwright.chromium.launch(
                    channel=candidate.channel,
                    headless=headless,
                )
            except AsyncPlaywrightError as exc:
                errors.append(f"{candidate.name} (canal) : {exc}")

            for executable_path in candidate.executable_paths:
                if not executable_path.is_file():
                    continue
                try:
                    return await playwright.chromium.launch(
                        executable_path=str(executable_path),
                        headless=headless,
                    )
                except AsyncPlaywrightError as exc:
                    errors.append(
                        f"{candidate.name} ({executable_path}) : {exc}"
                    )

        details = "\n".join(errors[-4:]) if errors else "Aucun exécutable détecté."
        raise BrowserLaunchError(
            "Impossible de démarrer l'enrichissement.\n\n"
            "Form@Prospect nécessite Microsoft Edge ou Google Chrome. "
            "Installez ou mettez à jour l'un de ces navigateurs, puis réessayez.\n\n"
            f"Détails techniques :\n{details}"
        )
