from __future__ import annotations

import concurrent.futures
import re
from urllib.parse import parse_qs, quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from modules.company_matcher import confidence, identity_locations, identity_names, score_candidate
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
        "pagesjaunes.fr",
        "google.com",
        "google.fr",
        "bing.com",
        "duckduckgo.com",
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

        primary_locations = locations[:2]
        queries = []

        # Priorité aux alias/enseignes puis à la raison sociale, avec ville ou CP.
        for name in names[:2]:
            location = primary_locations[0] if primary_locations else {}
            where = " ".join(
                value
                for value in (
                    str(location.get("code_postal") or "").strip(),
                    str(location.get("ville") or "").strip(),
                )
                if value
            )
            queries.append(" ".join(x for x in (name, where) if x))
            if len(queries) >= WebFallbackFinder.MAX_QUERIES:
                break

        # Une recherche exacte par SIRET est très efficace sur les annuaires web
        # génériques. Contrairement à PagesJaunes, le SIRET est pertinent ici.
        siret = re.sub(r"\D", "", str(identity.get("siret") or ""))
        if len(siret) == 14:
            queries.append(siret)

        # Si le siège/une autre implantation est connue, une variante du nom
        # principal avec cette ville peut retrouver une fiche qui n'existe pas
        # à l'adresse du SIRET courant.
        if len(primary_locations) > 1:
            alt = primary_locations[1]
            where = " ".join(
                value
                for value in (
                    str(alt.get("code_postal") or "").strip(),
                    str(alt.get("ville") or "").strip(),
                )
                if value
            )
            if where:
                queries.append(f"{names[0]} {where}")

        return list(dict.fromkeys(q.strip() for q in queries if q.strip()))[: WebFallbackFinder.MAX_QUERIES]

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
            for anchor in soup.select("a.result__a, .result a[href]"):
                url = self._clean_result_url(anchor.get("href", ""))
                host = self._host(url)
                if not url or not host:
                    continue
                if self._domain_matches(host, self.SOCIAL_DOMAINS):
                    continue
                if url not in urls:
                    urls.append(url)
                if len(urls) >= self.MAX_RESULT_URLS:
                    break
            return urls
        except Exception as exc:
            self.last_errors.append(f"recherche web '{query}': {type(exc).__name__}: {exc}")
            return []

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

    def _fetch_candidate(self, url: str, identity: dict) -> dict:
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
                return self._empty()

            final_url = response.url or url
            soup = BeautifulSoup(response.text, "lxml")
            title = (soup.title.get_text(" ", strip=True) if soup.title else "").strip()
            for tag in soup(["script", "style", "noscript", "svg", "template"]):
                tag.decompose()
            text = soup.get_text(" ", strip=True)
            if not text:
                return self._empty()

            phones = extract_phones_from_text(text, require_contact_hint=True)
            email_candidates = EmailFinder.extraire_emails(text)

            current_host = self._host(final_url)
            if self._is_official_candidate_domain(final_url):
                parsed = urlparse(final_url)
                site_web = f"{parsed.scheme}://{parsed.netloc}/"
            else:
                site_web = self._external_site_from_links(soup, final_url)

            cp = ""
            for location in identity_locations(identity):
                expected = str(location.get("code_postal") or "").strip()
                if expected and re.search(rf"\b{re.escape(expected)}\b", text):
                    cp = expected
                    break

            candidate = {
                "source": "web_fallback",
                "source_detail": current_host,
                "nom": title,
                "adresse": "",
                "code_postal": cp,
                "ville": "",
                "telephones": list(dict.fromkeys(phones["mobile"] + phones["phone"])),
                "faxes": list(dict.fromkeys(phones["fax"])),
                "site_web": site_web,
                "email": email_candidates[0] if email_candidates else "",
                "texte": text[:24000],
                "technical_errors": [],
            }
            score, reasons = score_candidate(identity, candidate)
            candidate.update(
                match_score=score,
                match_reasons=reasons,
                confidence=confidence(score),
            )
            return candidate
        except Exception as exc:
            return self._empty([f"page {url}: {type(exc).__name__}: {exc}"])

    @staticmethod
    def _merge_valid(candidates: list[dict]) -> dict:
        valid = [x for x in candidates if x.get("confidence") == "validated"]
        if not valid:
            best = max(candidates, key=lambda x: int(x.get("match_score") or 0), default=None)
            return best or WebFallbackFinder._empty()

        valid.sort(key=lambda x: int(x.get("match_score") or 0), reverse=True)
        best = dict(valid[0])
        faxes = []
        phones = []
        emails = []
        sites = []
        details = []
        texts = []
        for item in valid:
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

        fax_keys = {re.sub(r"\D", "", x) for x in faxes}
        merged_phones = []
        seen = set()
        for phone in phones:
            key = re.sub(r"\D", "", phone)
            if key and key not in fax_keys and key not in seen:
                seen.add(key)
                merged_phones.append(phone)

        best["telephones"] = merged_phones
        best["faxes"] = list(dict.fromkeys(faxes))
        best["email"] = next((x for x in emails if x), "")
        best["site_web"] = next((x for x in sites if x), "")
        best["source_detail"] = " + ".join(dict.fromkeys(details))
        best["texte"] = "\n".join(texts)[:30000]
        return best

    def rechercher(self, identity: dict) -> dict:
        self.last_errors = []
        urls = []
        for query in self._query_plan(identity):
            for url in self._search_urls(query):
                if url not in urls:
                    urls.append(url)
                if len(urls) >= self.MAX_FETCHES:
                    break
            if len(urls) >= self.MAX_FETCHES:
                break

        if not urls:
            return self._empty(self.last_errors)

        candidates = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(urls))) as executor:
            futures = [executor.submit(self._fetch_candidate, url, identity) for url in urls]
            for future in concurrent.futures.as_completed(futures):
                try:
                    candidate = future.result()
                except Exception as exc:
                    self.last_errors.append(f"lecture web: {type(exc).__name__}: {exc}")
                    continue
                if candidate:
                    candidates.append(candidate)

        result = self._merge_valid(candidates)
        result["technical_errors"] = list(dict.fromkeys(
            list(result.get("technical_errors") or []) + self.last_errors
        ))
        return result
