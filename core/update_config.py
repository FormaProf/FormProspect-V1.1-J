from __future__ import annotations

import os

# URL publique du manifeste de la dernière version.
# Le système peut être redirigé sans modifier le code grâce à la variable
# d'environnement FORMAPROSPECT_UPDATE_MANIFEST_URL.
UPDATE_MANIFEST_URL = os.getenv(
    "FORMAPROSPECT_UPDATE_MANIFEST_URL",
    "https://forma-prof.fr/formaprospect/releases/latest.json",
).strip()

UPDATE_CONNECT_TIMEOUT = 4
UPDATE_READ_TIMEOUT = 15
