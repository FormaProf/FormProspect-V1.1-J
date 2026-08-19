import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class EmailFinder:
    def extraire_emails(self, texte):
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        emails = re.findall(pattern, texte)

        propres = []
        exclusions = ["example@", "test@", "noreply@", "no-reply@"]

        for email in emails:
            email = email.strip().lower()
            if any(exclu in email for exclu in exclusions):
                continue
            if email not in propres:
                propres.append(email)

        return propres

    def chercher(self, site_web):
        if not site_web or str(site_web).strip() in ["", "nan", "None"]:
            return ""

        if not site_web.startswith("http"):
            site_web = "https://" + site_web

        pages = [
            site_web,
            urljoin(site_web, "/contact"),
            urljoin(site_web, "/contactez-nous"),
            urljoin(site_web, "/nous-contacter"),
            urljoin(site_web, "/mentions-legales"),
        ]

        headers = {"User-Agent": "Mozilla/5.0"}

        for url in pages:
            try:
                r = requests.get(url, headers=headers, timeout=10)
                texte = r.text

                emails = self.extraire_emails(texte)
                if emails:
                    return emails[0]

                soup = BeautifulSoup(texte, "lxml")
                for lien in soup.select('a[href^="mailto:"]'):
                    email = lien.get("href", "").replace("mailto:", "").split("?")[0].strip().lower()
                    if email:
                        return email

            except Exception:
                continue

        return ""