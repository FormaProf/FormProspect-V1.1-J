from services.prospect_mapper import ProspectMapper

def blank():
    return {k: "" for k in ProspectMapper.DEPLOYMENT_COLUMNS}

def test_enriched_local_data_maps_to_cloud():
    row = blank()
    row.update(
        entreprise="Baza Etancheite",
        siret="12345678901234",
        siren="123456789",
        adresse="10 rue Test",
        code_postal="59000",
        ville="Lille",
        code_naf="4399A",
        telephone="0612345678",
        site_web="baza.example",
        email="contact@baza.example",
        linkedin="linkedin.com/company/baza",
        twitter="x.com/baza",
        social_other_urls="tiktok.com/@baza",
        statut_enrichissement="Enrichi",
        date_collecte="2026-08-12",
        pipeline="🔵 RDV programmé",
        priorite="⭐⭐⭐",
        commercial_assigne="Nacim",
        score_prospect=80,
    )
    p = ProspectMapper.from_sqlite(row)
    assert p["company_name"] == "Baza Etancheite"
    assert p["naf_code"] == "43.99A"
    assert p["website"] == "https://baza.example"
    assert p["linkedin"] == "https://linkedin.com/company/baza"
    assert p["twitter"] == "https://x.com/baza"
    assert p["pipeline_stage"] == "rdv_planifie"
    assert p["priority"] == "haute"
    assert p["enrichment_status"] == "enriched"
    assert p["enriched_at"].startswith("2026-08-12T")
    assert "commercial_assigne" not in p
    assert "score_prospect" not in p

def test_client_maps_to_gagne():
    row = blank()
    row["entreprise"] = "Client"
    row["pipeline"] = "🟢 Client"
    assert ProspectMapper.from_sqlite(row)["pipeline_stage"] == "gagne"

def test_invalid_siret_is_omitted():
    row = blank()
    row["entreprise"] = "Test"
    row["siret"] = "123"
    assert "siret" not in ProspectMapper.from_sqlite(row)

def test_other_urls_are_preserved():
    row = blank()
    row["entreprise"] = "Test"
    row["social_other_urls"] = "tiktok.com/@test;https://threads.net/@test"
    assert ProspectMapper.from_sqlite(row)["social_other_urls"].splitlines() == [
        "https://tiktok.com/@test",
        "https://threads.net/@test",
    ]
