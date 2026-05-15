from fastapi import status

def test_fetch_my_payments(client, student_token_headers):
    response = client.get("/payments/me", headers=student_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_create_payment_unauthenticated(client):
    response = client.post("/payments", json={"order_id": 1, "amount": 100.0, "payment_method": "mpesa", "transaction_ref": "REF", "idempotency_key": "key1"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
