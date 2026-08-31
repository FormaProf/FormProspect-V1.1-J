import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class SocialFinder:
    OTHER_DOMAINS = (
        "tiktok.com", "threads.net", "pinterest.", "snapchat.com",
        "wa.me", "whatsapp.com", "telegram.me", "t.me",
    )

    GENERIC_PATH_PARTS = {
        "", "/", "/home", "/login", "/signin", "/signup", "/register",
        "/share", "/shares", "/sharer", "/dialog", "/plugins",
        "/intent", "/oauth", "/watch", "/feed", "/explore",
    }

    @staticmethod
    def _valid(value):
        value = str(value or "").strip()
        if not value:
            return ""
        parsed = urlparse(value)
        return value if parsed.scheme in {"http", "https"} else ""

    @classmethod
    def _is_generic_social_url(cls, value, platform=""):
        """Écarte les liens vers l'accueil/connexion/partage d'un réseau.

        L'enrichissement ne doit compter qu'une URL de profil/page réelle.
        Exemples rejetés : facebook.com/, instagram.com/, linkedin.com/login,
        facebook.com/sharer.php, x.com/intent/....
        """
        value = cls._valid(value)
        if not value:
            return True

        parsed = urlparse(value)
        host = (parsed.netloc or "").lower().split(":", 1)[0]
        if host.startswith("www."):
            host = host[4:]
        path = (parsed.path or "/").rstrip("/").lower() or "/"

        # Racine ou pages génériques connues.
        if path in cls.GENERIC_PATH_PARTS:
            return True

        parts = [part for part in path.split("/") if part]
        if not parts:
            return True
        first = parts[0]

        generic_first = {
            "login", "signin", "signup", "register", "share", "shares",
            "sharer", "dialog", "plugins", "intent", "oauth", "home",
            "feed", "explore", "search", "help", "privacy", "terms",
        }
        if first in generic_first:
            return True

        # LinkedIn : /company/... ou /in/... sont exploitables. Les autres
        # routes institutionnelles/génériques ne sont pas considérées comme
        # des profils prospects.
        if platform == "linkedin":
            return not (len(parts) >= 2 and first in {"company", "in", "school", "showcase"})

        # YouTube : accepter une chaîne/handle, pas la page d'accueil ni les
        # URL de partage génériques. Une vidéo seule n'est pas un profil social
        # de l'entreprise et n'est donc pas retenue comme chaîne.
        if platform == "youtube":
            if first in {"channel", "c", "user"} and len(parts) >= 2:
                return False
            if first.startswith("@") and len(first) > 1:
                return False
            return True

        # Facebook/Instagram/X : un premier segment distinctif suffit pour
        # représenter une page ou un profil, après exclusion des routes génériques.
        return False

    @classmethod
    def _social_profile(cls, href, platform):
        href = cls._valid(href)
        if not href or cls._is_generic_social_url(href, platform):
            return ""
        return href

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
                    profile = self._social_profile(href, "facebook")
                    if profile:
                        resultats["facebook"] = profile
                elif "linkedin.com" in low and not resultats["linkedin"]:
                    profile = self._social_profile(href, "linkedin")
                    if profile:
                        resultats["linkedin"] = profile
                elif "instagram.com" in low and not resultats["instagram"]:
                    profile = self._social_profile(href, "instagram")
                    if profile:
                        resultats["instagram"] = profile
                elif ("twitter.com" in low or "x.com" in low) and not resultats["twitter"]:
                    profile = self._social_profile(href, "twitter")
                    if profile:
                        resultats["twitter"] = profile
                elif ("youtube.com" in low or "youtu.be" in low) and not resultats["youtube"]:
                    profile = self._social_profile(href, "youtube")
                    if profile:
                        resultats["youtube"] = profile
                elif any(domain in low for domain in self.OTHER_DOMAINS):
                    # Les autres réseaux ne sont conservés que si l'URL pointe
                    # vers quelque chose de plus précis que leur racine.
                    if not self._is_generic_social_url(href) and href not in resultats["other_urls"]:
                        resultats["other_urls"].append(href)
        except Exception:
            pass
        return resultats
