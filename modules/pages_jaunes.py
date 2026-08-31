from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin, urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from modules.browser_manager import BrowserManager
from modules.company_matcher import confidence, identity_locations, identity_names, score_candidate
from modules.contact_quality import extract_phones_from_text, normalize_fr_phone


class PagesJaunesFinder:
    SEARCH_URL = "https://www.pagesjaunes.fr/annuaire/chercherlespros"
    RESULT_WAIT_MS = 3500
    PROFILE_LIMIT = 3

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self._cookies_checked = False
        self.last_errors: list[str] = []

    async def ouvrir(self):
        if self.browser is not None:
            return
        try:
            self.playwright = await async_playwright().start()
            self.browser = await BrowserManager.launch_async(
                self.playwright,
                headless=False,
            )
            self.page = await self.browser.new_page()
        except Exception:
            await self.fermer()
            raise

    async def fermer(self):
        if self.browser:
            try:
                await self.browser.close()
            finally:
                self.browser = None
                self.page = None

        if self.playwright:
            try:
                await self.playwright.stop()
            finally:
                self.playwright = None
        self._cookies_checked = False

    @staticmethod
    def extraire_telephones(texte):
        extracted = extract_phones_from_text(str(texte or ""))
        return extracted["phone"] + extracted["mobile"]

    @staticmethod
    def _phone_sort_key(numero):
        compact = re.sub(r"\D", "", numero)
        return (
            0 if compact.startswith(("06", "07")) else 1,
            compact,
        )

    async def _accept_cookies_once(self):
        """Accepte automatiquement la bannière PagesJaunes une fois.

        La bannière n'est normalement présentée qu'au début de la session. On
        attend brièvement son bouton, puis on ne refait plus ce contrôle.
        """
        if self._cookies_checked:
            return True

        button_pattern = re.compile(
            r"^(tout accepter|accepter tout|accepter|j['’]accepte)$",
            re.I,
        )
        try:
            target = self.page.get_by_role("button", name=button_pattern).first
            await target.wait_for(state="visible", timeout=1800)
            await target.click(timeout=1800)
        except Exception:
            # Pas de bannière visible = consentement déjà enregistré ou CMP
            # absente. PagesJaunes reste utilisable, on ne ralentit pas la suite.
            pass

        self._cookies_checked = True
        return True

    @staticmethod
    def _external_site(links):
        """Retourne uniquement un lien explicitement presente comme site officiel."""

        excluded_domains = {
            "pagesjaunes.fr",
            "solocal.com",
            "pappers.fr",
            "societe.com",
            "verif.com",
            "manageo.fr",
            "infogreffe.fr",
            "allbiz.fr",
            "cylex-locale.fr",
            "118000.fr",
            "118712.fr",
            "le-site-de.com",
            "hoodspot.fr",
            "kompass.com",
            "entreprises.lefigaro.fr",
            "annuaire-entreprises.data.gouv.fr",
            "annuaire-entreprises-rge.fr",
            "facebook.com",
            "instagram.com",
            "linkedin.com",
            "youtube.com",
            "twitter.com",
            "x.com",
            "tiktok.com",
        }

        website_hints = (
            "site internet",
            "site web",
            "website",
            "voir le site",
            "visiter le site",
            "acceder au site",
            "consulter le site",
            "site officiel",
        )

        for item in links or []:
            if isinstance(item, dict):
                href = str(item.get("href") or "").strip()
                label = " ".join(
                    str(item.get(key) or "").strip()
                    for key in ("text", "title", "aria_label")
                ).lower()
            else:
                href = str(item or "").strip()
                label = ""

            if not href.startswith(("http://", "https://")):
                continue

            try:
                host = (urlparse(href).hostname or "").lower().strip(".")
            except Exception:
                continue

            if host.startswith("www."):
                host = host[4:]

            if not host:
                continue

            if any(
                host == domain or host.endswith("." + domain)
                for domain in excluded_domains
            ):
                continue

            if not any(hint in label for hint in website_hints):
                continue

            return href

        return ""

    @staticmethod
    def _empty_result(errors=None):
        return {
            "source": "pages_jaunes",
            "nom": "",
            "adresse": "",
            "code_postal": "",
            "ville": "",
            "telephones": [],
            "faxes": [],
            "site_web": "",
            "texte": "",
            "match_score": 0,
            "match_reasons": [],
            "confidence": "rejected",
            "technical_errors": list(errors or []),
        }

    async def _extract_profile(self):
        body = await self.page.inner_text("body")
        name = ""
        address = ""

        for selector in (
            "h1",
            '[class*="denomination"]',
            '[class*="company-name"]',
        ):
            try:
                el = self.page.locator(selector).first
                if await el.count():
                    name = (await el.inner_text()).strip()
                    if name:
                        break
            except Exception:
                continue

        candidates = []
        for selector in (
            '[class*="adresse"]',
            '[class*="address"]',
            "address",
        ):
            try:
                loc = self.page.locator(selector)
                for i in range(min(await loc.count(), 6)):
                    text = (await loc.nth(i).inner_text()).strip()
                    if text:
                        candidates.append(text)
            except Exception:
                continue

        if candidates:
            address = max(candidates, key=len)

        # Lot 1.1 : on privilégie les éléments explicitement téléphoniques.
        # Scanner tout le body récupérait aussi des fax et des numéros
        # techniques présents ailleurs dans la fiche.
        semantic_chunks = []
        try:
            loc = self.page.locator('a[href^="tel:"]')
            for i in range(min(await loc.count(), 8)):
                el = loc.nth(i)
                href = await el.get_attribute("href")
                label = await el.get_attribute("aria-label")
                text = await el.inner_text()
                semantic_chunks.append(" ".join(x for x in (label, text, href) if x))
        except Exception:
            pass

        for selector in (
            'button[aria-label*="Téléphone"]',
            'a[aria-label*="Téléphone"]',
            'button[aria-label*="telephone" i]',
            'a[aria-label*="telephone" i]',
            'button[aria-label*="Fax"]',
            'a[aria-label*="Fax"]',
        ):
            try:
                loc = self.page.locator(selector)
                for i in range(min(await loc.count(), 8)):
                    el = loc.nth(i)
                    label = await el.get_attribute("aria-label")
                    text = await el.inner_text()
                    semantic_chunks.append(" ".join(x for x in (label, text) if x))
            except Exception:
                continue

        classified = {"phone": [], "mobile": [], "fax": []}
        seen = {"phone": set(), "mobile": set(), "fax": set()}
        for chunk in semantic_chunks:
            found = extract_phones_from_text(chunk)
            for kind in classified:
                for number in found[kind]:
                    key = number.replace(" ", "")
                    if key not in seen[kind]:
                        seen[kind].add(key)
                        classified[kind].append(number)

        if not classified["phone"] and not classified["mobile"]:
            fallback = extract_phones_from_text(
                body,
                require_contact_hint=True,
            )
            classified = fallback

        phones = sorted(
            dict.fromkeys(classified["phone"] + classified["mobile"]),
            key=self._phone_sort_key,
        )

        try:
            links = await self.page.locator("a[href]").evaluate_all(
                """
                (els) => els.map(e => ({
                    href: e.href || "",
                    text: (e.innerText || "").trim(),
                    title: (e.getAttribute("title") || "").trim(),
                    aria_label: (e.getAttribute("aria-label") || "").trim()
                })).filter(x => x.href)
                """
            )
        except Exception:
            links = []

        cp_match = re.search(r"\b(\d{5})\b", address or body)

        return {
            "source": "pages_jaunes",
            "nom": name,
            "adresse": address,
            "code_postal": cp_match.group(1) if cp_match else "",
            "ville": "",
            "telephones": phones,
            "faxes": classified["fax"],
            "site_web": self._external_site(links),
            "texte": body[:16000],
        }

    async def _wait_for_search_results(self):
        locator = self.page.locator('a[href*="/pros/"]')
        try:
            await locator.first.wait_for(
                state="attached",
                timeout=self.RESULT_WAIT_MS,
            )
        except PlaywrightTimeoutError:
            # Une recherche sans résultat n'est pas une erreur technique.
            pass

    async def _search_once(self, identity, quoiqui: str, location: str = ""):
        params = {"quoiqui": quoiqui}
        if location:
            params["ou"] = location
        url = self.SEARCH_URL + "?" + urlencode(params)

        try:
            await self.page.goto(
                url,
                timeout=30000,
                wait_until="domcontentloaded",
            )
            await self._accept_cookies_once()
            await self._wait_for_search_results()
        except Exception as exc:
            self.last_errors.append(
                f"recherche '{quoiqui}': {type(exc).__name__}: {exc}"
            )
            return self._empty_result(self.last_errors)

        hrefs = []
        if "/pros/" in (self.page.url or ""):
            hrefs.append(self.page.url)

        try:
            links = self.page.locator('a[href*="/pros/"]')
            for i in range(min(await links.count(), self.PROFILE_LIMIT)):
                href = await links.nth(i).get_attribute("href")
                if href:
                    href = urljoin("https://www.pagesjaunes.fr", href)
                    if href not in hrefs:
                        hrefs.append(href)
        except Exception as exc:
            self.last_errors.append(
                f"lecture résultats '{quoiqui}': {type(exc).__name__}: {exc}"
            )

        best = None
        best_score = -999
        for href in hrefs[: self.PROFILE_LIMIT]:
            try:
                if href != self.page.url:
                    await self.page.goto(
                        href,
                        timeout=30000,
                        wait_until="domcontentloaded",
                    )
                candidate = await self._extract_profile()
                score, reasons = score_candidate(identity, candidate)
                candidate.update(
                    match_score=score,
                    match_reasons=reasons,
                    confidence=confidence(score),
                    technical_errors=list(self.last_errors),
                )
                if score > best_score:
                    best = candidate
                    best_score = score
                if candidate["confidence"] == "validated":
                    return candidate
            except Exception as exc:
                self.last_errors.append(
                    f"fiche PagesJaunes: {type(exc).__name__}: {exc}"
                )

        if best:
            best["technical_errors"] = list(self.last_errors)
            return best
        return self._empty_result(self.last_errors)

    @staticmethod
    def _name_search_plan(identity):
        """Construit les recherches PagesJaunes à partir des noms publics.

        Lot 2.2 : lorsqu'un SIREN possède plusieurs établissements dans le
        projet, les noms et localisations mutualisés peuvent être essayés. Le
        SIRET/SIREN ne sont toujours jamais envoyés à PagesJaunes.
        """
        entreprise = str(identity.get("entreprise") or "").strip()
        names = identity_names(identity)
        if not names:
            return []

        primary = entreprise
        aliases = [name for name in names if name != primary][:4]
        ordered_names = aliases + ([primary] if primary else [])

        locations = identity_locations(identity)
        if not locations:
            locations = [{"adresse": "", "code_postal": "", "ville": ""}]

        # La localisation du SIRET courant reste prioritaire. On ajoute au plus
        # deux autres implantations du même SIREN pour ne pas faire exploser le
        # temps de traitement.
        locations = locations[:3]
        compact_locations = []
        full_locations = []
        for item in locations:
            cp = str(item.get("code_postal") or "").strip()
            city = str(item.get("ville") or "").strip()
            address = str(item.get("adresse") or "").strip()
            compact = " ".join(value for value in (cp, city) if value)
            full = " ".join(value for value in (address, cp, city) if value)
            if compact not in compact_locations:
                compact_locations.append(compact)
            if full and full not in full_locations:
                full_locations.append(full)

        plan = []
        # Les alias sont les plus utiles lorsqu'une fiche publique porte le nom
        # commercial du siège plutôt que la raison sociale de l'établissement.
        for name in ordered_names:
            for location in compact_locations[:2]:
                plan.append((name, location))

        # Dernier recours : raison sociale avec les adresses complètes connues.
        # On garde une limite stricte afin de préserver la vitesse du Lot 2.
        if primary:
            for full_location in full_locations[:2]:
                pair = (primary, full_location)
                if pair not in plan:
                    plan.append(pair)

        return list(dict.fromkeys(plan))[:12]

    async def rechercher_nom(self, identity):
        """Recherche PagesJaunes par nom/raison sociale + localisation.

        Important : aucun SIRET/SIREN n'est envoyé dans la barre de recherche
        PagesJaunes. Ces identifiants servent seulement à valider/scorer les
        fiches obtenues lorsqu'ils sont présents dans leur contenu.
        """
        await self.ouvrir()
        self.last_errors = []

        plan = self._name_search_plan(identity)
        if not plan:
            return self._empty_result()

        best = None
        best_score = -999
        for quoiqui, location in plan:
            result = await self._search_once(identity, quoiqui, location)
            score = int(result.get("match_score") or 0)
            if score > best_score:
                best = result
                best_score = score
            if result.get("confidence") == "validated":
                return result

        return best or self._empty_result(self.last_errors)

    async def rechercher_identifiant(self, identity):
        """Compatibilité avec l'ancienne API, sans recherche par identifiant.

        Conservée pour éviter de casser un éventuel appel externe, mais elle
        délègue désormais à la recherche par nom/localisation.
        """
        return await self.rechercher_nom(identity)

    async def rechercher(self, identity):
        """Compatibilité avec l'ancienne API."""
        return await self.rechercher_nom(identity)
