from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class EmailFinder:
    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    TECHNICAL_DOMAINS = (
        "sentry.io",
        "sentry-next.wixpress.com",
        "wixpress.com",
        "wix.com",
        "example.com",
        "example.org",
        "localhost",
        "cloudflare.com",
    )
    TECHNICAL_LOCALS = {
        "noreply", "no-reply", "donotreply", "do-not-reply",
        "mailer-daemon", "postmaster",
    }

    def __init__(self):
        self.last_source = ""
        self.last_score = 0

    @staticmethod
    def _site_domain(site_web: str) -> str:
        try:
            host = (urlparse(site_web).hostname or "").lower().strip(".")
        except Exception:
            return ""
        if host.startswith("www."):
            host = host[4:]
        return host

    @classmethod
    def _clean_email(cls, value: str) -> str:
        return str(value or "").strip().strip("<>[](){}.,;:'\"").lower()

    @classmethod
    def _is_technical(cls, email: str) -> bool:
        email = cls._clean_email(email)
        if "@" not in email:
            return True
        local, domain = email.rsplit("@", 1)
        domain = domain.strip(".")

        if local in cls.TECHNICAL_LOCALS:
            return True
        if any(token in domain for token in cls.TECHNICAL_DOMAINS):
            return True
        if any(token in local for token in ("sentry", "wixpress")):
            return True
        # Les identifiants techniques injectés par des SDK ressemblent souvent
        # à un hash hexadécimal long, comme celui observé sur Wix/Sentry.
        if len(local) >= 24 and re.fullmatch(r"[0-9a-f]+", local):
            return True
        return False

    @classmethod
    def extraire_emails(cls, texte):
        propres = []
        for raw in cls.EMAIL_RE.findall(str(texte or "")):
            email = cls._clean_email(raw)
            if cls._is_technical(email):
                continue
            if email not in propres:
                propres.append(email)
        return propres

    @classmethod
    def _score_email(
        cls,
        email: str,
        *,
        site_domain: str,
        source_kind: str,
    ) -> int:
        if cls._is_technical(email):
            return -1
        local, domain = email.rsplit("@", 1)
        score = 70 if source_kind == "mailto" else 50

        # Un email sur le domaine officiel est très fiable, mais on conserve
        # aussi les adresses Orange/Free/Gmail visibles sur les sites artisans.
        if site_domain and (
            domain == site_domain or domain.endswith("." + site_domain)
        ):
            score += 35

        if local in {
            "contact", "info", "accueil", "commercial", "bonjour",
            "direction", "secretariat", "bureau",
        }:
            score += 5
        return score

    def _candidates_from_html(self, html: str, site_domain: str):
        soup = BeautifulSoup(html or "", "lxml")
        candidates = []

        # Les liens mailto sont la preuve la plus forte : l'éditeur du site a
        # explicitement déclaré l'adresse comme moyen de contact.
        for link in soup.select('a[href^="mailto:"]'):
            href = link.get("href", "")
            raw = href.split(":", 1)[-1].split("?", 1)[0]
            for email in self.extraire_emails(raw):
                candidates.append(
                    (
                        self._score_email(
                            email,
                            site_domain=site_domain,
                            source_kind="mailto",
                        ),
                        email,
                        "mailto",
                    )
                )

        # Ne jamais scanner le HTML brut : scripts et SDK injectent des emails
        # techniques. On ne regarde que le texte réellement visible.
        for tag in soup(["script", "style", "noscript", "svg", "template"]):
            tag.decompose()
        visible_text = soup.get_text(" ", strip=True)
        for email in self.extraire_emails(visible_text):
            candidates.append(
                (
                    self._score_email(
                        email,
                        site_domain=site_domain,
                        source_kind="visible_text",
                    ),
                    email,
                    "visible_text",
                )
            )

        return [item for item in candidates if item[0] >= 0]

    def chercher(self, site_web):
        self.last_source = ""
        self.last_score = 0

        if not site_web or str(site_web).strip() in ["", "nan", "None"]:
            return ""

        site_web = str(site_web).strip()
        if not site_web.startswith(("http://", "https://")):
            site_web = "https://" + site_web

        pages = list(dict.fromkeys([
            site_web,
            urljoin(site_web, "/contact"),
            urljoin(site_web, "/contactez-nous"),
            urljoin(site_web, "/nous-contacter"),
            urljoin(site_web, "/mentions-legales"),
        ]))
        site_domain = self._site_domain(site_web)
        headers = {"User-Agent": "Mozilla/5.0"}
        best = None

        for url in pages:
            try:
                response = requests.get(url, headers=headers, timeout=8)
                if response.status_code >= 400:
                    continue
                for score, email, source_kind in self._candidates_from_html(
                    response.text,
                    site_domain,
                ):
                    candidate = (score, email, source_kind, url)
                    if best is None or candidate[0] > best[0]:
                        best = candidate

                # mailto + domaine officiel : inutile de visiter quatre pages
                # supplémentaires, on a déjà une donnée de très forte qualité.
                if best and best[0] >= 105:
                    break
            except Exception:
                continue

        if not best:
            return ""

        self.last_score, email, source_kind, source_url = best
        self.last_source = f"{source_kind}:{source_url}"
        return email
