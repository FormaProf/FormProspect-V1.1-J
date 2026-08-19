from __future__ import annotations

import asyncio
import re
from urllib.parse import quote_plus

from playwright.async_api import async_playwright

from modules.browser_manager import BrowserManager
from modules.company_matcher import score_candidate, confidence


class GoogleMapsFinder:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

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

    @staticmethod
    def extraire_telephones(texte):
        pattern = r"(?:0|\+33\s?)[1-9](?:[\s.\-]?\d{2}){4}"
        propres = []
        for numero in re.findall(pattern, str(texte or "")):
            compact = re.sub(r"\D", "", numero)
            if numero.strip().startswith("+33"):
                compact = "0" + compact[2:]
            if len(compact) == 10 and compact.startswith("0"):
                formatted = " ".join(
                    compact[i:i + 2] for i in range(0, 10, 2)
                )
                if formatted not in propres:
                    propres.append(formatted)
        return propres

    @staticmethod
    def _phone_sort_key(numero):
        compact = re.sub(r"\D", "", numero)
        return (
            0 if compact.startswith(("06", "07")) else 1,
            compact,
        )

    async def _accept_cookies(self):
        for label in ("Tout accepter", "Accepter tout"):
            try:
                await self.page.get_by_role(
                    "button",
                    name=label,
                ).click(timeout=1800)
                await asyncio.sleep(1)
                return
            except Exception:
                pass

    async def _extract_place(self):
        body = await self.page.inner_text("body")
        name = ""
        address = ""
        site_web = ""

        try:
            name = (
                await self.page.locator("h1").first.inner_text(timeout=2500)
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
                pass

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
                pass

        phones = []
        try:
            loc = self.page.locator(
                'button[data-item-id^="phone"],'
                'button[aria-label^="Téléphone"],'
                'button[aria-label*="Téléphone"]'
            )
            for i in range(min(await loc.count(), 8)):
                el = loc.nth(i)
                label = await el.get_attribute("aria-label")
                text = await el.inner_text()
                phones += self.extraire_telephones(
                    (label or "") + " " + (text or "")
                )
        except Exception:
            pass

        if not phones:
            phones = self.extraire_telephones(body)

        phones = sorted(
            dict.fromkeys(phones),
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
            "site_web": site_web,
            "texte": body[:12000],
        }

    async def rechercher(self, identity):
        await self.ouvrir()

        entreprise, adresse, code_postal, ville = [
            str(identity.get(key) or "").strip()
            for key in ("entreprise", "adresse", "code_postal", "ville")
        ]

        queries = [
            " ".join(
                value
                for value in (
                    entreprise,
                    adresse,
                    code_postal,
                    ville,
                )
                if value
            ),
            " ".join(
                value
                for value in (
                    entreprise,
                    code_postal,
                    ville,
                )
                if value
            ),
        ]

        best = None
        best_score = -999

        for recherche in dict.fromkeys(q for q in queries if q):
            url = (
                "https://www.google.com/maps/search/"
                + quote_plus(recherche)
            )
            try:
                await self.page.goto(
                    url,
                    timeout=60000,
                    wait_until="domcontentloaded",
                )
                await asyncio.sleep(4)
                await self._accept_cookies()
                await asyncio.sleep(2)

                links = self.page.locator('a[href*="/maps/place/"]')
                hrefs = []

                try:
                    for i in range(min(await links.count(), 5)):
                        href = await links.nth(i).get_attribute("href")
                        if href and href not in hrefs:
                            hrefs.append(href)
                except Exception:
                    pass

                current_url = self.page.url
                for href in (hrefs or [current_url]):
                    try:
                        if href != self.page.url:
                            await self.page.goto(
                                href,
                                timeout=60000,
                                wait_until="domcontentloaded",
                            )
                            await asyncio.sleep(3)

                        candidate = await self._extract_place()
                        score, reasons = score_candidate(
                            identity,
                            candidate,
                        )
                        candidate.update(
                            match_score=score,
                            match_reasons=reasons,
                            confidence=confidence(score),
                        )

                        if score > best_score:
                            best = candidate
                            best_score = score

                        if candidate["confidence"] == "validated":
                            return candidate
                    except Exception:
                        continue
            except Exception:
                continue

        return best or {
            "source": "google_maps",
            "nom": "",
            "adresse": "",
            "code_postal": "",
            "ville": "",
            "telephones": [],
            "site_web": "",
            "texte": "",
            "match_score": 0,
            "match_reasons": [],
            "confidence": "rejected",
        }
