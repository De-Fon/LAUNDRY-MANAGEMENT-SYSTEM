from fastapi import status

def test_fetch_wash_types(client):
    response = client.get("/pricing/wash-types")
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_add_wash_type_as_vendor(client, vendor_token_headers):
    response = client.post(
        "/pricing/wash-types",
        headers=vendor_token_headers,
        json={"name": "Express", "description": "Fast", "price_multiplier": 1.5, "duration_hours": 2}
    )
    assert response.status_code == status.HTTP_201_CREATED

def test_add_wash_type_as_student_fails(client, student_token_headers):
    response = client.post(
        "/pricing/wash-types",
        headers=student_token_headers,
        json={"name": "Express", "description": "Fast", "price_multiplier": 1.5, "duration_hours": 2}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
