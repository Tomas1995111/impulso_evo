"""Servidor inbound para recibir webhooks de Evolution (MESSAGES_UPSERT)."""

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler

from core import config
from flows.inbound.abandoned import check_abandoned_conversations as check_abandoned


def main() -> None:
    scheduler = BackgroundScheduler(timezone=config.TIMEZONE)
    scheduler.add_job(check_abandoned, "interval", minutes=15)
    scheduler.start()

    uvicorn.run(
        "flows.inbound.inbound:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
