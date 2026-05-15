from fastapi import status

def test_fetch_my_entries(client, student_token_headers):
    response = client.get("/waitlist/me", headers=student_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_join_waitlist_unauthenticated(client):
    response = client.post("/waitlist", json={"service_item_id": 1, "note": "Test note"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
