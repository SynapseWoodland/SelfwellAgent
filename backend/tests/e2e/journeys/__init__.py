"""E2E Phase 4 · 批次 5：6 类旅程全通。

Phase 4 批次 5 引入的 e2e_journey_* 测试套件，按行程划分到独立文件。
purpose: 用 httpx.AsyncClient 驱动真实 uvicorn（http://127.0.0.1:8001），
不依赖 in-process engine，避免 Windows reload 致命错误。
"""
