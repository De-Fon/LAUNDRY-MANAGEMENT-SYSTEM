from fastapi import status

def test_fetch_my_notifications(client, student_token_headers):
    response = client.get("/notifications/me", headers=student_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_create_notification_unauthenticated(client):
    response = client.post("/notifications", json={"user_id": 1, "channel": "in_app", "subject": "Test", "message": "Test message"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
