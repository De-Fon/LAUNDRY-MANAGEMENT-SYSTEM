from fastapi import status

def test_login_missing_fields(client):
    response = client.post("/auth/login", json={"email": "wrong@example.com"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_login_wrong_credentials(client):
    response = client.post("/auth/login", json={"email": "wrong@example.com", "password": "wrongpassword"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user(client, student_token_headers):
    response = client.get("/auth/me", headers=student_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["email"] == "student@test.com"
