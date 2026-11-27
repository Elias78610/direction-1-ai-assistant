import os
from dotenv import load_dotenv

# 从同目录 .env 读取本地配置；.env 已在 .gitignore 中，不要提交
load_dotenv(override=True)

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "bill"),
    "charset": "utf8mb4",
}
