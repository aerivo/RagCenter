import uvicorn
from fastapi import FastAPI

if __package__:
    from .api.router import api_v1_router
    from .log.log import RequestLoggingMiddleware, configure_logging
else:
    from api.router import api_v1_router
    from log.log import RequestLoggingMiddleware, configure_logging

configure_logging()
app = FastAPI(title="RagCenter")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(api_v1_router)


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False)


if __name__ == "__main__":
    main()
