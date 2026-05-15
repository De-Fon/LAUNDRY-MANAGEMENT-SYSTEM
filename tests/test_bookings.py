from fastapi import status

def test_fetch_my_bookings(client, student_token_headers):
    response = client.get("/bookings/me", headers=student_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_create_booking_unauthenticated(client):
    response = client.post("/bookings", json={"pickup_at": "2030-01-01T12:00:00Z", "pickup_address": "Test", "items": []})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
