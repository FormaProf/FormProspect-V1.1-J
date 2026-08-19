"""Deployment smoke check for Form@Prospect V1.1-J.

Exit 0 when the CRM endpoint exists (401/403 without a token is acceptable).
Exit 1 on 404 or network/server errors.
"""
from __future__ import annotations

import os
import sys
import requests

BASE_URL = os.getenv(
    "FORMAPROSPECT_API_BASE_URL", "https://api.forma-prof.fr/api/v1"
).rstrip("/")


def main() -> int:
    url = f"{BASE_URL}/prospects"
    try:
        response = requests.get(url, timeout=20)
    except requests.RequestException as exc:
        print(f"ECHEC connexion: {exc}")
        return 1

    print(f"GET {url} -> {response.status_code}")
    if response.status_code == 404:
        print("ECHEC: la route CRM n'est pas déployée.")
        return 1
    if response.status_code >= 500:
        print("ECHEC: erreur serveur.")
        return 1

    print("OK: la route CRM existe. Un statut 401/403 est normal sans jeton.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
