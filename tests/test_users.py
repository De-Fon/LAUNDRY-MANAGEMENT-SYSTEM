from fastapi import status

def test_fetch_users_as_admin(client, admin_token_headers):
    response = client.get("/users/", headers=admin_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_fetch_users_as_student_fails(client, student_token_headers):
    response = client.get("/users/", headers=student_token_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
