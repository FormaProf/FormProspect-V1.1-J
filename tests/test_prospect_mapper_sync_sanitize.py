from services.prospect_mapper import ProspectMapper


def _row(**changes):
    values = {name: "" for name in ProspectMapper.DEPLOYMENT_COLUMNS}
    values.update({
        "id": 1,
        "entreprise": "Entreprise test",
        "telephone": "04 91 66 18 36 / 09 70 11 22 33",
        "mobile": "06 12 34 56 78 / 07 98 76 54 32",
        "pipeline": "Nouveau",
        "priorite": "Normal",
    })
    values.update(changes)
    return values


def test_mapper_preserves_all_phone_and_mobile_values():
    payload = ProspectMapper.from_sqlite(_row())
    assert payload["phone"] == "04 91 66 18 36 / 09 70 11 22 33"
    assert payload["mobile"] == "06 12 34 56 78 / 07 98 76 54 32"


def test_invalid_email_is_omitted_from_cloud_payload():
    payload = ProspectMapper.from_sqlite(_row(email="contact at entreprise.fr"))
    assert "email" not in payload


def test_valid_email_is_kept():
    payload = ProspectMapper.from_sqlite(_row(email="contact@entreprise.fr"))
    assert payload["email"] == "contact@entreprise.fr"
