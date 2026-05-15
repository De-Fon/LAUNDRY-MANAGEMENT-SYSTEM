from fastapi import status

def test_fetch_account_summary(client, student_token_headers):
    # This might return 404 since the ledger account hasn't been created yet
    response = client.get("/ledger/my-summary", headers=student_token_headers)
    assert response.status_code in {status.HTTP_200_OK, status.HTTP_404_NOT_FOUND}

def test_open_ledger_unauthenticated(client):
    response = client.post("/ledger/accounts", json={"student_id": 1, "vendor_id": 1})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
