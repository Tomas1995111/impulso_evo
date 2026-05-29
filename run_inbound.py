"""Servidor inbound para recibir webhooks de Evolution (MESSAGES_UPSERT)."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "flows.inbound.inbound:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
