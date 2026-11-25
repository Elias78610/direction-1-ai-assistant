"""预算接口回归测试。"""

import pytest

BASE = "/api/v1"


def add_expense(client, amount, spent_at, category="餐饮"):
    response = client.post(
        f"{BASE}/expenses",
        json={"amount": amount, "category": category, "spent_at": spent_at},
    )
    assert response.status_code == 201
    return response.json()


def set_budget(client, month, amount):
    return client.put(f"{BASE}/budgets/{month}", json={"amount": amount})


def test_set_and_get_budget(client):
    response = set_budget(client, "2026-11", "1000.00")
    assert response.status_code == 200
    body = response.json()
    assert body["month"] == "2026-11"
    assert body["amount"] == "1000.00"
    assert body["spent"] == "0.00"
    assert body["remaining"] == "1000.00"
    assert body["usage_percent"] == 0.0
    assert body["status"] == "normal"

    detail = client.get(f"{BASE}/budgets/2026-11")
    assert detail.status_code == 200
    assert detail.json()["amount"] == "1000.00"


def test_repeat_set_updates_same_month(client):
    set_budget(client, "2026-11", "1000.00")
    response = set_budget(client, "2026-11", "1200.00")
    assert response.status_code == 200
    assert response.json()["amount"] == "1200.00"


def test_unset_month_returns_404(client):
    response = client.get(f"{BASE}/budgets/2099-01")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "该月未设置预算"


@pytest.mark.parametrize("month", ["2026-13", "2026-00", "2026-1", "abc"])
def test_invalid_month_returns_422(client, month):
    assert set_budget(client, month, "100.00").status_code == 422


@pytest.mark.parametrize("amount", ["0", "-1", "1.234"])
def test_invalid_amount_returns_422(client, amount):
    assert set_budget(client, "2026-11", amount).status_code == 422


def test_extra_field_rejected(client):
    response = client.put(
        f"{BASE}/budgets/2026-11",
        json={"amount": "100.00", "total_budget_cents": 10000},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("budget", "expected_status"),
    [
        ("200.00", "normal"),    # 50%
        ("125.00", "warning"),   # 80%
        ("100.00", "warning"),   # 100%
        ("99.99", "exceeded"),   # 100.01%
    ],
)
def test_status_thresholds(client, budget, expected_status):
    add_expense(client, "100.00", "2026-11-15T12:00:00")
    body = set_budget(client, "2026-11", budget).json()
    assert body["spent"] == "100.00"
    assert body["status"] == expected_status


def test_decimal_sum_without_float_error(client):
    add_expense(client, "0.10", "2026-11-10T08:00:00")
    add_expense(client, "0.20", "2026-11-10T09:00:00")
    body = set_budget(client, "2026-11", "1.00").json()
    assert body["spent"] == "0.30"
    assert body["remaining"] == "0.70"


def test_month_boundary(client):
    add_expense(client, "10.00", "2026-11-30T23:59:59")
    add_expense(client, "20.00", "2026-12-01T00:00:00")

    november = set_budget(client, "2026-11", "100.00").json()
    december = set_budget(client, "2026-12", "100.00").json()
    assert november["spent"] == "10.00"
    assert december["spent"] == "20.00"
