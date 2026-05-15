from fastapi import status

def test_fetch_daily_report_as_vendor(client, vendor_token_headers):
    # This should return 200 or 404 (if vendor profile not found)
    # Analytics might depend on vendor dashboard profile existing
    response = client.get("/analytics/daily", headers=vendor_token_headers)
    assert response.status_code in {status.HTTP_200_OK, status.HTTP_404_NOT_FOUND}

def test_fetch_daily_report_unauthenticated(client):
    response = client.get("/analytics/daily")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
