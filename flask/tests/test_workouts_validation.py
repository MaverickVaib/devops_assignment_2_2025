from aceest_fitness.app import create_app

def test_reject_empty_workout():
    app = create_app()
    c = app.test_client()
    r = c.post("/api/workouts",
               data=b'{"workout":"","duration":10}',
               content_type="application/json")
    assert r.status_code == 400, r.get_data(as_text=True)

def test_reject_non_positive_duration():
    app = create_app()
    c = app.test_client()
    r = c.post("/api/workouts",
               data=b'{"workout":"Plank","duration":0}',
               content_type="application/json")
    assert r.status_code == 400, r.get_data(as_text=True)
