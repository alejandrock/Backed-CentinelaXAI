def _login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def test_soc_cannot_list_users(client):
    _login(client, "soc@centinelax.ai", "Strong!Soc12345")
    response = client.get("/api/v1/users")
    assert response.status_code == 403
    assert response.get_json()["status"] == "FORBIDDEN"


def test_admin_can_list_users(client):
    _login(client, "admin@centinelax.ai", "Strong!Admin123")
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    assert response.get_json()["data"]["total"] == 2
