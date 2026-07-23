from __future__ import annotations

from .knowledge_engine import FormAProfKnowledgeEngine

_ENGINE = FormAProfKnowledgeEngine()


class FormAProfKnowledge:
    """Couche de compatibilité utilisée par l'Assistant IA existant."""

    BRAND = _ENGINE.company().get("brand", "Form@Prof – Up Your Skills")
    FUNDING_WORDING = _ENGINE.funding().get("mandatory_wording", "")
    QUALITY_SUPPORT = (
        "Nous assurons également un accompagnement qualité pendant douze mois afin "
        "de vérifier que l'outil répond toujours aux besoins, de réaliser les ajustements "
        "utiles et de nous assurer qu'il fonctionne correctement."
    )
    BUSINESS_BENEFITS = (
        "centraliser les devis, chantiers, règlements et relances",
        "suivre le chiffre d'affaires, les marges et la rentabilité",
        "réduire les doubles saisies et les tâches administratives",
        "obtenir des indicateurs clairs pour prendre de meilleures décisions",
    )
    QUALIFICATION_QUESTIONS = tuple(_ENGINE.qualification_questions())

    OBJECTIONS = {}
    _mapping = {
        "already_excel": "excel",
        "already_erp": "erp",
        "no_time": "temps",
        "too_expensive": "prix",
        "no_need": "pas_besoin",
    }
    for _item in _ENGINE.objections():
        _legacy_key = _mapping.get(_item.get("id"))
        if _legacy_key:
            OBJECTIONS[_legacy_key] = _item.get("response", "")

    @classmethod
    def engine(cls) -> FormAProfKnowledgeEngine:
        return _ENGINE

    @classmethod
    def reload(cls) -> None:
        _ENGINE.reload()
