"""预算接口回归测试。"""

from decimal import Decimal

import pytest

from app.core.exceptions import AppException
from app.modules.budget.models import Budget
from app.modules.budget.repository import BudgetRepository
from app.modules.budget.service import BudgetService

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
    """首次设置预算后，查询应返回同样的金额和正常状态。"""
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
    """同一月份重复设置应更新金额，而不是新增一条记录。"""
    set_budget(client, "2026-11", "1000.00")
    response = set_budget(client, "2026-11", "1200.00")
    assert response.status_code == 200
    assert response.json()["amount"] == "1200.00"


def test_unset_month_returns_404(client):
    """未设置预算的月份返回 404，前端据此提示去设置。"""
    response = client.get(f"{BASE}/budgets/2099-01")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "该月未设置预算"


@pytest.mark.parametrize(
    "month",
    ["2026-13", "2026-00", "2026-1", "abc", "0000-01", "3000-01"],
)
def test_invalid_month_returns_422(client, month):
    """月份必须是补零的 YYYY-MM。"""
    assert set_budget(client, month, "100.00").status_code == 422


@pytest.mark.parametrize("amount", ["0", "-1", "1.234"])
def test_invalid_amount_returns_422(client, amount):
    """预算金额必须大于 0，且最多两位小数。"""
    assert set_budget(client, "2026-11", amount).status_code == 422


def test_year_zero_returns_422_without_dirty_row(client, db_session):
    """0000 年由路径正则拦截，返回 422，且不能写入任何预算记录。"""
    assert set_budget(client, "0000-01", "100.00").status_code == 422
    assert client.get(f"{BASE}/budgets/0000-01").status_code == 422
    assert db_session.query(Budget).count() == 0


@pytest.mark.parametrize("month", ["0000-01", "2026-1", "2026-13"])
def test_service_rejects_invalid_month_before_write(db_session, month):
    """即使绕过路由直接调用 service，也应在写库前失败。"""
    service = BudgetService(BudgetRepository(db_session), db_session)
    with pytest.raises(AppException):
        service.set_budget(month, Decimal("100.00"))
    assert db_session.query(Budget).count() == 0


def test_delete_budget(client):
    """已设置的预算可以取消，取消后查询返回 404。"""
    assert set_budget(client, "2026-11", "1000.00").status_code == 200
    assert client.delete(f"{BASE}/budgets/2026-11").status_code == 204
    assert client.get(f"{BASE}/budgets/2026-11").status_code == 404


def test_delete_unset_month_returns_404(client):
    """取消未设置的预算返回 404。"""
    assert client.delete(f"{BASE}/budgets/2099-02").status_code == 404


def test_delete_invalid_month_returns_422(client):
    """非法月份在路径校验阶段就被拦截。"""
    assert client.delete(f"{BASE}/budgets/0000-01").status_code == 422


def test_concurrent_first_insert_falls_back_to_update(
    db_session_factory, monkeypatch
):
    """模拟并发首次写入：读不到记录时插入冲突，应回滚后改为更新。"""
    month = "2026-07"

    # 模拟另一个请求已经抢先写入
    other = db_session_factory()
    other.add(Budget(month=month, amount=Decimal("100.00")))
    other.commit()
    other.close()

    session = db_session_factory()
    repo = BudgetRepository(session)
    original_get = repo.get
    calls = {"count": 0}

    def fake_get(target_month):
        calls["count"] += 1
        if calls["count"] == 1:
            return None  # 模拟并发时还没读到对方写入的记录
        return original_get(target_month)

    monkeypatch.setattr(repo, "get", fake_get)
    service = BudgetService(repo, session)

    result = service.set_budget(month, Decimal("200.00"))

    assert result.amount == Decimal("200.00")
    assert session.query(Budget).count() == 1
    session.close()


def test_extra_field_rejected(client):
    """严格模式：未定义字段不能被静默忽略。"""
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
    """验证 80% 预警和 100% 超支的分界。"""
    add_expense(client, "100.00", "2026-11-15T12:00:00")
    body = set_budget(client, "2026-11", budget).json()
    assert body["spent"] == "100.00"
    assert body["status"] == expected_status


def test_decimal_sum_without_float_error(client):
    """0.10 + 0.20 必须得到 0.30，不能出现浮点尾差。"""
    add_expense(client, "0.10", "2026-11-10T08:00:00")
    add_expense(client, "0.20", "2026-11-10T09:00:00")
    body = set_budget(client, "2026-11", "1.00").json()
    assert body["spent"] == "0.30"
    assert body["remaining"] == "0.70"


def test_month_boundary(client):
    """月末 23:59:59 计入当月，次日 00:00 计入下月。"""
    add_expense(client, "10.00", "2026-11-30T23:59:59")
    add_expense(client, "20.00", "2026-12-01T00:00:00")

    november = set_budget(client, "2026-11", "100.00").json()
    december = set_budget(client, "2026-12", "100.00").json()
    assert november["spent"] == "10.00"
    assert december["spent"] == "20.00"
