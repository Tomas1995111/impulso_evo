"""Entry point del CRM diario (ejecuta process_crm() cada día a las 9 AM)."""
from apscheduler.schedulers.blocking import BlockingScheduler
from flows.crm.crm_worker import process_crm

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="America/Argentina/Buenos_Aires")
    scheduler.add_job(process_crm, "cron", hour=9, minute=0)
    print("⏰ CRM Worker programado: se ejecutará cada día a las 09:00 ART.")
    scheduler.start()
