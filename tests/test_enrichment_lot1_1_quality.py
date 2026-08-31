from modules.contact_quality import extract_phones_from_text
from modules.email_finder import EmailFinder
from services.enrichment_service import EnrichmentService


def test_context_phone_filter_drops_fax_and_unlabelled_number():
    text = (
        "Téléphone : 01 39 19 22 26\n"
        "Fax : 01 39 19 22 00\n"
        "Référence interne 01 72 54 16 66"
    )
    result = extract_phones_from_text(text, require_contact_hint=True)
    assert result["phone"] == ["01 39 19 22 26"]
    assert "01 39 19 22 00" in result["fax"]
    assert "01 72 54 16 66" not in result["phone"]


def test_mobile_is_classified_separately():
    result = extract_phones_from_text("Portable : 06 12 34 56 78")
    assert result["mobile"] == ["06 12 34 56 78"]
    assert result["phone"] == []


def test_email_finder_rejects_wix_sentry_hash():
    finder = EmailFinder()
    html = """
    <html><body>
      <script>var x='605a7baede844d278b89dc95ae0a9123@sentry-next.wixpress.com';</script>
      <p>Contactez-nous à contact@ets-sciarini.com</p>
    </body></html>
    """
    candidates = finder._candidates_from_html(html, "ets-sciarini.com")
    emails = [item[1] for item in candidates]
    assert "605a7baede844d278b89dc95ae0a9123@sentry-next.wixpress.com" not in emails
    assert "contact@ets-sciarini.com" in emails


def test_email_finder_keeps_external_business_email_when_visible():
    finder = EmailFinder()
    html = "<html><body><p>Email : thermeca@free.fr</p></body></html>"
    candidates = finder._candidates_from_html(
        html,
        "thermeca-chauffagiste-94.fr",
    )
    assert any(item[1] == "thermeca@free.fr" for item in candidates)


def test_email_finder_prefers_mailto_official_domain():
    finder = EmailFinder()
    html = """
    <html><body>
      <p>Ancienne adresse : artisan@gmail.com</p>
      <a href="mailto:contact@entreprise.fr">Nous écrire</a>
    </body></html>
    """
    candidates = finder._candidates_from_html(html, "entreprise.fr")
    best = max(candidates, key=lambda item: item[0])
    assert best[1] == "contact@entreprise.fr"
    assert best[2] == "mailto"


def test_service_keeps_all_validated_phone_sources():
    valid = [
        {
            "source": "pages_jaunes",
            "match_score": 200,
            "telephones": ["01 39 19 22 26"],
        },
        {
            "source": "google_maps",
            "match_score": 120,
            "telephones": ["01 72 54 16 66"],
        },
    ]
    phones, source = EnrichmentService._select_contact_numbers(valid)
    assert phones == ["01 39 19 22 26", "01 72 54 16 66"]
    assert source == "pages_jaunes + google_maps"


def test_sanitize_existing_contacts_removes_only_known_technical_email(tmp_path):
    import sqlite3

    db = tmp_path / "project.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE prospects (id INTEGER PRIMARY KEY, email TEXT)")
    con.executemany(
        "INSERT INTO prospects (id, email) VALUES (?, ?)",
        [
            (1, "605a7baede844d278b89dc95ae0a9123@sentry-next.wixpress.com"),
            (2, "thermeca@free.fr"),
        ],
    )
    con.commit()

    service = EnrichmentService()
    cleaned = service._sanitize_existing_contacts(con)
    rows = dict(con.execute("SELECT id, email FROM prospects").fetchall())
    con.close()

    assert cleaned == 1
    assert rows[1] == ""
    assert rows[2] == "thermeca@free.fr"
