from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher

LEGAL_WORDS = {
    "sas", "sasu", "sarl", "eurl", "sa", "scop", "sci", "ets",
    "etablissement", "etablissements", "entreprise", "societe", "ste",
    "groupe", "group", "france",
}

GENERIC_SHORT_ALIASES = {
    "btp", "tp", "bat", "batiment", "construction", "services", "service",
}


def _ascii(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize(value: str) -> str:
    value = _ascii(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _compact_acronym(value: str) -> str:
    """Compacte les sigles écrits lettre par lettre (``C T O`` -> ``CTO``)."""
    tokens = normalize(value).split()
    if 2 <= len(tokens) <= 8 and all(len(token) == 1 for token in tokens):
        return "".join(tokens).upper()
    return ""


def identity_names(identity: dict) -> list[str]:
    """Retourne le nom principal et les noms publics alternatifs du prospect.

    Lot 2.2 : les noms hérités d'autres établissements du même SIREN peuvent
    être présents dans ``noms_recherche``. Les sigles espacés sont également
    compactés afin que ``C T O`` puisse retrouver une fiche publiée sous
    ``CTO`` / ``Cto``.
    """
    names: list[str] = []
    raw_aliases = identity.get("noms_recherche", [])
    if isinstance(raw_aliases, str):
        raw_aliases = raw_aliases.strip()
        if raw_aliases:
            try:
                parsed = json.loads(raw_aliases)
                raw_aliases = parsed if isinstance(parsed, list) else [raw_aliases]
            except Exception:
                raw_aliases = [x.strip() for x in raw_aliases.split("\n") if x.strip()]
        else:
            raw_aliases = []

    for value in list(raw_aliases or []) + [identity.get("entreprise", "")]:
        value = str(value or "").strip()
        key = normalize(value)
        if value and key and all(normalize(existing) != key for existing in names):
            names.append(value)

        compact = _compact_acronym(value)
        compact_key = normalize(compact)
        if (
            compact
            and compact_key
            and all(normalize(existing) != compact_key for existing in names)
        ):
            names.append(compact)
    return names


def identity_locations(identity: dict) -> list[dict]:
    """Retourne les localisations connues du SIRET et de son unité légale.

    La première localisation est toujours celle du prospect courant. Les
    suivantes proviennent des autres établissements locaux ayant le même SIREN.
    """
    raw_locations = identity.get("localisations_recherche", [])
    if isinstance(raw_locations, str):
        raw_locations = raw_locations.strip()
        if raw_locations:
            try:
                parsed = json.loads(raw_locations)
                raw_locations = parsed if isinstance(parsed, list) else []
            except Exception:
                raw_locations = []
        else:
            raw_locations = []

    candidates = [
        {
            "adresse": identity.get("adresse", ""),
            "code_postal": identity.get("code_postal", ""),
            "ville": identity.get("ville", ""),
        }
    ] + [item for item in (raw_locations or []) if isinstance(item, dict)]

    locations: list[dict] = []
    seen = set()
    for item in candidates:
        address = str(item.get("adresse") or "").strip()
        cp = str(item.get("code_postal") or "").strip()
        city = str(item.get("ville") or "").strip()
        key = (normalize(address), normalize(cp), normalize(city))
        if not any(key) or key in seen:
            continue
        seen.add(key)
        locations.append(
            {"adresse": address, "code_postal": cp, "ville": city}
        )
    return locations


def _alias_similarity(expected: str, candidate: str) -> float:
    sim = name_similarity(expected, candidate)
    a, b = normalize(expected), normalize(candidate)
    if not a or not b:
        return sim

    # Une enseigne/sigle distinctif peut être inclus dans un libellé plus long
    # (ex. CIPA -> Agence Etoile Cipa). On évite de survaloriser les alias
    # génériques tels que BTP ou TP.
    compact = a.replace(" ", "")
    if (
        len(compact) >= 4
        and a not in GENERIC_SHORT_ALIASES
        and re.search(rf"(?:^| )\b{re.escape(a)}\b(?: |$)", b)
    ):
        sim = max(sim, 0.94)
    return sim


def best_identity_name_similarity(identity: dict, candidate_name: str) -> tuple[float, str]:
    best_score = 0.0
    best_name = ""
    for expected in identity_names(identity):
        sim = _alias_similarity(expected, candidate_name)
        if sim > best_score:
            best_score = sim
            best_name = expected
    return best_score, best_name


def company_tokens(value: str) -> set[str]:
    return {
        token
        for token in normalize(value).split()
        if len(token) >= 2 and token not in LEGAL_WORDS
    }


def name_similarity(expected: str, candidate: str) -> float:
    a, b = normalize(expected), normalize(candidate)
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    ta, tb = company_tokens(a), company_tokens(b)
    overlap = len(ta & tb) / max(1, len(ta | tb))
    return max(ratio, overlap)


def address_similarity(expected: str, candidate: str) -> float:
    a = set(normalize(expected).split())
    b = set(normalize(candidate).split())
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _best_location_signals(identity: dict, candidate: dict) -> dict:
    """Compare une fiche à toutes les adresses connues du même SIREN."""
    candidate_cp = normalize(candidate.get("code_postal", ""))
    candidate_city = normalize(candidate.get("ville", ""))
    candidate_address = candidate.get("adresse", "")
    raw = normalize(candidate.get("texte", ""))

    best = {
        "cp_exact": False,
        "cp_in_raw": False,
        "city_exact": False,
        "city_in_raw": False,
        "address_similarity": 0.0,
    }
    for location in identity_locations(identity):
        expected_cp = normalize(location.get("code_postal", ""))
        expected_city = normalize(location.get("ville", ""))
        expected_address = location.get("adresse", "")

        if expected_cp:
            best["cp_exact"] = best["cp_exact"] or bool(
                candidate_cp and expected_cp == candidate_cp
            )
            best["cp_in_raw"] = best["cp_in_raw"] or expected_cp in raw
        if expected_city:
            best["city_exact"] = best["city_exact"] or bool(
                candidate_city and expected_city == candidate_city
            )
            best["city_in_raw"] = best["city_in_raw"] or expected_city in raw
        best["address_similarity"] = max(
            best["address_similarity"],
            address_similarity(expected_address, candidate_address),
        )
    return best


def score_candidate(identity: dict, candidate: dict) -> tuple[int, list[str]]:
    """Évalue si une fiche publique correspond au prospect attendu.

    Lot 2.2 : un résultat peut appartenir au siège ou à un autre établissement
    de la même unité légale. Le SIREN reste alors le signal fort, et les noms /
    adresses mutualisés du groupe SIREN peuvent également valider la fiche.
    """
    score = 0
    reasons: list[str] = []

    candidate_digits = digits(candidate.get("texte", ""))
    siret = digits(identity.get("siret", ""))
    siren = digits(identity.get("siren", ""))

    # Identifiant établissement exact : validation immédiate et prioritaire.
    if len(siret) == 14 and siret in candidate_digits:
        return 200, ["SIRET exact"]

    # Identifiant unité légale exact : signal très fort. Un SIRET d'un autre
    # établissement contient également les neuf chiffres du SIREN.
    siren_exact = len(siren) == 9 and siren in candidate_digits
    if siren_exact:
        score += 90
        reasons.append("SIREN exact")

    sim, matched_name = best_identity_name_similarity(
        identity,
        candidate.get("nom", ""),
    )
    alias_match = bool(
        matched_name
        and normalize(matched_name) != normalize(identity.get("entreprise", ""))
    )
    reason_prefix = "enseigne/alias" if alias_match else "nom"

    if sim >= 0.92:
        score += 55
        reasons.append(f"{reason_prefix} très proche")
    elif sim >= 0.78:
        score += 42
        reasons.append(f"{reason_prefix} proche")
    elif sim >= 0.62:
        score += 28
        reasons.append(f"{reason_prefix} partiellement proche")
    elif candidate.get("nom") and not siren_exact:
        score -= 45
        reasons.append("nom différent")

    locations = identity_locations(identity)
    location_signals = _best_location_signals(identity, candidate)
    candidate_cp = normalize(candidate.get("code_postal", ""))
    candidate_city = normalize(candidate.get("ville", ""))

    if locations:
        has_expected_cp = any(normalize(x.get("code_postal", "")) for x in locations)
        if has_expected_cp:
            if location_signals["cp_exact"]:
                score += 22
                reasons.append("code postal exact")
            elif location_signals["cp_in_raw"]:
                score += 18
                reasons.append("code postal présent")
            elif candidate_cp and not siren_exact:
                score -= 35
                reasons.append("code postal différent")

        has_expected_city = any(normalize(x.get("ville", "")) for x in locations)
        if has_expected_city:
            if location_signals["city_exact"]:
                score += 16
                reasons.append("ville exacte")
            elif location_signals["city_in_raw"]:
                score += 12
                reasons.append("ville présente")
            elif candidate_city and not siren_exact:
                score -= 25
                reasons.append("ville différente")

    addr_sim = location_signals["address_similarity"]
    if addr_sim >= 0.65:
        score += 22
        reasons.append("adresse proche")
    elif addr_sim >= 0.40:
        score += 12
        reasons.append("adresse partiellement proche")

    if candidate.get("nom") and sim < 0.45 and not siren_exact:
        score = min(score, 25)

    return score, reasons


def confidence(score: int) -> str:
    if score >= 65:
        return "validated"
    if score >= 50:
        return "review"
    return "rejected"
