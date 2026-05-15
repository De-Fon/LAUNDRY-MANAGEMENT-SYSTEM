from fastapi import status

def test_fetch_student_tabs(client, student_token_headers):
    response = client.get("/credit/my", headers=student_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_fetch_vendor_tabs(client, vendor_token_headers):
    response = client.get("/credit/vendor/all", headers=vendor_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
