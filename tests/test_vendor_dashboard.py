from fastapi import status

def test_fetch_dashboard(client, vendor_token_headers):
    # This might return 404 since the profile hasn't been set up
    response = client.get("/vendor/dashboard", headers=vendor_token_headers)
    assert response.status_code in {status.HTTP_200_OK, status.HTTP_404_NOT_FOUND}

def test_setup_profile_unauthenticated(client):
    response = client.post("/vendor/profile", json={"business_name": "Laundry Co", "business_address": "Test", "contact_phone": "0700000000", "max_orders_per_day": 10})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
