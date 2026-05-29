from core.alerts import search_alert_condition

tickers_top = [
    'NOW', 'SHW', 'COST', 'AZO', 'SNPS', 'META', 'LMT', 'CAT', 'TMO', 'UNH',
    'DE', 'ADSK', 'IBM', 'JPM', 'AAPL', 'UNP', 'HD', 'BLK', 'PNC', 'FDX',
    'NSC', 'AMZN', 'BRK-B', 'TMUS', 'CRM', 'MAR', 'RSG', 'EXPE', 'AXP', 'QCOM',
    'LOW', 'GE', 'CVX', 'RL', 'VST', 'LIN', 'CMI', 'ACN', 'MCD', 'MSFT', 'DIS',
    'JNJ', 'AMGN', 'HON', 'PG', 'MMM', 'BA', 'NVDA', 'KO', 'V', 'WMT',
    'VZ', 'GS', 'NKE', 'CSCO', 'MRK', 'NFLX', 'ASML', 'REGN', 'KLAC', 'BKNG',
    'MELI', 'MDB', 'MSTR', 'ZS', 'AMD', 'AVGO', 'GILD', 'TXN', 'TSLA', 'GOOG',
    'ROST', 'TTWO', 'WDAY', 'PLTR', 'CEG', 'MU', 'LLY', 'MCK', 'GOOGL', 'TSM',
    'MA', 'ORCL', 'XOM', 'SAP', 'BAC', 'ABBV', 'SPY', 'QQQ', 'DIA', 'IWM',
    'VTI', 'VEA', 'VWO', 'TLT', 'GLD', 'XLF', 'XLE', 'XLV', 'XLK', 'XLY',
    'XLU', 'INTC', 'PEP', 'UPS', 'ADBE', 'MDT', 'PFE', 'BABA', 'SBUX', 'CSX',
]


def generar_alerta_aleatoria():
    return search_alert_condition(tickers_top)


if __name__ == "__main__":
    alerta = generar_alerta_aleatoria()
    if alerta:
        print(alerta)
    else:
        print("No hay alertas en este momento.")
