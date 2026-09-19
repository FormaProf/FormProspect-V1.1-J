from services.dashboard_data_provider import CloudDashboardDataProvider
from services.prospect_data_provider import CloudProspectDataProvider


def test_cloud_provider_counts_phone_or_mobile_once():
    provider = CloudProspectDataProvider(
        api_client=object(),
        project_id="project-123",
    )

    items = [
        {"id": "p1", "company_name": "Fixe", "phone": "01 11 11 11 11", "mobile": ""},
        {"id": "p2", "company_name": "Mobile", "phone": "", "mobile": "06 22 22 22 22"},
        {"id": "p3", "company_name": "Les deux", "phone": "03 33 33 33 33", "mobile": "07 33 33 33 33"},
        {"id": "p4", "company_name": "Aucun", "phone": "", "mobile": ""},
    ]

    provider._list = lambda **kwargs: [
        provider._row(item) for item in items
    ]

    assert provider.count_with_phone() == 3


def test_cloud_dashboard_counts_phone_or_mobile_once():
    provider = CloudDashboardDataProvider(
        api_client=object(),
        project_id="project-123",
    )

    provider._load_all_prospects = lambda: [
        {"id": "p1", "company_name": "Fixe", "phone": "01 11 11 11 11", "mobile": ""},
        {"id": "p2", "company_name": "Mobile", "phone": "", "mobile": "06 22 22 22 22"},
        {"id": "p3", "company_name": "Les deux", "phone": "03 33 33 33 33", "mobile": "07 33 33 33 33"},
        {"id": "p4", "company_name": "Aucun", "phone": "", "mobile": ""},
    ]

    data = provider.get_dashboard_data()

    assert data["kpi"]["prospects"] == 4
    assert data["kpi"]["telephones"] == 3
    assert data["quality"]["telephone"]["value"] == 3
    assert data["quality"]["telephone"]["percentage"] == 75
    assert data["kpi"]["quality_score"] == 19
    assert ("Téléphones", 3) in data["contact_distribution"]
    assert data["activity"]["missing_phone"] == 1
