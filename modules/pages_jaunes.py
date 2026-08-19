from __future__ import annotations

import asyncio
import re
from urllib.parse import urlencode, urljoin, urlparse

from playwright.async_api import async_playwright

from modules.browser_manager import BrowserManager
from modules.company_matcher import score_candidate, confidence


class PagesJaunesFinder:
    SEARCH_URL = "https://www.pagesjaunes.fr/annuaire/chercherlespros"

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
        out = []
        for numero in re.findall(pattern, str(texte or "")):
            compact = re.sub(r"\D", "", numero)
            if numero.strip().startswith("+33"):
                compact = "0" + compact[2:]
            if len(compact) == 10 and compact.startswith("0"):
                formatted = " ".join(
                    compact[i:i + 2] for i in range(0, 10, 2)
                )
                if formatted not in out:
                    out.append(formatted)
        return out

    @staticmethod
    def _phone_sort_key(numero):
        compact = re.sub(r"\D", "", numero)
        return (
            0 if compact.startswith(("06", "07")) else 1,
            compact,
        )

    async def _accept_cookies(self):
        for label in ("Tout accepter", "Accepter", "J'accepte"):
            try:
                await self.page.get_by_role(
                    "button",
                    name=label,
                ).click(timeout=1500)
                await asyncio.sleep(1)
                return
            except Exception:
                pass

    @staticmethod
    def _external_site(links):
        excluded = (
            "pagesjaunes.fr",
            "solocal.com",
            "facebook.com",
            "instagram.com",
            "linkedin.com",
            "youtube.com",
            "twitter.com",
            "x.com",
        )
        for href in links:
            try:
                host = urlparse(href).netloc.lower()
            except Exception:
                continue
            if (
                href.startswith("http")
                and host
                and not any(item in host for item in excluded)
            ):
                return href
        return ""

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
                pass

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
                pass

        if candidates:
            address = max(candidates, key=len)

        phones = sorted(
            dict.fromkeys(self.extraire_telephones(body)),
            key=self._phone_sort_key,
        )

        try:
            links = await self.page.locator("a").evaluate_all(
                "(els) => els.map(e => e.href).filter(Boolean)"
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
            "site_web": self._external_site(links),
            "texte": body[:16000],
        }

    async def rechercher(self, identity):
        await self.ouvrir()

        entreprise = str(identity.get("entreprise") or "").strip()
        adresse = str(identity.get("adresse") or "").strip()
        code_postal = str(identity.get("code_postal") or "").strip()
        ville = str(identity.get("ville") or "").strip()

        location = " ".join(
            value
            for value in (
                adresse,
                code_postal,
                ville,
            )
            if value
        ) or ville

        url = (
            self.SEARCH_URL
            + "?"
            + urlencode(
                {
                    "quoiqui": entreprise,
                    "ou": location,
                }
            )
        )

        best = None
        best_score = -999

        try:
            await self.page.goto(
                url,
                timeout=60000,
                wait_until="domcontentloaded",
            )
            await asyncio.sleep(4)
            await self._accept_cookies()
            await asyncio.sleep(2)

            links = self.page.locator('a[href*="/pros/"]')
            hrefs = []

            for i in range(min(await links.count(), 6)):
                href = await links.nth(i).get_attribute("href")
                if href:
                    href = urljoin(
                        "https://www.pagesjaunes.fr",
                        href,
                    )
                    if href not in hrefs:
                        hrefs.append(href)

            for href in hrefs:
                try:
                    await self.page.goto(
                        href,
                        timeout=60000,
                        wait_until="domcontentloaded",
                    )
                    await asyncio.sleep(3)

                    candidate = await self._extract_profile()
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
            pass

        return best or {
            "source": "pages_jaunes",
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
