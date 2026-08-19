import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class SocialFinder:
    OTHER_DOMAINS = (
        "tiktok.com", "threads.net", "pinterest.", "snapchat.com",
        "wa.me", "whatsapp.com", "telegram.me", "t.me",
    )

    @staticmethod
    def _valid(value):
        value = str(value or "").strip()
        if not value:
            return ""
        parsed = urlparse(value)
        return value if parsed.scheme in {"http", "https"} else ""

    def chercher(self, site_web):
        resultats = {
            "facebook": "", "linkedin": "", "instagram": "",
            "twitter": "", "youtube": "", "other_urls": [],
        }
        if not site_web or str(site_web).strip() in {"", "nan", "None"}:
            return resultats

        site_web = str(site_web).strip()
        if not site_web.startswith(("http://", "https://")):
            site_web = "https://" + site_web

        try:
            response = requests.get(
                site_web,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            for anchor in soup.find_all("a", href=True):
                href = self._valid(urljoin(site_web, anchor["href"]))
                if not href:
                    continue
                low = href.lower()
                if "facebook.com" in low and not resultats["facebook"]:
                    resultats["facebook"] = href
                elif "linkedin.com" in low and not resultats["linkedin"]:
                    resultats["linkedin"] = href
                elif "instagram.com" in low and not resultats["instagram"]:
                    resultats["instagram"] = href
                elif ("twitter.com" in low or "x.com" in low) and not resultats["twitter"]:
                    resultats["twitter"] = href
                elif ("youtube.com" in low or "youtu.be" in low) and not resultats["youtube"]:
                    resultats["youtube"] = href
                elif any(domain in low for domain in self.OTHER_DOMAINS):
                    if href not in resultats["other_urls"]:
                        resultats["other_urls"].append(href)
        except Exception:
            pass
        return resultats
