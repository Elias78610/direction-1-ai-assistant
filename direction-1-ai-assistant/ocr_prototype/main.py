from langchain_deepseek import ChatDeepSeek
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")

deepseek_llm = ChatDeepSeek(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model="deepseek-chat",
)

from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from pydantic import BaseModel, Field
import sqlite3
import re


class BillStruct(BaseModel):
    intent: str = Field(description="只能是 add_bill / query_bill")
    amount: Optional[float] = Field(default=None)
    category: Optional[str] = Field(default=None)
    bill_type: Optional[str] = Field(default=None)
    bill_date: Optional[str] = Field(default=None)
    remark: Optional[str] = Field(default=None)
    query_keyword: Optional[str] = Field(default=None)


class State(TypedDict):
    user_query: str
    bill_struct: Optional[BillStruct]
    retrieved: List[dict]
    result_json: dict



def parse_node(state: State) -> State:
    text = state["user_query"].lower()
    intent = "query_bill"
    amount = None
    category = None
    bill_type = None
    bill_date = None
    remark = state["user_query"]
    query_keyword = None

    # 判断记账意图
    if any(k in text for k in ["记", "花了", "付了", "赚了", "收入"]):
        intent = "add_bill"
        # 提取金额
        nums = re.findall(r"\d+\.?\d*", text)
        if nums:
            amount = float(nums[0])
        # 收支类型
        if "收入" in text or "赚" in text:
            bill_type = "收入"
        else:
            bill_type = "支出"
        # 分类
        if "餐饮" in text:
            category = "餐饮"
        elif "交通" in text:
            category = "交通"
        elif "购物" in text:
            category = "购物"
        else:
            category = "其他"
    else:
        intent = "query_bill"
        query_keyword = text

    bill_struct = BillStruct(
        intent=intent,
        amount=amount,
        category=category,
        bill_type=bill_type,
        bill_date=bill_date,
        remark=remark,
        query_keyword=query_keyword
    )
    return {"user_query": state["user_query"], "bill_struct": bill_struct}


# 路由
def route_parse(state: State):
    s = state["bill_struct"]
    if s.intent == "add_bill":
        return "add_bill"
    else:
        return "query_bill"


# 写入账单
def add_bill_node(state: State) -> State:
    s: BillStruct = state["bill_struct"]
    conn = sqlite3.connect("./bill.db")
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bill(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_date TEXT,
        category TEXT,
        bill_type TEXT,
        amount REAL,
        remark TEXT
    )
    """)
    cur.execute(
        "INSERT INTO bill(bill_date,category,bill_type,amount,remark) VALUES (?,?,?,?,?)",
        (s.bill_date, s.category, s.bill_type, s.amount, s.remark)
    )
    conn.commit()
    conn.close()
    res_json = {
        "code": 200,
        "msg": "记账成功",
        "data": s.model_dump()
    }
    return {"result_json": res_json}



def query_bill_node(state: State) -> State:
    conn = sqlite3.connect("./bill.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM bill")
    rows = cur.fetchall()
    conn.close()
    data_list = []
    for r in rows:
        data_list.append({
            "id": r[0],
            "bill_date": r[1],
            "category": r[2],
            "bill_type": r[3],
            "amount": r[4],
            "remark": r[5]
        })
    res_json = {
        "code": 200,
        "msg": "查询成功",
        "data": data_list
    }
    return {"result_json": res_json}


# 构建图
builder = StateGraph(State)
builder.add_node("parse", parse_node)
builder.add_node("add_bill", add_bill_node)
builder.add_node("query_bill", query_bill_node)

builder.set_entry_point("parse")
builder.add_conditional_edges("parse", route_parse, {
    "add_bill": "add_bill",
    "query_bill": "query_bill"
})
builder.add_edge("add_bill", END)
builder.add_edge("query_bill", END)

graph = builder.compile()


if __name__ == "__main__":

    test3 = "收入1020美元"
    # test3 = "记一笔餐饮花了45元"
    # test3 = "查一下所有账单"
    res = graph.invoke({"user_query": test3})
    import json
    print(json.dumps(res["result_json"], ensure_ascii=False, indent=2))






