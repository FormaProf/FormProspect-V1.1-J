from __future__ import annotations

import re
from urllib.parse import quote_plus

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from modules.browser_manager import BrowserManager
from modules.company_matcher import confidence, identity_locations, identity_names, score_candidate
from modules.contact_quality import extract_phones_from_text


class GoogleMapsFinder:
    RESULT_WAIT_MS = 3500
    PLACE_LIMIT = 3

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
        """Accepte automatiquement le consentement Google si nécessaire.

        Sur ``consent.google.com`` le bouton peut apparaître après le
        ``domcontentloaded``. L'ancien code abandonnait après 900 ms et marquait
        malgré tout la vérification comme terminée, d'où la validation manuelle.
        """
        if self._cookies_checked:
            return True

        current_url = str(getattr(self.page, "url", "") or "").lower()
        consent_page = "consent.google." in current_url
        button_pattern = re.compile(
            r"^(tout accepter|accepter tout|j['’]accepte|accept all|i agree)$",
            re.I,
        )

        if consent_page:
            # Une seule attente longue, uniquement sur la vraie page de
            # consentement. Cela n'ajoute aucun délai aux recherches suivantes.
            candidates = (
                self.page.get_by_role("button", name=button_pattern),
                self.page.locator("button").filter(has_text=button_pattern),
            )
            for idx, locator in enumerate(candidates):
                try:
                    target = locator.first
                    await target.wait_for(
                        state="visible",
                        timeout=6500 if idx == 0 else 1200,
                    )
                    await target.click(timeout=2500)
                    self._cookies_checked = True
                    try:
                        await self.page.wait_for_load_state(
                            "domcontentloaded", timeout=5000
                        )
                    except Exception:
                        pass
                    return True
                except Exception:
                    continue

            # Ne surtout pas passer le drapeau à True : une prochaine
            # navigation pourra retenter automatiquement.
            return False

        # Cas rare : bannière directement superposée à Maps. On ne fait aucune
        # attente coûteuse ; si un bouton est déjà visible on le clique.
        try:
            target = self.page.get_by_role("button", name=button_pattern).first
            if await target.count() and await target.is_visible():
                await target.click(timeout=1200)
        except Exception:
            pass

        self._cookies_checked = True
        return True

    @staticmethod
    def _empty_result(errors=None):
        return {
            "source": "google_maps",
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

    async def _extract_place(self):
        body = await self.page.inner_text("body")
        name = ""
        address = ""
        site_web = ""

        try:
            name = (
                await self.page.locator("h1").first.inner_text(timeout=2200)
            ).strip()
        except Exception:
            pass

        for selector in (
            'button[data-item-id="address"]',
            'button[aria-label^="Adresse"]',
            'button[aria-label*="Adresse"]',
        ):
            try:
                el = self.page.locator(selector).first
                if await el.count():
                    label = await el.get_attribute("aria-label")
                    text = await el.inner_text()
                    address = (label or text or "").strip()
                    address = re.sub(
                        r"^\s*Adresse\s*:?\s*",
                        "",
                        address,
                        flags=re.I,
                    )
                    if address:
                        break
            except Exception:
                continue

        for selector in (
            'a[data-item-id="authority"]',
            'a[aria-label^="Site Web"]',
            'a[aria-label*="Site web"]',
        ):
            try:
                el = self.page.locator(selector).first
                if await el.count():
                    href = (await el.get_attribute("href") or "").strip()
                    if href.startswith("http"):
                        site_web = href
                        break
            except Exception:
                continue

        semantic_chunks = []
        try:
            loc = self.page.locator(
                'button[data-item-id^="phone"],'
                'button[aria-label^="Téléphone"],'
                'button[aria-label*="Téléphone"],'
                'a[href^="tel:"]'
            )
            for i in range(min(await loc.count(), 8)):
                el = loc.nth(i)
                label = await el.get_attribute("aria-label")
                text = await el.inner_text()
                href = await el.get_attribute("href")
                semantic_chunks.append(" ".join(x for x in (label, text, href) if x))
        except Exception:
            pass

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

        # Lot 1.2 : pas de fallback sur le texte complet de Google Maps.
        # Le corps de page peut contenir des numéros provenant de résultats
        # voisins, d'annonces ou d'éléments d'interface. On ne conserve donc
        # que les numéros issus des contrôles explicitement rattachés à la
        # fiche ouverte (bouton téléphone / lien tel:).

        phones = sorted(
            dict.fromkeys(classified["phone"] + classified["mobile"]),
            key=self._phone_sort_key,
        )
        cp_match = re.search(r"\b(\d{5})\b", address or body)

        return {
            "source": "google_maps",
            "nom": name,
            "adresse": address,
            "code_postal": cp_match.group(1) if cp_match else "",
            "ville": "",
            "telephones": phones,
            "faxes": classified["fax"],
            "site_web": site_web,
            "texte": body[:12000],
        }

    async def _wait_for_results(self):
        # Google Maps peut arriver soit sur une liste, soit directement sur une
        # fiche. On attend l'un des éléments utiles, sans imposer plusieurs
        # secondes de pause fixe à chaque prospect.
        selector = (
            'a[href*="/maps/place/"], h1, '
            'button[data-item-id="address"], '
            'button[data-item-id^="phone"]'
        )
        try:
            await self.page.locator(selector).first.wait_for(
                state="attached",
                timeout=self.RESULT_WAIT_MS,
            )
        except PlaywrightTimeoutError:
            pass

    @staticmethod
    def _search_queries(identity):
        entreprise = str(identity.get("entreprise") or "").strip()

        # Lot 2.2 : les alias et implantations des autres établissements du même
        # SIREN peuvent aussi servir à trouver la fiche publique du siège.
        names = identity_names(identity)
        aliases = [name for name in names if name != entreprise][:4]
        ordered_names = aliases + ([entreprise] if entreprise else [])
        locations = identity_locations(identity)[:3]
        if not locations:
            locations = [{"adresse": "", "code_postal": "", "ville": ""}]

        queries = []
        for name in ordered_names:
            for location in locations[:2]:
                query = " ".join(
                    value
                    for value in (
                        name,
                        str(location.get("code_postal") or "").strip(),
                        str(location.get("ville") or "").strip(),
                    )
                    if value
                )
                if query:
                    queries.append(query)

        # Dernier recours : raison sociale + adresses complètes du SIREN.
        if entreprise:
            for location in locations[:2]:
                full_query = " ".join(
                    value
                    for value in (
                        entreprise,
                        str(location.get("adresse") or "").strip(),
                        str(location.get("code_postal") or "").strip(),
                        str(location.get("ville") or "").strip(),
                    )
                    if value
                )
                if full_query:
                    queries.append(full_query)

        return list(dict.fromkeys(queries))[:12]

    async def rechercher(self, identity):
        await self.ouvrir()
        self.last_errors = []
        queries = self._search_queries(identity)

        best = None
        best_score = -999

        for recherche in dict.fromkeys(q for q in queries if q):
            url = "https://www.google.com/maps/search/" + quote_plus(recherche)
            try:
                await self.page.goto(
                    url,
                    timeout=30000,
                    wait_until="domcontentloaded",
                )
                await self._accept_cookies_once()
                await self._wait_for_results()
            except Exception as exc:
                self.last_errors.append(
                    f"recherche '{recherche}': {type(exc).__name__}: {exc}"
                )
                continue

            hrefs = []
            current_url = self.page.url or ""
            if "/maps/place/" in current_url:
                hrefs.append(current_url)

            try:
                links = self.page.locator('a[href*="/maps/place/"]')
                for i in range(min(await links.count(), self.PLACE_LIMIT)):
                    href = await links.nth(i).get_attribute("href")
                    if href and href not in hrefs:
                        hrefs.append(href)
            except Exception as exc:
                self.last_errors.append(
                    f"lecture résultats Google Maps: {type(exc).__name__}: {exc}"
                )

            # Si Maps a chargé directement une fiche sans URL /maps/place/, on
            # inspecte tout de même la page courante.
            targets = hrefs or [current_url]
            for href in targets[: self.PLACE_LIMIT]:
                try:
                    if href and href != self.page.url:
                        await self.page.goto(
                            href,
                            timeout=30000,
                            wait_until="domcontentloaded",
                        )
                        await self._wait_for_results()

                    candidate = await self._extract_place()
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
                        f"fiche Google Maps: {type(exc).__name__}: {exc}"
                    )

        if best:
            best["technical_errors"] = list(self.last_errors)
            return best
        return self._empty_result(self.last_errors)
