from fastapi import status

def test_fetch_my_orders(client, student_token_headers):
    response = client.get("/orders/my", headers=student_token_headers)
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)

def test_place_order_unauthenticated(client):
    response = client.post("/orders/", json={"vendor_id": 1, "service_item_id": 1, "wash_type": "Normal", "quantity": 1})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
