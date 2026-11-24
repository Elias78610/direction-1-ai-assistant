"""账目接口回归测试：锁住近期修复的行为。"""

BASE = "/api/v1"


def expense_payload(**overrides):
    payload = {
        "amount": "10.00",
        "category": "餐饮",
        "spent_at": "2026-11-24T12:00:00",
    }
    payload.update(overrides)
    return payload


def test_unknown_field_returns_422(client):
    """严格模式：未定义字段不能被静默忽略。"""
    response = client.post(
        f"{BASE}/expenses",
        json=expense_payload(amount_cents=1000),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(error["field"] == "body.amount_cents" for error in body["errors"])


def test_timezone_rejected(client):
    """带时区的时间统一拒绝，避免比较时报错或时区被丢弃。"""
    response = client.post(
        f"{BASE}/expenses",
        json=expense_payload(spent_at="2026-11-24T12:00:00+08:00"),
    )
    assert response.status_code == 422

    response = client.get(
        f"{BASE}/expenses",
        params={"start": "2026-11-01T00:00:00+08:00"},
    )
    assert response.status_code == 422


def test_end_date_includes_whole_day(client):
    """end 传日期时包含当天，而不是只到 00:00。"""
    created = client.post(
        f"{BASE}/expenses",
        json=expense_payload(spent_at="2026-11-30T18:00:00"),
    )
    assert created.status_code == 201

    response = client.get(f"{BASE}/expenses", params={"end": "2026-11-30"})
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_not_found_response_structure(client):
    """404 使用统一错误结构，并带请求 ID。"""
    response = client.get(f"{BASE}/expenses/999")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "账目不存在"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_put_missing_id_returns_404_before_empty_body(client):
    """修改不存在的账目时，即使请求体为空也返回 404。"""
    response = client.put(f"{BASE}/expenses/999", json={})
    assert response.status_code == 404


def test_put_existing_with_empty_body_returns_400(client):
    """账目存在但没有任何修改字段时返回 400。"""
    created = client.post(f"{BASE}/expenses", json=expense_payload()).json()
    response = client.put(f"{BASE}/expenses/{created['id']}", json={})
    assert response.status_code == 400


def test_source_must_match_source_fields(client):
    """ocr 必须带 image_path，nlp 必须带 raw_text。"""
    assert client.post(
        f"{BASE}/expenses", json=expense_payload(source="ocr")
    ).status_code == 422
    assert client.post(
        f"{BASE}/expenses", json=expense_payload(source="nlp")
    ).status_code == 422
    assert client.post(
        f"{BASE}/expenses",
        json=expense_payload(source="ocr", image_path="data/uploads/a.jpg"),
    ).status_code == 201


def test_source_not_changeable_on_update(client):
    """来源在创建时确定，修改接口不接受 source。"""
    created = client.post(f"{BASE}/expenses", json=expense_payload()).json()
    response = client.put(
        f"{BASE}/expenses/{created['id']}", json={"source": "ocr"}
    )
    assert response.status_code == 422
