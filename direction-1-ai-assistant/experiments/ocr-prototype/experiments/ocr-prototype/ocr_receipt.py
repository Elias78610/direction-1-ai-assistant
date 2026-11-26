# -*- coding: utf-8 -*-
"""
小票 OCR -> JSON -> MySQL 全流程
用法：
    python ocr_receipt.py                 # 默认识别项目目录下的 receipt.jpg
    python ocr_receipt.py 其他小票.jpg     # 指定图片路径
"""
import os
import re
import sys
import json
import pymysql

from storage import DB_CONFIG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_IMG = os.path.join(BASE_DIR, "receipt.jpg")
JSON_FILE = os.path.join(BASE_DIR, "receipt.json")


# ---------------------- 1. OCR 识别 ----------------------
def ocr_image(img_path):
    """用 PaddleOCR 识别图片，返回文本行列表"""
    from paddleocr import PaddleOCR

    # enable_mkldnn=False：规避 CPU 上 oneDNN 与 PIR 的兼容报错
    ocr = PaddleOCR(lang="ch", enable_mkldnn=False)
    result = ocr.predict(img_path)

    lines = []
    for res in (result or []):
        # paddleocr 3.x：结果里 rec_texts 就是识别出的文本行
        if isinstance(res, dict):
            texts = res.get("rec_texts")
        else:
            texts = getattr(res, "rec_texts", None)
        if texts:
            for text in texts:
                text = str(text).strip()
                if text:
                    lines.append(text)
    return lines



def _find(pattern, lines, group=1, flags=re.I):
    for line in lines:
        m = re.search(pattern, line, flags)
        if m:
            return m.group(group).strip()
    return None


def _to_float(s):
    if s is None:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(s))
    return float(m.group()) if m else None


def parse_receipt(lines):
    receipt = {
        "store": None,
        "branch": None,
        "cashier": None,
        "order_no": None,
        "time": None,
        "items": [],
        "total": None,
        "discount": None,
        "payable": None,
        "paid": None,
        "payment_method": None,
        "raw_lines": lines,
    }

    consumed = [False] * len(lines)

    def value_at(i):
        """取冒号后同栏位的值；为空则取下一非空行"""
        parts = re.split(r"[:：]", lines[i], maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            return parts[1].strip(), i
        if i + 1 < len(lines):
            return lines[i + 1].strip(), i + 1
        return None, i


    rules = [
        ("branch", r"门店[:：]", "text"),
        ("cashier", r"收银员[:：]", "text"),
        ("order_no", r"单号[:：]", "text"),
        ("payment_method", r"支付方式[:：]", "text"),
        ("total", r"商品合计[:：]", "money"),
        ("discount", r"优惠金额[:：]", "money"),
        ("payable", r"应付金额[:：]", "money"),
        ("paid", r"实付金额[:：]", "money"),
    ]
    for i, line in enumerate(lines):
        for field, pattern, kind in rules:
            if re.search(pattern, line):
                val, vi = value_at(i)
                consumed[i] = True
                if vi != i:
                    consumed[vi] = True
                if kind == "money":
                    receipt[field] = _to_float(val)
                else:
                    receipt[field] = val
                break

    # 时间单独匹配（日期时间格式）
    for i, line in enumerate(lines):
        m = re.search(r"时间[:：]\s*(\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2})", line)
        if m:
            receipt["time"] = m.group(1)
            consumed[i] = True
            break

    # 门店名称：第一条含 超市/商店/便利店/商场 的行
    for line in lines:
        if re.search(r"超市|商店|便利店|商场", line):
            receipt["store"] = line
            break

    # 商品明细：OCR 常把“名称 / ×数量 / 金额”拆成多行，按当前名称归组
    qty_re = re.compile(r"^[×xX]\s*(\d+)$")
    price_re = re.compile(r"^-?\d+(?:\.\d+)?$")
    current = None
    for i, line in enumerate(lines):
        if consumed[i]:
            continue
        s = line.strip()
        if not s or re.search(r"欢迎|光临", s):
            continue
        if re.search(r"超市|商店|便利店|商场", s):
            continue
        mq = qty_re.match(s)
        mp = price_re.match(s)
        if mq:
            if current is not None:
                current["quantity"] = int(mq.group(1))
        elif mp:
            if current is not None:
                current["price"] = float(mp.group())
        else:
            current = {"name": s, "quantity": None, "price": None}
            receipt["items"].append(current)

    return receipt


def save_json(receipt, filename=JSON_FILE):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)
    return filename



def save_to_mysql(receipt):
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()


    cur.execute("""
        CREATE TABLE IF NOT EXISTS expense (
            id INT AUTO_INCREMENT PRIMARY KEY,
            price VARCHAR(100) NOT NULL,
            time VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            merchant VARCHAR(100),
            meal VARCHAR(50)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)


    cur.execute("""
        CREATE TABLE IF NOT EXISTS receipt_item (
            id INT AUTO_INCREMENT PRIMARY KEY,
            expense_id INT,
            name VARCHAR(200),
            quantity INT,
            price DECIMAL(10,2)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    merchant = receipt["store"] or ""
    if receipt["branch"]:
        merchant = f"{merchant}{receipt['branch']}"


    cur.execute(
        """
        INSERT INTO expense (price, time, category, merchant, meal)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            str(receipt["paid"]) if receipt["paid"] is not None else "0",
            receipt["time"] or "",
            "购物",
            merchant or None,
            None,
        ),
    )
    expense_id = cur.lastrowid


    for item in receipt["items"]:
        cur.execute(
            """
            INSERT INTO receipt_item (expense_id, name, quantity, price)
            VALUES (%s, %s, %s, %s)
            """,
            (expense_id, item["name"], item["quantity"], item["price"]),
        )

    conn.commit()
    cur.close()
    conn.close()
    return {"expense_id": expense_id, "item_count": len(receipt["items"])}



if __name__ == "__main__":
    img_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMG
    if not os.path.exists(img_path):
        print(f"找不到图片：{img_path}")
        sys.exit(1)

    print("正在 OCR 识别（首次运行会下载识别模型，请稍候）...")
    ocr_lines = ocr_image(img_path)

    receipt = parse_receipt(ocr_lines)

    json_path = save_json(receipt)
    print(f"\n===== 识别结果 JSON（已保存到 {json_path}）=====")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))

    result = save_to_mysql(receipt)
    print(f"\n已写入 MySQL：账单 id={result['expense_id']}，商品 {result['item_count']} 条")
