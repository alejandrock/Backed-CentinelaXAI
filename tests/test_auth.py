def test_login_and_me(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@centinelax.ai", "password": "Strong!Admin123"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["user"]["email"] == "admin@centinelax.ai"

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.get_json()["data"]
    assert body["email"] == "admin@centinelax.ai"
    assert "*" in body["permissions"]


def test_invalid_login_is_rejected(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@centinelax.ai", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.get_json()["status"] == "UNAUTHORIZED"
