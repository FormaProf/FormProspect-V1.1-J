from __future__ import annotations

import re
import unicodedata

PHONE_RE = re.compile(
    r"(?<!\d)(?:\+33|0033|0)\s*[1-9](?:[\s.\-]?\d{2}){4}(?!\d)"
)


def _plain(value: str) -> str:
    value = str(value or "").lower()
    value = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in value if not unicodedata.combining(ch))


def normalize_fr_phone(value: str) -> str:
    raw = str(value or "").strip()
    compact = re.sub(r"\D", "", raw)

    if compact.startswith("0033") and len(compact) == 13:
        compact = "0" + compact[4:]
    elif compact.startswith("33") and len(compact) == 11:
        compact = "0" + compact[2:]

    if (
        len(compact) == 10
        and compact.startswith("0")
        and compact[1] in "123456789"
    ):
        return " ".join(compact[i:i + 2] for i in range(0, 10, 2))
    return ""


def _last_hint_position(text: str, hints: tuple[str, ...]) -> int:
    positions = [text.rfind(hint) for hint in hints]
    return max(positions) if positions else -1


def classify_phone_context(text: str, start: int, end: int, number: str) -> str:
    """Classe un numéro grâce au libellé le plus proche avant celui-ci."""
    source = str(text or "")
    before = _plain(source[max(0, start - 65):start])
    after = _plain(source[end:min(len(source), end + 25)])

    fax_pos = _last_hint_position(before, ("fax", "telecopie", "facsimile"))
    mobile_pos = _last_hint_position(before, ("mobile", "portable"))
    phone_pos = _last_hint_position(before, ("telephone", "tel :", "tel:", "tel."))

    # Le libellé le plus proche du nombre l'emporte. Cela évite qu'un ancien
    # « Fax » plus haut dans la ligne contamine le téléphone suivant.
    nearest = max(fax_pos, mobile_pos, phone_pos)
    if nearest == fax_pos and fax_pos >= 0:
        return "fax"
    if nearest == mobile_pos and mobile_pos >= 0:
        return "mobile"

    normalized = normalize_fr_phone(number)
    if normalized.replace(" ", "").startswith(("06", "07")):
        return "mobile"

    return "phone"


def extract_phones_from_text(
    text: str,
    *,
    require_contact_hint: bool = False,
) -> dict[str, list[str]]:
    """Extrait seulement les coordonnées téléphoniques plausibles.

    Quand `require_contact_hint` est vrai (fallback sur le corps complet d'une
    page), un numéro fixe n'est conservé que si un mot de contact se trouve à
    proximité. Cela évite d'aspirer des numéros techniques ou administratifs.
    """
    source = str(text or "")
    result = {"phone": [], "mobile": [], "fax": []}
    seen = set()

    for match in PHONE_RE.finditer(source):
        normalized = normalize_fr_phone(match.group(0))
        if not normalized:
            continue

        compact = normalized.replace(" ", "")
        if compact in seen:
            continue

        before = _plain(source[max(0, match.start() - 80):match.start()])
        after = _plain(source[match.end():min(len(source), match.end() + 40)])
        context = f"{before} {after}"

        administrative_hints = ("siret", "siren", "tva", "code ape", "naf")
        contact_hints = (
            "telephone", "tel :", "tel:", "tel.", "contact", "appeler",
            "numero", "standard", "accueil", "mobile", "portable",
            "fax", "telecopie",
        )
        admin_pos = _last_hint_position(before, administrative_hints)
        contact_pos = _last_hint_position(before, contact_hints)
        if admin_pos >= 0 and admin_pos > contact_pos:
            continue

        kind = classify_phone_context(
            source,
            match.start(),
            match.end(),
            match.group(0),
        )

        if require_contact_hint and kind == "phone":
            if contact_pos < 0:
                continue

        seen.add(compact)
        result[kind].append(normalized)

    return result


def merge_contact_numbers(*texts: str) -> dict[str, list[str]]:
    merged = {"phone": [], "mobile": [], "fax": []}
    seen = {"phone": set(), "mobile": set(), "fax": set()}
    for text in texts:
        extracted = extract_phones_from_text(text)
        for kind in merged:
            for number in extracted[kind]:
                compact = number.replace(" ", "")
                if compact not in seen[kind]:
                    seen[kind].add(compact)
                    merged[kind].append(number)
    return merged
