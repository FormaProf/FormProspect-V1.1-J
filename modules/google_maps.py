import re
import time
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

from modules.browser_manager import BrowserManager


class GoogleMapsFinder:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    def ouvrir(self):
        if self.browser is not None:
            return

        try:
            self.playwright = sync_playwright().start()
            self.browser = BrowserManager.launch(self.playwright, headless=False)
            self.page = self.browser.new_page()
        except Exception:
            self.fermer()
            raise

    def fermer(self):
        if self.browser:
            try:
                self.browser.close()
            finally:
                self.browser = None
                self.page = None

        if self.playwright:
            try:
                self.playwright.stop()
            finally:
                self.playwright = None

    def extraire_telephones(self, texte):
        pattern = r"(?:0|\+33\s?)[1-9](?:[\s.-]?\d{2}){4}"
        numeros = re.findall(pattern, texte)

        propres = []
        for numero in numeros:
            numero = numero.replace(".", " ").replace("-", " ")
            numero = re.sub(r"\s+", " ", numero).strip()
            if numero.startswith("+33"):
                numero = numero.replace("+33", "0", 1).strip()
            if numero not in propres:
                propres.append(numero)

        return propres

    def choisir_meilleur_numero(self, numeros):
        mobiles = [n for n in numeros if n.startswith("06") or n.startswith("07")]
        fixes = [n for n in numeros if n.startswith(("01", "02", "03", "04", "05"))]

        if mobiles:
            return mobiles[0]
        if fixes:
            return fixes[0]
        if numeros:
            return numeros[0]
        return ""

    def extraire_site(self):
        exclusions = [
            "google.",
            "gstatic.",
            "ggpht.",
            "schema.org",
            "facebook.com",
            "instagram.com",
            "linkedin.com",
            "youtube.com",
            "support.google",
            "policies.google",
            "accounts.google",
        ]

        try:
            liens = self.page.locator("a").evaluate_all(
                "(elements) => elements.map(e => e.href).filter(Boolean)"
            )

            for lien in liens:
                lien_min = lien.lower()

                if not lien.startswith("http"):
                    continue
                if any(exclu in lien_min for exclu in exclusions):
                    continue
                if "maps/place" in lien_min:
                    continue
                if "search?" in lien_min:
                    continue

                return lien

        except Exception:
            return ""

        return ""

    def rechercher(self, entreprise, code_postal, ville):
        self.ouvrir()

        recherche = f"{entreprise} {code_postal} {ville}"
        url = "https://www.google.com/maps/search/" + quote_plus(recherche)

        try:
            self.page.goto(url, timeout=60000)
            time.sleep(7)

            try:
                self.page.get_by_role("button", name="Tout accepter").click(timeout=3000)
                time.sleep(2)
                self.page.goto(url, timeout=60000)
                time.sleep(7)
            except Exception:
                pass

            contenu = self.page.inner_text("body")
            numeros = self.extraire_telephones(contenu)

            return {
                "telephone": self.choisir_meilleur_numero(numeros),
                "site_web": self.extraire_site(),
            }

        except Exception:
            return {
                "telephone": "",
                "site_web": "",
            }
