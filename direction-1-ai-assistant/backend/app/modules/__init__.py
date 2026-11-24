"""集中导入所有 ORM 模型，确保 Base.metadata 能注册到全部表。

新增模型时，在这里补充 import，main.py 中的 create_all 才会建表。
"""

from app.modules.expense.models import Expense

__all__ = ["Expense"]
