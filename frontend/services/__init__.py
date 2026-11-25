# -*- coding: utf-8 -*-
"""
services 包：前端与后端通信层。
api_client.py 是页面层与 FastAPI 之间的唯一通道（真实 HTTP 统一封装，
DEMO_MODE 开启时自动切换 demo_data.py 内置示例数据，见 config.py）。
"""
