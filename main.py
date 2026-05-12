def on_startup(ctx):
    ctx["crud_currency"] = "get_crud_currency"


class WorkerSettings:
    # app: str = "mock_tasks"
    ctx: dict = {"crud_currency": "get_crud_currency"}
    on_startup = on_startup
    on_shutdown = None
    # workers: int = 5
