# -*- coding: utf-8 -*-
"""
sections 包：主区域六个功能 Section 的页面逻辑（固定顺序，不用 tab 导航）。
  ① nl_bookkeeping   自然语言记账
  ② receipt_ocr      小票 OCR 上传
  ③ transaction_list 流水列表
  ④ charts_section   消费图表
  ⑤ nl_query         自然语言查账
  ⑥ budget           预算预警（banner + 预算设置）
每个 Section 只组合 components 与 api 层，不写后端/数据库/LLM 业务逻辑。
"""
