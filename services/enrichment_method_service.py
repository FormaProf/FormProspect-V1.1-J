from __future__ import annotations

from dataclasses import dataclass


POLICY_ALWAYS = "always"
POLICY_IF_NO_USEFUL = "if_no_useful"
POLICY_IF_NO_PHONE = "if_no_phone"


@dataclass(frozen=True)
class EnrichmentMethodProfile:
    key: str
    label: str
    description: str
    engine_ready: bool
    uses_excel: bool = False
    google_policy: str = POLICY_ALWAYS
    annuaire_118000_policy: str = POLICY_ALWAYS
    web_policy: str = POLICY_ALWAYS
    site_analysis_limit: int = 2

    def should_run_google(self, *, has_useful: bool) -> bool:
        if self.google_policy == POLICY_ALWAYS:
            return True
        if self.google_policy == POLICY_IF_NO_USEFUL:
            return not has_useful
        raise ValueError(f"Politique Google Maps invalide : {self.google_policy!r}")

    def should_run_118000(self, *, has_phone: bool) -> bool:
        if self.annuaire_118000_policy == POLICY_ALWAYS:
            return True
        if self.annuaire_118000_policy == POLICY_IF_NO_PHONE:
            return not has_phone
        raise ValueError(
            f"Politique 118000 invalide : {self.annuaire_118000_policy!r}"
        )

    def should_run_web(self, *, has_useful: bool) -> bool:
        if self.web_policy == POLICY_ALWAYS:
            return True
        if self.web_policy == POLICY_IF_NO_USEFUL:
            return not has_useful
        raise ValueError(f"Politique WebFallback invalide : {self.web_policy!r}")


class EnrichmentMethodCatalog:
    """Décrit les quatre méthodes d'enrichissement de Form@Prospect.

    ``standard`` reproduit exactement le pipeline E6 existant. ``rapid`` réduit
    les appels complémentaires lorsque des coordonnées fiables sont déjà
    disponibles. ``deep`` conserve toutes les sources E6 et analyse davantage
    de sites validés. ``excel`` reste un flux séparé et ne lance jamais le
    moteur web.
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
                "Priorité à la vitesse : API + PagesJaunes d'abord, puis sources "
                "complémentaires uniquement si les données utiles manquent. "
                "Analyse jusqu'à 1 site validé."
            ),
            engine_ready=True,
            google_policy=POLICY_IF_NO_USEFUL,
            annuaire_118000_policy=POLICY_IF_NO_PHONE,
            web_policy=POLICY_IF_NO_USEFUL,
            site_analysis_limit=1,
        ),
        EnrichmentMethodProfile(
            key=STANDARD,
            label="⚖ Standard",
            description=(
                "Équilibre couverture / vitesse. Pipeline E6 actuel inchangé : "
                "toutes les sources complémentaires et jusqu'à 2 sites validés."
            ),
            engine_ready=True,
            google_policy=POLICY_ALWAYS,
            annuaire_118000_policy=POLICY_ALWAYS,
            web_policy=POLICY_ALWAYS,
            site_analysis_limit=2,
        ),
        EnrichmentMethodProfile(
            key=DEEP,
            label="🔎 Approfondi",
            description=(
                "Couverture maximale : pipeline E6 complet et analyse jusqu'à "
                "4 sites validés pour rechercher davantage d'emails et réseaux."
            ),
            engine_ready=True,
            google_policy=POLICY_ALWAYS,
            annuaire_118000_policy=POLICY_ALWAYS,
            web_policy=POLICY_ALWAYS,
            site_analysis_limit=4,
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
            site_analysis_limit=0,
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


class EnrichmentMethodRuntime:
    """Pont process-wide avec le Worker Qt existant.

    Le Worker actuel ne reçoit pas encore de paramètre ``strategy``. Comme un
    seul enrichissement peut être lancé à la fois et que le sélecteur UI est
    verrouillé pendant l'exécution, la méthode choisie peut être publiée ici
    juste avant le démarrage du QThread. EnrichmentService la lit ensuite au
    début de son exécution. Cela préserve le contrat du Worker et évite de
    toucher à un autre composant pendant le chantier E6.
    """

    _active_key = EnrichmentMethodCatalog.DEFAULT

    @classmethod
    def activate(cls, key: str | None) -> EnrichmentMethodProfile:
        profile = EnrichmentMethodCatalog.get(key)
        if profile.uses_excel:
            raise ValueError("La méthode Excel ne peut pas activer le moteur web.")
        if not profile.engine_ready:
            raise ValueError(f"Le moteur {profile.label} n'est pas disponible.")
        cls._active_key = profile.key
        return profile

    @classmethod
    def active_key(cls) -> str:
        return cls._active_key

    @classmethod
    def active_profile(cls) -> EnrichmentMethodProfile:
        return EnrichmentMethodCatalog.get(cls._active_key)

    @classmethod
    def reset(cls) -> None:
        cls._active_key = EnrichmentMethodCatalog.DEFAULT
