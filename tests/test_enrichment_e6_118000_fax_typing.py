import importlib


def test_118000_explicit_fax_is_typed_and_removed_from_phones(monkeypatch):
    module = importlib.import_module("modules.annuaire_118000")
    html = """
    <html><body>
      <div class="card">
        <div data-info='{"address":"7 AVENUE CARNOT",
        "mainLine":"0134512677","tel":"0134512677","fax":"0130741632",
        "urlDetail":"https://www.118000.fr/e_TEST","name":"ENTREPRISE NADOT",
        "cp":"78100","city":"SAINT GERMAIN EN LAYE"}'></div>
        ENTREPRISE NADOT 7 AVENUE CARNOT 78100 SAINT GERMAIN EN LAYE
        Téléphone 01 34 51 26 77 Fax : 01 30 74 16 32
      </div>
    </body></html>
    """

    class Response:
        status_code = 200
        text = html
        url = "https://www.118000.fr/search?who=NADOT&label=78100"

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(
        "modules.annuaire_118000.requests.get",
        lambda *args, **kwargs: Response(),
    )

    finder = module.Annuaire118000Finder()
    identity = {
        "entreprise": "ENTREPRISE NADOT",
        "siret": "31035888200028",
        "siren": "310358882",
        "adresse": "7 AVENUE CARNOT",
        "code_postal": "78100",
        "ville": "SAINT-GERMAIN-EN-LAYE",
        "noms_recherche": ["ENTREPRISE NADOT", "NADOT"],
        "localisations_recherche": [
            {
                "adresse": "7 AVENUE CARNOT 78100 SAINT-GERMAIN-EN-LAYE",
                "code_postal": "78100",
                "ville": "SAINT-GERMAIN-EN-LAYE",
            }
        ],
    }

    result = finder.rechercher(identity)
    assert "01 34 51 26 77" in result["telephones"]
    assert "01 30 74 16 32" in result["faxes"]
    assert "01 30 74 16 32" not in result["telephones"]
