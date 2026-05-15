from fastapi import status

def test_fetch_categories(client):
    response = client.get("/catalog/categories")
    assert response.status_code == status.HTTP_200_OK

def test_create_category_as_vendor(client, vendor_token_headers):
    response = client.post(
        "/catalog/categories",
        headers=vendor_token_headers,
        json={"name": "Dry Cleaning", "description": "Professional dry cleaning"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["name"] == "Dry Cleaning"

def test_create_category_as_student_fails(client, student_token_headers):
    response = client.post(
        "/catalog/categories",
        headers=student_token_headers,
        json={"name": "Dry Cleaning", "description": "Professional dry cleaning"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
