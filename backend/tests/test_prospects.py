import uuid

from backend.app.models import OrganizationMembership, UserProfile


def _add_user(test_context, *, role: str, organization_id=None):
    auth_user_id = uuid.uuid4()
    user_id = uuid.uuid4()
    organization_id = organization_id or test_context["org_id"]
    with test_context["session_factory"]() as db:
        db.add(
            UserProfile(
                id=user_id,
                auth_user_id=auth_user_id,
                email=f"{role}-{user_id}@example.test",
            )
        )
        db.add(
            OrganizationMembership(
                organization_id=organization_id,
                user_id=user_id,
                role=role,
                is_active=True,
            )
        )
        db.commit()
    headers = {
        "Authorization": f"Bearer {test_context['token'](auth_user_id)}",
        "X-Organization-ID": str(organization_id),
        "X-Device-ID": role,
    }
    return user_id, headers


def test_admin_crud_search_archive_restore(test_context, auth_headers):
    client = test_context["client"]
    created = client.post(
        "/api/v1/prospects",
        headers=auth_headers,
        json={
            "company_name": "  Entreprise ABC  ",
            "email": "contact@example.com",
            "city": "Lille",
        },
    )
    assert created.status_code == 201, created.text
    prospect = created.json()
    assert prospect["company_name"] == "Entreprise ABC"
    assert prospect["owner_user_id"] == str(test_context["user_id"])

    listed = client.get("/api/v1/prospects", headers=auth_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = client.patch(
        f"/api/v1/prospects/{prospect['id']}",
        headers=auth_headers,
        json={"pipeline_stage": "qualifie"},
    )
    assert updated.status_code == 200
    assert updated.json()["pipeline_stage"] == "qualifie"

    filtered = client.get(
        "/api/v1/prospects?pipeline_stage=qualifie&search=Lille",
        headers=auth_headers,
    )
    assert filtered.status_code == 200
    assert len(filtered.json()) == 1

    archived = client.post(
        f"/api/v1/prospects/{prospect['id']}/archive",
        headers=auth_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert client.get("/api/v1/prospects", headers=auth_headers).json() == []

    archived_items = client.get(
        "/api/v1/prospects?include_archived=true",
        headers=auth_headers,
    )
    assert len(archived_items.json()) == 1

    restored = client.post(
        f"/api/v1/prospects/{prospect['id']}/restore",
        headers=auth_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_commercial_only_sees_and_updates_owned_prospects(test_context, auth_headers):
    commercial_user_id, commercial_headers = _add_user(test_context, role="commercial")
    admin_prospect = test_context["client"].post(
        "/api/v1/prospects",
        headers=auth_headers,
        json={"company_name": "Admin prospect"},
    ).json()

    created = test_context["client"].post(
        "/api/v1/prospects",
        headers=commercial_headers,
        json={"company_name": "Commercial prospect"},
    )
    assert created.status_code == 201
    assert created.json()["owner_user_id"] == str(commercial_user_id)

    items = test_context["client"].get(
        "/api/v1/prospects",
        headers=commercial_headers,
    ).json()
    assert [item["company_name"] for item in items] == ["Commercial prospect"]

    hidden = test_context["client"].get(
        f"/api/v1/prospects/{admin_prospect['id']}",
        headers=commercial_headers,
    )
    assert hidden.status_code == 404

    own_update = test_context["client"].patch(
        f"/api/v1/prospects/{created.json()['id']}",
        headers=commercial_headers,
        json={"city": "Roubaix"},
    )
    assert own_update.status_code == 200
    assert own_update.json()["city"] == "Roubaix"

    forbidden_assignment = test_context["client"].post(
        "/api/v1/prospects",
        headers=commercial_headers,
        json={
            "company_name": "Forbidden",
            "owner_user_id": str(test_context["user_id"]),
        },
    )
    assert forbidden_assignment.status_code == 403


def test_manager_can_assign_and_update_all(test_context):
    manager_user_id, manager_headers = _add_user(test_context, role="manager")
    commercial_user_id, _ = _add_user(test_context, role="commercial")

    response = test_context["client"].post(
        "/api/v1/prospects",
        headers=manager_headers,
        json={
            "company_name": "Prospect affecté",
            "owner_user_id": str(commercial_user_id),
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["owner_user_id"] == str(commercial_user_id)

    updated = test_context["client"].patch(
        f"/api/v1/prospects/{response.json()['id']}",
        headers=manager_headers,
        json={"source": "salon"},
    )
    assert updated.status_code == 200
    assert updated.json()["source"] == "salon"
    assert manager_user_id != commercial_user_id


def test_cross_tenant_owner_is_rejected(test_context, auth_headers):
    other_user_id, _ = _add_user(
        test_context,
        role="commercial",
        organization_id=test_context["other_org_id"],
    )
    response = test_context["client"].post(
        "/api/v1/prospects",
        headers=auth_headers,
        json={
            "company_name": "Wrong owner",
            "owner_user_id": str(other_user_id),
        },
    )
    assert response.status_code == 422


def test_company_name_is_required(test_context, auth_headers):
    response = test_context["client"].post(
        "/api/v1/prospects",
        headers=auth_headers,
        json={"company_name": "   "},
    )
    assert response.status_code == 422


def test_rich_business_fields_validation_and_normalization(test_context, auth_headers):
    response = test_context["client"].post(
        "/api/v1/prospects",
        headers=auth_headers,
        json={
            "company_name": "Entreprise Lot 2",
            "contact_first_name": "  Marie ",
            "contact_last_name": "DUPONT",
            "job_title": "Gérante",
            "email": "  MARIE@EXAMPLE.COM ",
            "phone": "+33 3 20 00 00 00",
            "website": "example.com",
            "siren": "123456789",
            "siret": "12345678900012",
            "naf_code": "43.99a",
            "workforce": 12,
            "annual_revenue": "1250000.50",
            "priority": "HAUTE",
            "next_action": "Rappeler après envoi du devis",
            "next_action_at": "2026-08-01T09:30:00+02:00",
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["contact_first_name"] == "Marie"
    assert item["email"] == "MARIE@example.com"
    assert item["website"] == "https://example.com"
    assert item["naf_code"] == "43.99A"
    assert item["priority"] == "haute"
    assert item["workforce"] == 12
    assert item["annual_revenue"] == "1250000.50"


def test_invalid_business_fields_are_rejected(test_context, auth_headers):
    invalid_payloads = [
        {"company_name": "A", "email": "pas-un-email"},
        {"company_name": "A", "phone": "ABC"},
        {"company_name": "A", "siren": "123"},
        {"company_name": "A", "siret": "123456789"},
        {"company_name": "A", "naf_code": "4399A"},
        {"company_name": "A", "priority": "critique"},
        {"company_name": "A", "workforce": -1},
        {"company_name": "A", "annual_revenue": -1},
    ]
    for payload in invalid_payloads:
        response = test_context["client"].post(
            "/api/v1/prospects", headers=auth_headers, json=payload
        )
        assert response.status_code == 422, (payload, response.text)


def test_filters_sorting_pagination_and_total_headers(test_context, auth_headers):
    client = test_context["client"]
    data = [
        {
            "company_name": "Zulu BTP",
            "city": "Lille",
            "naf_code": "43.99A",
            "priority": "haute",
            "source": "Salon",
        },
        {
            "company_name": "Alpha Conseil",
            "city": "Roubaix",
            "naf_code": "70.22Z",
            "priority": "basse",
            "source": "Web",
        },
        {
            "company_name": "Beta Formation",
            "city": "Lille",
            "naf_code": "85.59A",
            "priority": "haute",
            "source": "Salon",
        },
    ]
    for payload in data:
        created = client.post("/api/v1/prospects", headers=auth_headers, json=payload)
        assert created.status_code == 201, created.text

    filtered = client.get(
        "/api/v1/prospects?city=Lille&priority=haute&source=Salon"
        "&sort_by=company_name&sort_direction=asc&limit=1&offset=0",
        headers=auth_headers,
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.headers["x-total-count"] == "2"
    assert filtered.headers["x-limit"] == "1"
    assert filtered.headers["x-offset"] == "0"
    assert [item["company_name"] for item in filtered.json()] == ["Beta Formation"]

    second_page = client.get(
        "/api/v1/prospects?city=Lille&priority=haute&source=Salon"
        "&sort_by=company_name&sort_direction=asc&limit=1&offset=1",
        headers=auth_headers,
    )
    assert [item["company_name"] for item in second_page.json()] == ["Zulu BTP"]

    naf_search = client.get(
        "/api/v1/prospects?search=70.22Z",
        headers=auth_headers,
    )
    assert [item["company_name"] for item in naf_search.json()] == ["Alpha Conseil"]


def test_delete_endpoint_soft_archives_and_restore_still_works(test_context, auth_headers):
    client = test_context["client"]
    created = client.post(
        "/api/v1/prospects",
        headers=auth_headers,
        json={"company_name": "À archiver"},
    ).json()

    deleted = client.delete(f"/api/v1/prospects/{created['id']}", headers=auth_headers)
    assert deleted.status_code == 204
    assert client.get("/api/v1/prospects", headers=auth_headers).json() == []

    archived = client.get(
        "/api/v1/prospects?include_archived=true", headers=auth_headers
    ).json()
    assert archived[0]["status"] == "archived"

    restored = client.post(
        f"/api/v1/prospects/{created['id']}/restore", headers=auth_headers
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_update_decimal_and_datetime_are_auditable(test_context, auth_headers):
    client = test_context["client"]
    created = client.post(
        "/api/v1/prospects",
        headers=auth_headers,
        json={"company_name": "Audit prospect"},
    ).json()
    updated = client.patch(
        f"/api/v1/prospects/{created['id']}",
        headers=auth_headers,
        json={
            "annual_revenue": "99999.99",
            "next_action_at": "2026-09-01T10:00:00Z",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["annual_revenue"] == "99999.99"
