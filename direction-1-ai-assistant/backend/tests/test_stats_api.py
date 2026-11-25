"""统计接口回归测试：金额口径、时间范围规则、补零与错误结构。"""

from datetime import datetime

from app.modules.stats import service as stats_service

BASE = "/api/v1/stats"


def add_expense(
    client,
    amount: str,
    category: str,
    spent_at: str,
    note: str | None = None,
) -> dict:
    payload = {"amount": amount, "category": category, "spent_at": spent_at}
    if note is not None:
        payload["note"] = note
    response = client.post("/api/v1/expenses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_summary_totals(client):
    """总览：金额、笔数、笔均（四舍五入到分）。"""
    add_expense(client, "10.00", "餐饮", "2026-11-01T12:00:00")
    add_expense(client, "20.50", "交通", "2026-11-02T08:00:00")
    add_expense(client, "98.00", "餐饮", "2026-11-28T19:30:00")

    response = client.get(
        f"{BASE}/summary",
        params={"start": "2026-11-01", "end": "2026-11-30"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["start"] == "2026-11-01T00:00:00"
    assert body["end"] == "2026-11-30T23:59:59"
    assert body["total_amount"] == "128.50"
    assert body["count"] == 3
    # 128.50 / 3 = 42.8333...
    assert body["avg_amount"] == "42.83"
    assert isinstance(body["total_amount"], str)
    assert isinstance(body["avg_amount"], str)


def test_summary_empty_range(client):
    """没有数据时返回 0 而不是 404。"""
    body = client.get(
        f"{BASE}/summary",
        params={"start": "2026-11-01", "end": "2026-11-30"},
    ).json()
    assert body["total_amount"] == "0.00"
    assert body["count"] == 0
    assert body["avg_amount"] == "0.00"


def test_summary_range_is_inclusive(client):
    """时间范围两端都包含；日期形态的 end 包含当天。"""
    add_expense(client, "10.00", "餐饮", "2026-10-31T23:59:59")
    add_expense(client, "20.00", "餐饮", "2026-11-30T23:59:59")
    add_expense(client, "40.00", "餐饮", "2026-12-01T00:00:00")

    body = client.get(
        f"{BASE}/summary",
        params={"start": "2026-11-01", "end": "2026-11-30"},
    ).json()
    assert body["total_amount"] == "20.00"
    assert body["count"] == 1


def test_default_range_is_current_month(client, monkeypatch):
    """都不传：本月 1 日 00:00:00 至当前时间。"""
    monkeypatch.setattr(
        stats_service, "_now", lambda: datetime(2026, 11, 25, 9, 0, 0)
    )
    add_expense(client, "10.00", "餐饮", "2026-10-31T20:00:00")
    add_expense(client, "20.00", "餐饮", "2026-11-01T00:00:00")
    add_expense(client, "30.00", "餐饮", "2026-11-25T09:00:00")

    body = client.get(f"{BASE}/summary").json()
    assert body["start"] == "2026-11-01T00:00:00"
    assert body["end"] == "2026-11-25T09:00:00"
    assert body["total_amount"] == "50.00"
    assert body["count"] == 2


def test_only_start_uses_now_as_end(client, monkeypatch):
    """只传 start：end 取当前时间。"""
    monkeypatch.setattr(
        stats_service, "_now", lambda: datetime(2026, 11, 25, 9, 0, 0)
    )
    add_expense(client, "10.00", "餐饮", "2026-11-20T12:00:00")

    body = client.get(
        f"{BASE}/summary", params={"start": "2026-11-10"}
    ).json()
    assert body["start"] == "2026-11-10T00:00:00"
    assert body["end"] == "2026-11-25T09:00:00"
    assert body["total_amount"] == "10.00"


def test_only_end_uses_month_begin_as_start(client):
    """只传 end：start 取 end 所在月 1 日 00:00:00。"""
    add_expense(client, "10.00", "餐饮", "2026-09-01T00:00:00")
    add_expense(client, "20.00", "餐饮", "2026-08-31T23:59:59")

    body = client.get(
        f"{BASE}/summary", params={"end": "2026-09-30"}
    ).json()
    assert body["start"] == "2026-09-01T00:00:00"
    assert body["end"] == "2026-09-30T23:59:59"
    assert body["total_amount"] == "10.00"
    assert body["count"] == 1


def test_start_after_end_returns_bad_request(client):
    """start 晚于 end：400 BAD_REQUEST，并带 request_id。"""
    response = client.get(
        f"{BASE}/summary",
        params={"start": "2026-11-30", "end": "2026-11-01"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "BAD_REQUEST"
    assert body["message"] == "开始时间不能晚于结束时间"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_timezone_aware_param_rejected(client):
    """统计接口的时间参数同样不接受时区。"""
    response = client.get(
        f"{BASE}/summary",
        params={"start": "2026-11-01T00:00:00+08:00"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_categories_amount_count_ratio(client):
    """分类统计：金额、笔数、占比（四位小数）与金额降序。"""
    for _ in range(5):
        add_expense(client, "16.00", "餐饮", "2026-11-10T12:00:00")
    for _ in range(5):
        add_expense(client, "7.00", "交通", "2026-11-11T08:00:00")
    for _ in range(2):
        add_expense(client, "6.75", "交通", "2026-11-12T18:00:00")

    body = client.get(
        f"{BASE}/categories",
        params={"start": "2026-11-01", "end": "2026-11-30"},
    ).json()
    assert body["total_amount"] == "128.50"
    assert [item["category"] for item in body["items"]] == ["餐饮", "交通"]

    dining, transport = body["items"]
    assert dining["amount"] == "80.00"
    assert dining["count"] == 5
    assert dining["ratio"] == 0.6226
    assert transport["amount"] == "48.50"
    assert transport["count"] == 7
    assert transport["ratio"] == 0.3774


def test_categories_empty_range(client):
    """空范围返回空列表，不返回 0 金额的分类。"""
    body = client.get(
        f"{BASE}/categories",
        params={"start": "2026-11-01", "end": "2026-11-30"},
    ).json()
    assert body["total_amount"] == "0.00"
    assert body["items"] == []


def test_trend_day_zero_filled(client):
    """按天趋势：缺失日期补 0，方便前端直接连折线。"""
    add_expense(client, "10.00", "餐饮", "2026-11-01T12:00:00")
    add_expense(client, "20.00", "餐饮", "2026-11-01T19:00:00")
    add_expense(client, "5.00", "交通", "2026-11-03T09:00:00")

    body = client.get(
        f"{BASE}/trend",
        params={
            "start": "2026-11-01",
            "end": "2026-11-03",
            "granularity": "day",
        },
    ).json()
    assert body["granularity"] == "day"
    assert [point["period"] for point in body["points"]] == [
        "2026-11-01",
        "2026-11-02",
        "2026-11-03",
    ]
    assert [point["amount"] for point in body["points"]] == ["30.00", "0.00", "5.00"]
    assert [point["count"] for point in body["points"]] == [2, 0, 1]


def test_trend_month_zero_filled(client):
    """按月趋势：跨月聚合且缺失月份补 0。"""
    add_expense(client, "12.00", "餐饮", "2026-05-10T12:00:00")
    add_expense(client, "8.00", "交通", "2026-05-20T08:00:00")
    add_expense(client, "9.50", "购物", "2026-07-02T15:00:00")

    body = client.get(
        f"{BASE}/trend",
        params={
            "start": "2026-05-01",
            "end": "2026-07-31",
            "granularity": "month",
        },
    ).json()
    assert [point["period"] for point in body["points"]] == [
        "2026-05",
        "2026-06",
        "2026-07",
    ]
    assert [point["amount"] for point in body["points"]] == [
        "20.00",
        "0.00",
        "9.50",
    ]
    assert [point["count"] for point in body["points"]] == [2, 0, 1]


def test_trend_month_partial_range_filters_days(client):
    """跨月区间只统计落在区间内的日期。"""
    add_expense(client, "1.00", "餐饮", "2026-05-01T12:00:00")
    add_expense(client, "5.00", "餐饮", "2026-05-15T12:00:00")

    body = client.get(
        f"{BASE}/trend",
        params={
            "start": "2026-05-10",
            "end": "2026-05-31",
            "granularity": "month",
        },
    ).json()
    assert body["points"] == [
        {"period": "2026-05", "amount": "5.00", "count": 1}
    ]


def test_trend_invalid_granularity(client):
    """granularity 只接受 day / month。"""
    response = client.get(
        f"{BASE}/trend",
        params={"start": "2026-11-01", "end": "2026-11-30", "granularity": "week"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(
        error["field"] == "query.granularity" for error in body["errors"]
    )


def test_trend_day_range_too_large(client):
    """按天最多一年，超出提示改用月粒度。"""
    response = client.get(
        f"{BASE}/trend",
        params={
            "start": "2024-01-01",
            "end": "2025-12-31",
            "granularity": "day",
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "BAD_REQUEST"
