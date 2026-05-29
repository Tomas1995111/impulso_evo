"""Ejecuta el CRM manualmente (fuera del horario programado de 9 AM)."""
from flows.crm.crm_worker import process_crm

if __name__ == "__main__":
    process_crm()
