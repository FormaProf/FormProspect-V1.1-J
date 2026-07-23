from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


class KnowledgeEngineError(RuntimeError):
    """Erreur lisible liée au chargement de la base de connaissances."""


class FormAProfKnowledgeEngine:
    """Charge et interroge la base de connaissances locale Form@Prof.

    Les contenus sont stockés dans des fichiers JSON modifiables sans toucher au
    code Python. Aucune donnée n'est transmise à un service externe.
    """

    REQUIRED_FILES = (
        "company.json",
        "offers.json",
        "funding.json",
        "objections.json",
        "scripts.json",
        "faq.json",
        "case_studies.json",
    )

    def __init__(self, knowledge_dir: str | Path | None = None):
        self.knowledge_dir = Path(knowledge_dir) if knowledge_dir else Path(__file__).with_name("knowledge")
        self._documents: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        documents: dict[str, Any] = {}
        errors: list[str] = []
        for filename in self.REQUIRED_FILES:
            path = self.knowledge_dir / filename
            if not path.exists():
                errors.append(f"Fichier manquant : {filename}")
                continue
            try:
                with path.open("r", encoding="utf-8") as handle:
                    documents[path.stem] = json.load(handle)
            except json.JSONDecodeError as exc:
                errors.append(f"{filename} : JSON invalide ligne {exc.lineno}, colonne {exc.colno}")
            except OSError as exc:
                errors.append(f"{filename} : {exc}")
        if errors:
            raise KnowledgeEngineError("\n".join(errors))
        self._documents = documents

    def validate(self) -> list[str]:
        errors: list[str] = []
        expected = {
            "company": ("brand", "method", "promise"),
            "offers": ("offers",),
            "funding": ("mandatory_wording", "possible_funders"),
            "objections": ("objections",),
            "scripts": ("scripts", "qualification_questions"),
            "faq": ("items",),
            "case_studies": ("cases",),
        }
        for document, keys in expected.items():
            payload = self._documents.get(document)
            if not isinstance(payload, dict):
                errors.append(f"{document}.json doit contenir un objet JSON.")
                continue
            for key in keys:
                if key not in payload:
                    errors.append(f"{document}.json : clé obligatoire absente « {key} ».")
        return errors

    def document(self, name: str) -> dict[str, Any]:
        key = name.removesuffix(".json")
        if key not in self._documents:
            raise KeyError(f"Document inconnu : {name}")
        return deepcopy(self._documents[key])

    def company(self) -> dict[str, Any]:
        return self.document("company")

    def offers(self) -> list[dict[str, Any]]:
        return deepcopy(self._documents["offers"].get("offers", []))

    def funding(self) -> dict[str, Any]:
        return self.document("funding")

    def objections(self) -> list[dict[str, Any]]:
        return deepcopy(self._documents["objections"].get("objections", []))

    def scripts(self) -> list[dict[str, Any]]:
        return deepcopy(self._documents["scripts"].get("scripts", []))

    def qualification_questions(self) -> list[str]:
        return list(self._documents["scripts"].get("qualification_questions", []))

    def faq(self) -> list[dict[str, str]]:
        return deepcopy(self._documents["faq"].get("items", []))

    def case_studies(self, include_templates: bool = True) -> list[dict[str, Any]]:
        cases = deepcopy(self._documents["case_studies"].get("cases", []))
        if include_templates:
            return cases
        return [item for item in cases if item.get("status") != "MODELE_A_PERSONNALISER"]

    def find_objection(self, objection_id: str) -> dict[str, Any] | None:
        return next((item for item in self.objections() if item.get("id") == objection_id), None)

    def find_offer(self, offer_id: str) -> dict[str, Any] | None:
        return next((item for item in self.offers() if item.get("id") == offer_id), None)

    def search(self, query: str, limit: int = 10) -> list[dict[str, str]]:
        words = [word.casefold() for word in query.split() if len(word) >= 2]
        if not words:
            return []
        results: list[dict[str, str]] = []
        for document, payload in self._documents.items():
            text = json.dumps(payload, ensure_ascii=False)
            folded = text.casefold()
            score = sum(folded.count(word) for word in words)
            if score:
                results.append({"document": document, "score": str(score), "preview": text[:280]})
        results.sort(key=lambda item: int(item["score"]), reverse=True)
        return results[:max(1, min(limit, 50))]

    def prompt_context(self) -> str:
        company = self.company()
        funding = self.funding()
        offers = self.offers()
        objections = self.objections()
        lines = [
            f"MARQUE : {company.get('brand', 'Form@Prof')}",
            f"POSITIONNEMENT : {company.get('positioning', '')}",
            f"PROMESSE : {company.get('promise', '')}",
            "METHODE : " + " > ".join(company.get("method", [])),
            f"FINANCEMENT - FORMULATION OBLIGATOIRE : {funding.get('mandatory_wording', '')}",
            "OFFRES : " + " | ".join(item.get("name", "") for item in offers),
            "OBJECTIONS DISPONIBLES : " + " | ".join(item.get("prospect_says", "") for item in objections),
        ]
        return "\n".join(lines)

    def overview(self) -> str:
        errors = self.validate()
        company = self.company()
        lines = [
            "KNOWLEDGE ENGINE FORM@PROF",
            "",
            f"Marque : {company.get('brand', '')}",
            f"Documents chargés : {len(self._documents)}/{len(self.REQUIRED_FILES)}",
            f"Offres : {len(self.offers())}",
            f"Scripts : {len(self.scripts())}",
            f"Objections : {len(self.objections())}",
            f"Financeurs référencés : {len(self.funding().get('possible_funders', []))}",
            f"FAQ : {len(self.faq())}",
            f"Cas clients / modèles : {len(self.case_studies())}",
            "",
            "Statut : " + ("Base valide et opérationnelle." if not errors else "Erreurs détectées :"),
        ]
        lines.extend(f"- {error}" for error in errors)
        lines.extend([
            "",
            "Les contenus peuvent être modifiés dans services/ai/knowledge/*.json.",
            "Les changements sont pris en compte au prochain démarrage de Form@Prospect.",
        ])
        return "\n".join(lines)
