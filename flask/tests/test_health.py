from aceest_fitness.app import create_app

def test_health():
    app = create_app()
    c = app.test_client()
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "healthy"
