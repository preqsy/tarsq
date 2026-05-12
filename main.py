class WorkerSettings:
    app: str = "mock_tasks"
    workers: int = 3
    timeout: int = 300
    ctx: dict = {"crud_currency": "get_crud_currency"}
    on_startup = None
    on_shutdown = None
