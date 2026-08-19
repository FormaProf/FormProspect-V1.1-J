from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

LEGAL_WORDS = {
    "sas", "sasu", "sarl", "eurl", "sa", "scop", "sci", "ets",
    "etablissement", "etablissements", "entreprise", "societe", "ste",
    "groupe", "group", "france",
}


def _ascii(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize(value: str) -> str:
    value = _ascii(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def company_tokens(value: str) -> set[str]:
    return {t for t in normalize(value).split() if len(t) >= 2 and t not in LEGAL_WORDS}


def name_similarity(expected: str, candidate: str) -> float:
    a, b = normalize(expected), normalize(candidate)
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    ta, tb = company_tokens(a), company_tokens(b)
    overlap = len(ta & tb) / max(1, len(ta | tb))
    return max(ratio, overlap)


def address_similarity(expected: str, candidate: str) -> float:
    a, b = set(normalize(expected).split()), set(normalize(candidate).split())
    if not a or not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def digits(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def score_candidate(identity: dict, candidate: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    sim = name_similarity(identity.get("entreprise", ""), candidate.get("nom", ""))

    if sim >= 0.92:
        score += 55; reasons.append("nom très proche")
    elif sim >= 0.78:
        score += 42; reasons.append("nom proche")
    elif sim >= 0.62:
        score += 28; reasons.append("nom partiellement proche")
    elif candidate.get("nom"):
        score -= 45; reasons.append("nom différent")

    candidate_digits = digits(candidate.get("texte", ""))
    siret, siren = digits(identity.get("siret", "")), digits(identity.get("siren", ""))
    exact_id = False
    if siret and siret in candidate_digits:
        score += 100; reasons.append("SIRET exact"); exact_id = True
    elif siren and siren in candidate_digits:
        score += 75; reasons.append("SIREN exact"); exact_id = True

    expected_cp = normalize(identity.get("code_postal", ""))
    candidate_cp = normalize(candidate.get("code_postal", ""))
    raw = normalize(candidate.get("texte", ""))
    if expected_cp and candidate_cp:
        if expected_cp == candidate_cp:
            score += 22; reasons.append("code postal exact")
        else:
            score -= 35; reasons.append("code postal différent")
    elif expected_cp and expected_cp in raw:
        score += 18; reasons.append("code postal présent")

    expected_city = normalize(identity.get("ville", ""))
    candidate_city = normalize(candidate.get("ville", ""))
    if expected_city and candidate_city:
        if expected_city == candidate_city:
            score += 16; reasons.append("ville exacte")
        else:
            score -= 25; reasons.append("ville différente")
    elif expected_city and expected_city in raw:
        score += 12; reasons.append("ville présente")

    addr_sim = address_similarity(identity.get("adresse", ""), candidate.get("adresse", ""))
    if addr_sim >= 0.65:
        score += 22; reasons.append("adresse proche")
    elif addr_sim >= 0.40:
        score += 12; reasons.append("adresse partiellement proche")

    if candidate.get("nom") and sim < 0.45 and not exact_id:
        score = min(score, 25)

    return score, reasons


def confidence(score: int) -> str:
    if score >= 65:
        return "validated"
    if score >= 50:
        return "review"
    return "rejected"
