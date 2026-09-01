from __future__ import annotations


FIELD_LABELS = {
    "entreprise": "Entreprise",
    "telephone": "Téléphones",
    "mobile": "Mobiles",
    "email": "Emails",
    "site_web": "Sites web",
    "linkedin": "LinkedIn",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "youtube": "YouTube",
    "adresse": "Adresses",
    "code_postal": "Codes postaux",
    "ville": "Villes",
    "code_naf": "Codes NAF / APE",
}

ACTION_LABELS = {
    "completer": "à compléter",
    "fusionner": "à fusionner",
    "verifier": "conflit à vérifier",
}


def build_excel_update_preview_text(stats: dict, *, detail_limit: int = 20) -> str:
    """Construit le texte de prévisualisation d'une comparaison Excel.

    Cette fonction ne fait aucune lecture de fichier et aucune écriture. Elle
    présente uniquement le dictionnaire retourné par
    ``ProspectExcelUpdateService.comparer_avec_sqlite``.
    """
    if detail_limit < 0:
        raise ValueError("detail_limit doit être supérieur ou égal à 0.")

    potential = dict(stats.get("modifications_potentielles") or {})
    lines = [
        "APERÇU DE LA MISE À JOUR EXCEL — LECTURE SEULE",
        "",
        f"Fichier : {stats.get('fichier') or '—'}",
        "Clé de correspondance : SIRET exact uniquement",
        "Création automatique de prospects : NON",
        "Suppression de données existantes : NON",
        "",
        "CORRESPONDANCES",
        f"Lignes Excel : {_as_int(stats.get('lignes_excel'))}",
        f"Prospects retrouvés par SIRET : {_as_int(stats.get('correspondances_siret'))}",
        f"SIRET introuvables : {_as_int(stats.get('introuvables'))}",
        f"SIRET absents : {_as_int(stats.get('sans_siret'))}",
        f"SIRET invalides : {_as_int(stats.get('siret_invalides'))}",
        f"SIRET ambigus dans la base : {_as_int(stats.get('ambigus_siret'))}",
        f"Lignes ignorées (SIRET/SIREN incohérents) : {_as_int(stats.get('ignores_incoherents'))}",
        f"Déjà à jour : {_as_int(stats.get('lignes_sans_changement'))}",
        "",
        "NOUVELLES INFORMATIONS DÉTECTÉES",
    ]

    ordered_fields = (
        "telephone",
        "mobile",
        "email",
        "site_web",
        "linkedin",
        "facebook",
        "instagram",
        "youtube",
        "entreprise",
        "adresse",
        "code_postal",
        "ville",
        "code_naf",
    )
    any_field = False
    for field in ordered_fields:
        count = _as_int(potential.get(field))
        if count:
            any_field = True
            lines.append(f"{FIELD_LABELS.get(field, field)} : {count}")
    if not any_field:
        lines.append("Aucune nouvelle information détectée.")

    lines.extend(
        [
            "",
            "SYNTHÈSE DES ACTIONS POTENTIELLES",
            f"Champs vides à compléter : {_as_int(stats.get('champs_vides_a_completer'))}",
            f"Valeurs à fusionner sans doublon : {_as_int(stats.get('valeurs_a_fusionner'))}",
            f"Conflits conservés pour vérification : {_as_int(stats.get('conflits_a_verifier'))}",
            "",
            "Aucune modification n'a été effectuée.",
        ]
    )

    preview = list(stats.get("apercu") or [])
    if detail_limit and preview:
        lines.extend(["", "DÉTAIL DE L'APERÇU"])
        for item in preview[:detail_limit]:
            company = str(item.get("entreprise") or "Prospect sans nom").strip()
            siret = str(item.get("siret") or "—").strip()
            excel_line = item.get("ligne_excel")
            lines.append("")
            lines.append(
                f"• {company} — SIRET {siret}"
                + (f" — ligne Excel {excel_line}" if excel_line else "")
            )
            for diff in item.get("differences") or []:
                source = str(diff.get("champ_source") or "").strip()
                label = FIELD_LABELS.get(source, source or "Information")
                action = ACTION_LABELS.get(
                    str(diff.get("action") or "").strip(),
                    str(diff.get("action") or "à vérifier").strip(),
                )
                values = [
                    str(value).strip()
                    for value in (diff.get("valeurs_excel") or [])
                    if str(value).strip()
                ]
                incoming = " ; ".join(values) or "—"
                lines.append(f"  - {label} ({action}) : {incoming}")

        remaining = len(preview) - min(detail_limit, len(preview))
        if remaining > 0:
            lines.append("")
            lines.append(f"… {remaining} autre(s) prospect(s) dans l'aperçu.")

    return "\n".join(lines)


def _as_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
