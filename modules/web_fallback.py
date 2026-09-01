from __future__ import annotations

import concurrent.futures
import re
import threading
from urllib.parse import parse_qs, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from modules.company_matcher import (
    confidence,
    identity_locations,
    identity_names,
    normalize,
    score_candidate,
)
from modules.contact_quality import extract_phones_from_text
from modules.email_finder import EmailFinder


class WebFallbackFinder:
    """Recherche web légère utilisée uniquement en dernier recours.

    Le moteur interroge DuckDuckGo HTML (sans clé API), ouvre quelques résultats
    publics et réutilise le score d'identité de Form@Prospect. Une page n'est
    donc exploitée que si elle correspond suffisamment au prospect attendu.
    """

    SEARCH_URL = "https://html.duckduckgo.com/html/"
    SEARCH_TIMEOUT = 6
    PAGE_TIMEOUT = 7
    MAX_QUERIES = 3
    MAX_RESULT_URLS = 5
    MAX_FETCHES = 4

    DIRECTORY_DOMAINS = {
    # Moteurs de recherche
        "google.com",
        "google.fr",
        "bing.com",
        "duckduckgo.com",

    # Annuaires / agrégateurs / bases entreprises
        "pagesjaunes.fr",
        "pappers.fr",
        "societe.com",
        "entreprises.lefigaro.fr",
        "annuaire-entreprises.data.gouv.fr",
        "annuaire-entreprises-rge.fr",
        "allbiz.fr",
        "cylex-locale.fr",
        "118000.fr",
        "118712.fr",
        "verif.com",
        "manageo.fr",
        "infogreffe.fr",
        "le-site-de.com",
        "hoodspot.fr",
        "kompass.com",
        "solocal.com",
        "monartisan.info",
        "batico.fr",
        "lookup.robokiller.com",
        "numlookup.com",
        "thisnumber.com",
    }

    SOCIAL_DOMAINS = {
        "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
        "twitter.com", "x.com", "tiktok.com",
    }

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        }
        self.last_errors: list[str] = []
        self._search_metadata: dict[str, dict] = {}
        self._search_metadata_lock = threading.Lock()

    @staticmethod
    def _host(url: str) -> str:
        try:
            host = (urlparse(url).hostname or "").lower().strip(".")
        except Exception:
            return ""
        return host[4:] if host.startswith("www.") else host

    @classmethod
    def _domain_matches(cls, host: str, domains: set[str]) -> bool:
        return any(host == domain or host.endswith("." + domain) for domain in domains)

    @classmethod
    def _is_official_candidate_domain(cls, url: str) -> bool:
        host = cls._host(url)
        if not host:
            return False
        return not (
            cls._domain_matches(host, cls.DIRECTORY_DOMAINS)
            or cls._domain_matches(host, cls.SOCIAL_DOMAINS)
        )

    @classmethod
    def _is_official_candidate_url(cls, url: str) -> bool:
        """Écarte les fiches annuaire/SEO même si leur domaine paraît normal.

        Exemple réel : ``fernandesclimatisation.com/entreprise/<siren>-decam``
        est une fiche générée autour de DECAM, pas le site officiel de DECAM.
        """
        if not cls._is_official_candidate_domain(url):
            return False

        try:
            parsed = urlparse(str(url or ""))
            path = (parsed.path or "/").lower()
        except Exception:
            return False

        segments = [segment for segment in path.split("/") if segment]
        profile_markers = {
            "annuaire",
            "business",
            "companies",
            "company",
            "entreprise",
            "entreprises",
            "etablissement",
            "etablissements",
            "fiche",
            "professionnel",
            "professionnels",
            "societe",
            "societes",
        }
        if any(segment in profile_markers for segment in segments):
            return False

        # Les agrégateurs SEO utilisent souvent un SIREN/SIRET directement
        # dans le slug. Un domaine d'entreprise réel reste accepté sur sa
        # racine et ses pages ordinaires.
        if re.search(r"(?:^|[-_/])\d{9}(?:\d{5})?(?:[-_/]|$)", path):
            return False

        return True

    @classmethod
    def _is_official_site_for_identity(cls, url: str, identity: dict) -> bool:
        """N'auto-promeut un domaine que s'il ressemble au nom/alias attendu.

        Une fiche SEO peut reprendre exactement le nom, le SIRET et la ville
        d'une entreprise tout en vivant sur un domaine générique sans rapport
        avec elle. Comme Form@Prospect préfère une absence de site à un faux
        positif, un domaine sans lien lexical avec les noms connus n'est pas
        considéré comme site officiel.
        """
        if not cls._is_official_candidate_url(url):
            return False

        host = cls._host(url)
        if not host:
            return False

        # Domaine principal sans TLD, tirets/points normalisés comme le reste du
        # moteur. Ex.: decam.fr -> "decam".
        host_label = host.split(".")[0]
        normalized_host = normalize(host_label)
        if not normalized_host:
            return False

        for name in identity_names(identity):
            normalized_name = normalize(name)
            if not normalized_name:
                continue

            # Les espaces de normalize permettent de comparer aussi les raisons
            # sociales composées avec les domaines utilisant des tirets.
            host_compact = normalized_host.replace(" ", "")
            name_compact = normalized_name.replace(" ", "")
            if (
                host_compact == name_compact
                or (
                    len(name_compact) >= 4
                    and name_compact in host_compact
                )
                or (
                    len(host_compact) >= 4
                    and host_compact in name_compact
                )
            ):
                return True

        return False

    @staticmethod
    def _clean_result_url(href: str) -> str:
        href = str(href or "").strip()
        if not href:
            return ""
        if href.startswith("//"):
            href = "https:" + href
        parsed = urlparse(href)
        if "duckduckgo.com" in (parsed.hostname or ""):
            qs = parse_qs(parsed.query)
            uddg = (qs.get("uddg") or [""])[0]
            if uddg:
                return uddg
        return href if href.startswith(("http://", "https://")) else ""

    @staticmethod
    def _empty(errors=None):
        return {
            "source": "web_fallback",
            "source_detail": "",
            "nom": "",
            "adresse": "",
            "code_postal": "",
            "ville": "",
            "telephones": [],
            "faxes": [],
            "site_web": "",
            "email": "",
            "texte": "",
            "match_score": 0,
            "match_reasons": [],
            "confidence": "rejected",
            "technical_errors": list(errors or []),
        }

    @staticmethod
    def _query_plan(identity: dict) -> list[str]:
        names = identity_names(identity)
        locations = identity_locations(identity)
        if not names:
            return []

        queries = []
        primary_name = names[0]
        current_location = locations[0] if locations else {}

        # 1. Recherche contact sur l'implantation actuelle.
        current_where = " ".join(
            value
            for value in (
                str(current_location.get("code_postal") or "").strip(),
                str(current_location.get("ville") or "").strip(),
            )
            if value
        )
        current_query = " ".join(
            value
            for value in (primary_name, current_where)
            if value
        )
        if current_query:
            queries.append(f"{current_query} téléphone")

        # 2. Recherche exacte par SIRET.
        siret = re.sub(r"\D", "", str(identity.get("siret") or ""))
        if len(siret) == 14:
            queries.append(siret)

        # 3. Si une implantation historique est déjà connue, elle occupe le
        # troisième axe. Sinon on réserve ce troisième axe à la découverte
        # d'identité/historique, sans le mot "téléphone". Ce type de requête
        # remonte beaucoup mieux les pages légales (Societe.com, etc.) qui
        # peuvent contenir les anciens établissements.
        current_cp = str(current_location.get("code_postal") or "").strip()
        current_city = str(current_location.get("ville") or "").strip().lower()

        historical_query_added = False
        for location in locations[1:]:
            cp = str(location.get("code_postal") or "").strip()
            city = str(location.get("ville") or "").strip()

            if not cp and not city:
                continue
            if cp == current_cp and city.lower() == current_city:
                continue

            address = str(location.get("adresse") or "").strip()
            # Certaines API renvoient déjà "CP VILLE" dans adresse.
            # On évite donc de produire "... 92300 LEVALLOIS-PERRET 92300
            # LEVALLOIS-PERRET" dans la requête web.
            suffix_pattern = r"\s+".join(
                re.escape(value)
                for value in (cp, city)
                if value
            )
            if suffix_pattern and re.search(
                rf"(?:\s+{suffix_pattern})$",
                address,
                flags=re.IGNORECASE,
            ):
                address = re.sub(
                    rf"(?:\s+{suffix_pattern})$",
                    "",
                    address,
                    flags=re.IGNORECASE,
                ).strip()

            historical_where = " ".join(
                value
                for value in (address, cp, city)
                if value
            )
            if historical_where:
                queries.append(
                    f"{primary_name} {historical_where} téléphone"
                )
                historical_query_added = True
                break

        if (
            not historical_query_added
            and len(queries) < WebFallbackFinder.MAX_QUERIES
        ):
            identity_query = current_query
            siren = re.sub(r"\D", "", str(identity.get("siren") or ""))
            if not identity_query and len(siren) == 9:
                identity_query = f"{primary_name} {siren}"
            if identity_query:
                queries.append(identity_query)

        # Si, exceptionnellement, il reste encore une place, un second alias
        # peut servir de dernier recours sans sacrifier l'axe historique.
        if (
            len(queries) < WebFallbackFinder.MAX_QUERIES
            and len(names) > 1
        ):
            alias_query = " ".join(
                value
                for value in (names[1], current_where)
                if value
            )
            if alias_query:
                queries.append(alias_query)

        unique_queries = list(
            dict.fromkeys(
                query.strip()
                for query in queries
                if query.strip()
            )
        )
        return unique_queries[: WebFallbackFinder.MAX_QUERIES]

    def _remember_search_metadata(
        self,
        url: str,
        *,
        title: str = "",
        snippet: str = "",
    ) -> None:
        url = str(url or "").strip()
        if not url:
            return

        metadata = {
            "url": url,
            "title": str(title or "").strip(),
            "snippet": str(snippet or "").strip(),
        }
        with self._search_metadata_lock:
            existing = dict(self._search_metadata.get(url) or {})
            if existing:
                # Une même URL peut apparaître dans plusieurs requêtes. On garde
                # séparément le titre et l'extrait les plus informatifs.
                if len(existing.get("title", "")) > len(metadata["title"]):
                    metadata["title"] = existing.get("title", "")
                if len(existing.get("snippet", "")) > len(metadata["snippet"]):
                    metadata["snippet"] = existing.get("snippet", "")
            self._search_metadata[url] = metadata

    def _search_urls(self, query: str) -> list[str]:
        try:
            response = requests.get(
                self.SEARCH_URL,
                params={"q": query},
                headers=self.headers,
                timeout=self.SEARCH_TIMEOUT,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            urls = []

            # DuckDuckGo HTML regroupe normalement titre + extrait dans un bloc
            # .result. On conserve ces métadonnées avant toute ouverture de page
            # afin de pouvoir exploiter un annuaire qui répond ensuite HTTP 403.
            for result in soup.select(".result"):
                anchor = result.select_one("a.result__a")
                if anchor is None:
                    anchor = result.select_one("a[href]")
                if anchor is None:
                    continue

                url = self._clean_result_url(anchor.get("href", ""))
                host = self._host(url)
                if not url or not host:
                    continue
                if self._domain_matches(host, self.SOCIAL_DOMAINS):
                    continue

                snippet_node = result.select_one(".result__snippet")
                title = anchor.get_text(" ", strip=True)
                snippet = (
                    snippet_node.get_text(" ", strip=True)
                    if snippet_node is not None
                    else ""
                )
                self._remember_search_metadata(
                    url,
                    title=title,
                    snippet=snippet,
                )

                if url not in urls:
                    urls.append(url)
                if len(urls) >= self.MAX_RESULT_URLS:
                    break

            # Compatibilité avec les variantes HTML ne contenant pas de bloc
            # .result : on garde l'ancien parcours des liens de résultats.
            if not urls:
                for anchor in soup.select("a.result__a, .result a[href]"):
                    url = self._clean_result_url(anchor.get("href", ""))
                    host = self._host(url)
                    if not url or not host:
                        continue
                    if self._domain_matches(host, self.SOCIAL_DOMAINS):
                        continue
                    self._remember_search_metadata(
                        url,
                        title=anchor.get_text(" ", strip=True),
                        snippet="",
                    )
                    if url not in urls:
                        urls.append(url)
                    if len(urls) >= self.MAX_RESULT_URLS:
                        break

            return urls
        except Exception as exc:
            self.last_errors.append(
                f"recherche web '{query}': {type(exc).__name__}: {exc}"
            )
            return []

    @staticmethod
    def _identity_name_in_text(text: str, identity: dict) -> str:
        """Retourne le nom/alias attendu lorsqu'il apparaît comme expression entière.

        Le contrôle se fait sur le texte normalisé afin de reconnaître aussi bien
        ``DECAM`` que ``D.E.C.A.M.`` sans confondre un simple fragment de mot.
        """
        normalized_text = normalize(text)
        if not normalized_text:
            return ""

        matches = []
        for name in identity_names(identity):
            normalized_name = normalize(name)
            if not normalized_name:
                continue
            pattern = rf"(?:^| ){re.escape(normalized_name)}(?: |$)"
            if re.search(pattern, normalized_text):
                matches.append((len(normalized_name), name))

        if not matches:
            return ""

        matches.sort(reverse=True)
        return matches[0][1]

    @staticmethod
    def _location_from_text(text: str, identity: dict) -> tuple[str, str]:
        """Repère une localisation actuelle ou historique dans un extrait."""
        raw_text = str(text or "")
        normalized_text = normalize(raw_text)
        cp = ""
        city = ""

        for location in identity_locations(identity):
            expected_cp = str(location.get("code_postal") or "").strip()
            expected_city = str(location.get("ville") or "").strip()

            if (
                not cp
                and expected_cp
                and re.search(rf"\b{re.escape(expected_cp)}\b", raw_text)
            ):
                cp = expected_cp

            normalized_city = normalize(expected_city)
            if (
                not city
                and normalized_city
                and re.search(
                    rf"(?:^| ){re.escape(normalized_city)}(?: |$)",
                    normalized_text,
                )
            ):
                city = expected_city

            if cp and city:
                break

        return cp, city

    def _identity_context_from_text(
        self,
        text: str,
        identity: dict,
    ) -> tuple[str, str]:
        """Isole le bloc du prospect dans une page contenant plusieurs sociétés.

        Les annuaires génériques peuvent afficher de nombreux artisans avec leurs
        propres coordonnées. On part d'une ligne portant le nom/alias attendu et
        on ne conserve que les lignes immédiatement rattachées à cette entrée.
        """
        raw_lines = str(text or "").splitlines()
        if not raw_lines:
            return "", ""

        contexts: list[tuple[int, str, str]] = []

        for index, raw_line in enumerate(raw_lines):
            line = re.sub(r"\s+", " ", raw_line).strip()
            matched_name = self._identity_name_in_text(line, identity)
            if not matched_name:
                continue

            block_lines = [line]
            for next_index in range(index + 1, min(len(raw_lines), index + 5)):
                raw_next = raw_lines[next_index]
                if not str(raw_next or "").strip():
                    break

                next_line = re.sub(r"\s+", " ", raw_next).strip()
                if not next_line:
                    break

                block_lines.append(next_line)
                joined = " ".join(block_lines)
                phones = extract_phones_from_text(
                    joined,
                    require_contact_hint=False,
                )
                emails = EmailFinder.extraire_emails(joined)
                cp, city = self._location_from_text(joined, identity)
                has_contact = bool(
                    phones["mobile"]
                    or phones["phone"]
                    or phones["fax"]
                    or emails
                )
                if has_contact and (cp or city):
                    break

            context = " ".join(block_lines).strip()
            cp, city = self._location_from_text(context, identity)
            probe = {
                "source": "web_fallback",
                "source_detail": "",
                "nom": matched_name,
                "adresse": "",
                "code_postal": cp,
                "ville": city,
                "telephones": [],
                "faxes": [],
                "site_web": "",
                "email": "",
                "texte": context,
            }
            score, reasons = score_candidate(identity, probe)
            phones = extract_phones_from_text(
                context,
                require_contact_hint=False,
            )
            emails = EmailFinder.extraire_emails(context)
            has_contact = bool(
                phones["mobile"]
                or phones["phone"]
                or phones["fax"]
                or emails
            )
            if has_contact:
                contexts.append(
                    (
                        score,
                        matched_name,
                        context,
                        tuple(reasons),
                    )
                )

        if not contexts:
            return "", ""

        contexts.sort(key=lambda item: item[0], reverse=True)
        best_score, best_name, best_context, _ = contexts[0]

        # Plusieurs lignes distinctes peuvent appartenir au même établissement
        # historique (ex. deux fiches DECAM à la même adresse avec deux numéros).
        # On fusionne uniquement les blocs qui atteignent eux-mêmes le seuil
        # renforcé nom + localisation, jamais les entrées voisines du catalogue.
        trusted_contexts = []
        seen_contexts = set()
        for score, matched_name, context, reasons in contexts:
            normalized_reasons = {
                str(reason or "").strip().lower()
                for reason in reasons
            }
            has_name = any(
                reason in normalized_reasons
                for reason in (
                    "nom très proche",
                    "enseigne/alias très proche",
                )
            )
            has_location = any(
                reason in normalized_reasons
                for reason in (
                    "code postal exact",
                    "code postal présent",
                    "ville exacte",
                    "ville présente",
                    "adresse proche",
                    "adresse partiellement proche",
                )
            )
            if score < 85 or not has_name or not has_location:
                continue

            key = normalize(context)
            if key in seen_contexts:
                continue
            seen_contexts.add(key)
            trusted_contexts.append(context)

        if trusted_contexts:
            return best_name, "\n".join(trusted_contexts)

        return best_name, best_context


    @staticmethod
    def _historical_locations_from_text(
        text: str,
        identity: dict,
    ) -> list[dict]:
        """Extrait des anciens établissements explicitement rattachés au même SIREN."""
        raw = re.sub(r"\s+", " ", str(text or "")).strip()
        if not raw:
            return []

        siren = re.sub(r"\D", "", str(identity.get("siren") or ""))
        current_siret = re.sub(r"\D", "", str(identity.get("siret") or ""))
        if len(siren) != 9:
            return []

        locations = []
        seen = set()

        pattern = re.compile(
            r"(?is)"
            r"SIRET\s*[:#-]?\s*([0-9][0-9 .-]{12,20}[0-9])"
            r".{0,700}?"
            r"Adresse\s*[:#-]?\s*"
            r"([^,;]{2,180}?)\s*[,;]\s*"
            r"(\d{5})\s+"
            r"([A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9'’\- ]{1,80})"
            r"(?=\s+(?:Dossier|Afficher|Activit|Ancien|SIRET|Adresse|Observations|$)|[.;]|$)"
        )

        for match in pattern.finditer(raw):
            siret = re.sub(r"\D", "", match.group(1))
            if len(siret) != 14 or not siret.startswith(siren):
                continue
            if current_siret and siret == current_siret:
                continue

            address = re.sub(r"\s+", " ", match.group(2)).strip(" ,-")
            cp = match.group(3).strip()
            city = re.sub(r"\s+", " ", match.group(4)).strip(" ,-")
            # Le HTML des fiches légales est souvent aplati sur une seule ligne.
            # Comme le motif global est insensible à la casse, le groupe ville
            # peut avaler le libellé suivant ("Dossier d'urbanisme", "Activité",
            # etc.). On coupe explicitement ces marqueurs de section.
            city = re.split(
                r"(?i)\s+(?:Dossier|Afficher|Activit(?:é|e)|Ancien|SIRET|"
                r"Adresse|Observations|Radiation|Transfert)\b",
                city,
                maxsplit=1,
            )[0].strip(" ,-")

            key = (normalize(address), cp, normalize(city), siret)
            if not address or not cp or not city or key in seen:
                continue
            seen.add(key)
            locations.append(
                {
                    "adresse": address,
                    "code_postal": cp,
                    "ville": city,
                    "siret": siret,
                }
            )

        return locations

    @staticmethod
    def _identity_with_historical_locations(
        identity: dict,
        historical_locations: list[dict],
    ) -> dict:
        """Ajoute des implantations historiques sans dupliquer l'adresse courante."""
        enriched = dict(identity or {})
        existing = []

        raw_locations = enriched.get("localisations_recherche") or []
        if isinstance(raw_locations, list):
            existing.extend(
                dict(item)
                for item in raw_locations
                if isinstance(item, dict)
            )

        current = {
            "adresse": str(enriched.get("adresse") or "").strip(),
            "code_postal": str(enriched.get("code_postal") or "").strip(),
            "ville": str(enriched.get("ville") or "").strip(),
        }

        def location_key(item: dict) -> tuple[str, str, str]:
            cp = str(item.get("code_postal") or "").strip()
            city = normalize(item.get("ville", ""))
            address = normalize(item.get("adresse", ""))

            # Certaines API incluent déjà "CP VILLE" dans le champ adresse.
            # On le retire de la clé de déduplication pour ne pas créer deux
            # implantations identiques.
            suffix = normalize(" ".join(value for value in (cp, city) if value))
            if suffix and address.endswith(" " + suffix):
                address = address[: -(len(suffix) + 1)].strip()

            return (address, cp, city)

        merged = []
        seen = set()

        for item in [current, *existing, *(historical_locations or [])]:
            if not isinstance(item, dict):
                continue
            address = str(item.get("adresse") or "").strip()
            cp = str(item.get("code_postal") or "").strip()
            city = str(item.get("ville") or "").strip()
            key = location_key(
                {"adresse": address, "code_postal": cp, "ville": city}
            )
            if not any(key) or key in seen:
                continue
            seen.add(key)

            clean = {
                "adresse": address,
                "code_postal": cp,
                "ville": city,
            }
            siret = re.sub(r"\D", "", str(item.get("siret") or ""))
            if len(siret) == 14:
                clean["siret"] = siret
            merged.append(clean)

        enriched["localisations_recherche"] = merged
        return enriched

    @staticmethod
    def _strong_metadata_identity(candidate: dict) -> bool:
        reasons = {
            str(reason or "").strip().lower()
            for reason in candidate.get("match_reasons") or []
            if str(reason or "").strip()
        }

        if "siret exact" in reasons or "siren exact" in reasons:
            return True

        very_close_name = any(
            reason in reasons
            for reason in (
                "nom très proche",
                "enseigne/alias très proche",
            )
        )
        location_evidence = any(
            reason in reasons
            for reason in (
                "code postal exact",
                "code postal présent",
                "ville exacte",
                "ville présente",
                "adresse proche",
                "adresse partiellement proche",
            )
        )
        return (
            int(candidate.get("match_score") or 0) >= 85
            and very_close_name
            and location_evidence
        )

    def _candidate_from_search_metadata(
        self,
        metadata: dict | None,
        identity: dict,
    ) -> dict:
        metadata = dict(metadata or {})
        url = str(metadata.get("url") or "").strip()
        title = str(metadata.get("title") or "").strip()
        snippet = str(metadata.get("snippet") or "").strip()
        text = " ".join(value for value in (title, snippet) if value).strip()
        if not text:
            return self._empty()

        cp, city = self._location_from_text(text, identity)
        matched_name = self._identity_name_in_text(text, identity)

        candidate = {
            "source": "web_fallback",
            "source_detail": self._host(url),
            # Le titre d'une page d'annuaire peut être générique. Si le nom du
            # prospect apparaît explicitement dans l'extrait, il constitue un
            # meilleur signal d'identité que ce titre SEO.
            "nom": matched_name or title,
            "adresse": "",
            "code_postal": cp,
            "ville": city,
            "telephones": [],
            "faxes": [],
            "site_web": "",
            "email": "",
            "texte": text[:12000],
            "technical_errors": [],
        }
        score, reasons = score_candidate(identity, candidate)
        candidate.update(
            match_score=score,
            match_reasons=reasons,
            confidence=confidence(score),
        )

        # Les extraits de moteur de recherche sont utiles, mais plus faciles à
        # contaminer qu'une page dédiée. On n'en extrait les coordonnées qu'avec
        # une preuve d'identité forte : SIRET/SIREN exact ou nom + localisation
        # particulièrement convaincants.
        if not self._strong_metadata_identity(candidate):
            if candidate["confidence"] == "validated":
                candidate["confidence"] = "review"
            return candidate

        phones = extract_phones_from_text(
            text,
            require_contact_hint=False,
        )
        email_candidates = EmailFinder.extraire_emails(text)
        candidate["telephones"] = list(
            dict.fromkeys(phones["mobile"] + phones["phone"])
        )
        candidate["faxes"] = list(dict.fromkeys(phones["fax"]))
        candidate["email"] = email_candidates[0] if email_candidates else ""
        return candidate

    def _external_site_from_links(self, soup: BeautifulSoup, current_url: str) -> str:
        """Ne retient qu'un lien explicitement présenté comme site de l'entreprise.

        Les annuaires contiennent beaucoup de publicités/liens partenaires ;
        prendre le premier domaine externe produirait de faux sites officiels.
        """
        current_host = self._host(current_url)
        website_hints = (
            "site web", "site internet", "website", "voir le site",
            "visiter le site", "accéder au site", "acceder au site",
        )
        for anchor in soup.select("a[href]"):
            label = " ".join(
                str(value or "")
                for value in (
                    anchor.get_text(" ", strip=True),
                    anchor.get("title"),
                    anchor.get("aria-label"),
                )
            ).lower()
            if not any(hint in label for hint in website_hints):
                continue
            href = self._clean_result_url(anchor.get("href", ""))
            if not href:
                continue
            host = self._host(href)
            if not host or host == current_host:
                continue
            if self._domain_matches(host, self.SOCIAL_DOMAINS):
                continue
            if self._domain_matches(host, self.DIRECTORY_DOMAINS):
                continue
            return href
        return ""

    def _fetch_candidate(
        self,
        url: str,
        identity: dict,
        search_metadata: dict | None = None,
    ) -> dict:
        metadata_candidate = (
            self._candidate_from_search_metadata(search_metadata, identity)
            if search_metadata
            else None
        )

        def fallback_with_errors(errors: list[str]) -> dict:
            if metadata_candidate is not None:
                fallback = dict(metadata_candidate)
                fallback["technical_errors"] = list(
                    dict.fromkeys(
                        list(fallback.get("technical_errors") or []) + errors
                    )
                )
                return fallback
            return self._empty(errors)

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.PAGE_TIMEOUT,
                allow_redirects=True,
            )
            response.raise_for_status()
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "html" not in content_type and "text" not in content_type:
                return fallback_with_errors([])

            final_url = response.url or url
            soup = BeautifulSoup(response.text, "lxml")
            title = (soup.title.get_text(" ", strip=True) if soup.title else "").strip()
            for tag in soup(["script", "style", "noscript", "svg", "template"]):
                tag.decompose()

            # Les retours à la ligne servent de frontières naturelles entre les
            # fiches d'un annuaire multi-entreprises.
            structured_text = soup.get_text("\n", strip=True)
            if not structured_text:
                return fallback_with_errors([])

            official_candidate = self._is_official_site_for_identity(
                final_url,
                identity,
            )
            matched_name = ""
            contact_text = structured_text

            if not official_candidate:
                matched_name, isolated_context = self._identity_context_from_text(
                    structured_text,
                    identity,
                )
                if isolated_context:
                    contact_text = isolated_context

            phones = extract_phones_from_text(
                contact_text,
                require_contact_hint=True,
            )
            email_candidates = EmailFinder.extraire_emails(contact_text)

            current_host = self._host(final_url)
            if official_candidate:
                parsed = urlparse(final_url)
                site_web = f"{parsed.scheme}://{parsed.netloc}/"
            else:
                site_web = self._external_site_from_links(soup, final_url)

            cp, city = self._location_from_text(contact_text, identity)

            candidate = {
                "source": "web_fallback",
                "source_detail": current_host,
                "nom": matched_name or title,
                "adresse": "",
                "code_postal": cp,
                "ville": city,
                "telephones": list(dict.fromkeys(phones["mobile"] + phones["phone"])),
                "faxes": list(dict.fromkeys(phones["fax"])),
                "site_web": site_web,
                "email": email_candidates[0] if email_candidates else "",
                "texte": contact_text[:24000],
                "technical_errors": [],
            }
            score, reasons = score_candidate(identity, candidate)
            candidate.update(
                match_score=score,
                match_reasons=reasons,
                confidence=confidence(score),
            )

            if metadata_candidate is None:
                return candidate

            # Si l'extrait et la page décrivent la même société avec une preuve
            # forte, on peut conserver les coordonnées visibles dans l'extrait
            # même si la page chargée est plus pauvre.
            return self._merge_valid([metadata_candidate, candidate])
        except Exception as exc:
            return fallback_with_errors(
                [f"page {url}: {type(exc).__name__}: {exc}"]
            )

    @staticmethod
    def _merge_valid(candidates: list[dict]) -> dict:
        valid = [
            item
            for item in candidates
            if item.get("confidence") == "validated"
        ]
        if not valid:
            best = max(
                candidates,
                key=lambda item: int(item.get("match_score") or 0),
                default=None,
            )
            return best or WebFallbackFinder._empty()

        valid.sort(
            key=lambda item: int(item.get("match_score") or 0),
            reverse=True,
        )

        best_source = valid[0]
        best = dict(best_source)

        def has_strong_merge_evidence(item: dict) -> bool:
            reasons = {
                str(reason or "").strip().lower()
                for reason in item.get("match_reasons") or []
                if str(reason or "").strip()
            }

            # Un identifiant légal exact suffit pour autoriser la fusion,
            # y compris pour un ancien établissement du même SIREN.
            if "siret exact" in reasons or "siren exact" in reasons:
                return True

            score = int(item.get("match_score") or 0)

            very_close_name = any(
                reason in reasons
                for reason in (
                    "nom très proche",
                    "enseigne/alias très proche",
                )
            )

            location_evidence = any(
                reason in reasons
                for reason in (
                    "code postal exact",
                    "code postal présent",
                    "ville exacte",
                    "ville présente",
                    "adresse proche",
                    "adresse partiellement proche",
                )
            )

            # Plus strict que le simple statut "validated" (>= 65) :
            # un candidat secondaire doit être vraiment convaincant avant
            # d'ajouter ses coordonnées au meilleur résultat.
            return (
                score >= 85
                and very_close_name
                and location_evidence
            )

        trusted = [best_source]
        trusted.extend(
            item
            for item in valid[1:]
            if has_strong_merge_evidence(item)
        )

        faxes = []
        phones = []
        emails = []
        sites = []
        details = []
        texts = []

        for item in trusted:
            faxes.extend(item.get("faxes") or [])
            phones.extend(item.get("telephones") or [])

            if item.get("email"):
                emails.append(item["email"])

            if item.get("site_web"):
                sites.append(item["site_web"])

            if item.get("source_detail"):
                details.append(item["source_detail"])

            if item.get("texte"):
                texts.append(item["texte"])

        fax_keys = {
            re.sub(r"\D", "", fax)
            for fax in faxes
            if re.sub(r"\D", "", fax)
        }

        merged_phones = []
        seen_phones = set()

        for phone in phones:
            key = re.sub(r"\D", "", phone)
            if (
                key
                and key not in fax_keys
                and key not in seen_phones
            ):
                seen_phones.add(key)
                merged_phones.append(phone)

        best["telephones"] = merged_phones
        best["faxes"] = list(dict.fromkeys(faxes))
        best["email"] = next(
            (email for email in emails if email),
            "",
        )
        best["site_web"] = next(
            (site for site in sites if site),
            "",
        )
        best["source_detail"] = " + ".join(
            dict.fromkeys(details)
        )
        best["texte"] = "\n".join(texts)[:30000]

        return best

    def rechercher(self, identity: dict) -> dict:
        self.last_errors = []
        with self._search_metadata_lock:
            self._search_metadata = {}

        queries = list(
            dict.fromkeys(
                query
                for query in self._query_plan(identity)
                if str(query or "").strip()
            )
        )

        # Exécuter tous les axes prioritaires (localisation actuelle, SIRET,
        # historique) avant d'appliquer la limite globale de pages à ouvrir.
        # Les requêtes au moteur de recherche restent volontairement
        # séquentielles : DuckDuckGo HTML peut renvoyer des pages vides lorsque
        # plusieurs requêtes partent simultanément depuis la même IP. Les pages
        # de résultats sélectionnées sont, elles, toujours ouvertes en parallèle
        # plus bas afin de préserver les performances.
        search_results = {query: [] for query in queries}

        for query in queries:
            try:
                search_results[query] = list(self._search_urls(query) or [])
            except Exception as exc:
                self.last_errors.append(
                    f"recherche web '{query}': "
                    f"{type(exc).__name__}: {exc}"
                )
                search_results[query] = []

        # Les extraits de recherche sont analysés immédiatement. Ils ne coûtent
        # aucune requête HTTP supplémentaire et restent disponibles même pour
        # les URLs qui ne feront pas partie des MAX_FETCHES pages ouvertes.
        with self._search_metadata_lock:
            search_metadata = {
                url: dict(metadata)
                for url, metadata in self._search_metadata.items()
            }

        # Répartition équitable des URLs : on prend d'abord le premier résultat
        # de chaque requête, puis le deuxième, etc. Ainsi une recherche large
        # ne peut plus consommer seule MAX_FETCHES avant que le SIRET ou
        # l'ancienne implantation aient été exploités.
        urls = []
        max_depth = max(
            (len(results) for results in search_results.values()),
            default=0,
        )

        for index in range(max_depth):
            for query in queries:
                results = search_results.get(query) or []
                if index >= len(results):
                    continue

                url = results[index]
                if url and url not in urls:
                    urls.append(url)

                if len(urls) >= self.MAX_FETCHES:
                    break

            if len(urls) >= self.MAX_FETCHES:
                break

        # Pour les résultats non ouverts à cause de MAX_FETCHES, l'extrait
        # DuckDuckGo reste exploitable s'il porte une preuve d'identité forte.
        # Les URLs effectivement ouvertes ne sont pas ajoutées ici : leur
        # métadonnée est transmise à _fetch_candidate, ce qui évite les doublons.
        candidates = [
            self._candidate_from_search_metadata(metadata, identity)
            for url, metadata in search_metadata.items()
            if url not in urls
        ]

        if not urls and not candidates:
            return self._empty(self.last_errors)

        if urls:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(4, len(urls))
            ) as executor:
                future_items = []
                for url in urls:
                    metadata = search_metadata.get(url)
                    if metadata:
                        future = executor.submit(
                            self._fetch_candidate,
                            url,
                            identity,
                            search_metadata=metadata,
                        )
                    else:
                        # Compatibilité avec les tests/callers existants qui
                        # remplacent _fetch_candidate par une fonction à 2 args.
                        future = executor.submit(
                            self._fetch_candidate,
                            url,
                            identity,
                        )
                    future_items.append(future)

                for future in concurrent.futures.as_completed(future_items):
                    try:
                        candidate = future.result()
                    except Exception as exc:
                        self.last_errors.append(
                            f"lecture web: {type(exc).__name__}: {exc}"
                        )
                        continue

                    if candidate:
                        candidates.append(candidate)

        # Les pages légales déjà validées peuvent contenir des établissements
        # historiques absents de l'API SIREN. On les extrait avant la fusion
        # finale, puis on effectue une seule seconde passe ciblée sur les
        # nouvelles implantations.
        historical_locations = []
        for candidate in list(candidates):
            if candidate.get("confidence") != "validated":
                continue

            reasons = {
                str(reason or "").strip().lower()
                for reason in candidate.get("match_reasons") or []
            }
            if not (
                "siret exact" in reasons
                or "siren exact" in reasons
            ):
                continue

            source_detail = str(candidate.get("source_detail") or "").strip().lower()
            if source_detail.startswith("www."):
                source_detail = source_detail[4:]
            if source_detail not in {
                "societe.com",
                "pappers.fr",
                "annuaire-entreprises.data.gouv.fr",
                "entreprises.lefigaro.fr",
                "verif.com",
                "manageo.fr",
                "infogreffe.fr",
            }:
                continue

            historical_locations.extend(
                self._historical_locations_from_text(
                    candidate.get("texte") or "",
                    identity,
                )
            )

        enriched_identity = self._identity_with_historical_locations(
            identity,
            historical_locations,
        )

        initial_location_keys = {
            (
                normalize(location.get("adresse", "")),
                str(location.get("code_postal") or "").strip(),
                normalize(location.get("ville", "")),
            )
            for location in identity_locations(identity)
        }
        enriched_location_keys = {
            (
                normalize(location.get("adresse", "")),
                str(location.get("code_postal") or "").strip(),
                normalize(location.get("ville", "")),
            )
            for location in identity_locations(enriched_identity)
        }

        has_new_history = bool(enriched_location_keys - initial_location_keys)

        if has_new_history:
            second_queries = [
                query
                for query in self._query_plan(enriched_identity)
                if str(query or "").strip() and query not in queries
            ]

            second_search_results = {query: [] for query in second_queries}
            for query in second_queries:
                try:
                    second_search_results[query] = list(
                        self._search_urls(query) or []
                    )
                except Exception as exc:
                    self.last_errors.append(
                        f"recherche web '{query}': "
                        f"{type(exc).__name__}: {exc}"
                    )
                    second_search_results[query] = []

            with self._search_metadata_lock:
                second_metadata = {
                    url: dict(metadata)
                    for url, metadata in self._search_metadata.items()
                }

            already_seen_urls = set(search_metadata)
            second_urls = []
            max_depth = max(
                (
                    len(results)
                    for results in second_search_results.values()
                ),
                default=0,
            )
            for index in range(max_depth):
                for query in second_queries:
                    results = second_search_results.get(query) or []
                    if index >= len(results):
                        continue
                    url = results[index]
                    if (
                        url
                        and url not in already_seen_urls
                        and url not in second_urls
                    ):
                        second_urls.append(url)
                    if len(second_urls) >= self.MAX_FETCHES:
                        break
                if len(second_urls) >= self.MAX_FETCHES:
                    break

            for url, metadata in second_metadata.items():
                if url in already_seen_urls or url in second_urls:
                    continue
                candidate = self._candidate_from_search_metadata(
                    metadata,
                    enriched_identity,
                )
                if candidate:
                    candidates.append(candidate)

            if second_urls:
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(4, len(second_urls))
                ) as executor:
                    future_items = []
                    for url in second_urls:
                        metadata = second_metadata.get(url)
                        if metadata:
                            future = executor.submit(
                                self._fetch_candidate,
                                url,
                                enriched_identity,
                                search_metadata=metadata,
                            )
                        else:
                            future = executor.submit(
                                self._fetch_candidate,
                                url,
                                enriched_identity,
                            )
                        future_items.append(future)

                    for future in concurrent.futures.as_completed(future_items):
                        try:
                            candidate = future.result()
                        except Exception as exc:
                            self.last_errors.append(
                                f"lecture web historique: "
                                f"{type(exc).__name__}: {exc}"
                            )
                            continue
                        if candidate:
                            candidates.append(candidate)

        result = self._merge_valid(candidates)

        candidate_errors = []
        for candidate in candidates:
            candidate_errors.extend(candidate.get("technical_errors") or [])

        result["technical_errors"] = list(
            dict.fromkeys(
                list(result.get("technical_errors") or [])
                + candidate_errors
                + self.last_errors
            )
        )
        return result
