def test_health_is_public(test_context):
    response = test_context["client"].get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Request-ID"]


def test_readiness_checks_database(test_context):
    response = test_context["client"].get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

