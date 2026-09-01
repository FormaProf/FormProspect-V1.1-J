from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnrichmentMethodProfile:
    key: str
    label: str
    description: str
    engine_ready: bool
    uses_excel: bool = False


class EnrichmentMethodCatalog:
    """Catalogue UI des méthodes d'enrichissement.

    Ce lot ne modifie pas encore le moteur web. Le profil ``standard``
    correspond donc exactement au comportement actuel. Les profils ``rapid``
    et ``deep`` sont déclarés mais restent verrouillés jusqu'au branchement du
    worker/service dans le lot suivant. ``excel`` route l'utilisateur vers le
    module Excel déjà disponible.
    """

    RAPID = "rapid"
    STANDARD = "standard"
    DEEP = "deep"
    EXCEL = "excel"
    DEFAULT = STANDARD

    _PROFILES = (
        EnrichmentMethodProfile(
            key=RAPID,
            label="⚡ Rapide",
            description=(
                "Priorité à la vitesse et aux sources les plus directes. "
                "Profil préparé ; activation du moteur au prochain lot."
            ),
            engine_ready=False,
        ),
        EnrichmentMethodProfile(
            key=STANDARD,
            label="⚖ Standard",
            description=(
                "Équilibre couverture / vitesse. C'est le comportement actuel "
                "du moteur Form@Prospect."
            ),
            engine_ready=True,
        ),
        EnrichmentMethodProfile(
            key=DEEP,
            label="🔎 Approfondi",
            description=(
                "Recherche multi-sources renforcée pour maximiser la couverture. "
                "Profil préparé ; activation du moteur au prochain lot."
            ),
            engine_ready=False,
        ),
        EnrichmentMethodProfile(
            key=EXCEL,
            label="📊 Excel",
            description=(
                "Met à jour les prospects existants à partir d'un fichier enrichi, "
                "par SIRET exact et sans supprimer les anciennes données."
            ),
            engine_ready=False,
            uses_excel=True,
        ),
    )

    @classmethod
    def profiles(cls) -> tuple[EnrichmentMethodProfile, ...]:
        return cls._PROFILES

    @classmethod
    def get(cls, key: str | None) -> EnrichmentMethodProfile:
        normalized = str(key or cls.DEFAULT).strip().lower()
        for profile in cls._PROFILES:
            if profile.key == normalized:
                return profile
        raise ValueError(f"Méthode d'enrichissement inconnue : {key!r}")

    @classmethod
    def engine_ready(cls, key: str | None) -> bool:
        return cls.get(key).engine_ready

    @classmethod
    def uses_excel(cls, key: str | None) -> bool:
        return cls.get(key).uses_excel
