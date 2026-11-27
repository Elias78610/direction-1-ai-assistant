import json
import pymysql

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123",
    "database": "bill",
    "charset": "utf8mb4",
}

OUTPUT_FILE = "bills.json"


def fetch_all_bills():

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, price, time, category, merchant, meal FROM expense ORDER BY id"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    bills = []
    for r in rows:
        bills.append({
            "id": r[0],
            "price": r[1],
            "time": r[2],
            "category": r[3],
            "merchant": r[4],
            "meal": r[5],
        })
    return bills


def export_to_json(bills, filename=OUTPUT_FILE):

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(bills, f, ensure_ascii=False, indent=2)
    return filename


if __name__ == "__main__":
    bills = fetch_all_bills()


    print(json.dumps(bills, ensure_ascii=False, indent=2))


    path = export_to_json(bills)
    print(f"\n已导出到：{path}（共 {len(bills)} 条）")
