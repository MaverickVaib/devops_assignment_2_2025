from aceest_fitness.app import create_app

def test_add_list_summary():
    app = create_app()
    c = app.test_client()

    # add one workout
    r = c.post("/api/workouts",
               data=b'{"workout":"Jog","duration":15}',
               content_type="application/json")
    assert r.status_code == 201, r.get_data(as_text=True)

    # list should include it
    r2 = c.get("/api/workouts")
    assert r2.status_code == 200
    arr = r2.get_json()
    assert any(w.get("workout") == "Jog" for w in arr)

    # summary should reflect minutes
    r3 = c.get("/api/workouts/summary")
    assert r3.status_code == 200
    assert r3.get_json()["total_minutes"] >= 15
