import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


class SocialFinder:
    def chercher(self, site_web):
        resultats = {
            "facebook": "",
            "linkedin": "",
            "instagram": "",
            "youtube": "",
        }

        if not site_web or str(site_web).strip() in ["", "nan", "None"]:
            return resultats

        if not site_web.startswith("http"):
            site_web = "https://" + site_web

        try:
            r = requests.get(site_web, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(r.text, "lxml")

            for lien in soup.find_all("a", href=True):
                href = urljoin(site_web, lien["href"])
                href_min = href.lower()

                if "facebook.com" in href_min and not resultats["facebook"]:
                    resultats["facebook"] = href
                elif "linkedin.com" in href_min and not resultats["linkedin"]:
                    resultats["linkedin"] = href
                elif "instagram.com" in href_min and not resultats["instagram"]:
                    resultats["instagram"] = href
                elif ("youtube.com" in href_min or "youtu.be" in href_min) and not resultats["youtube"]:
                    resultats["youtube"] = href

        except Exception:
            pass

        return resultats