from core.alerts import search_alert_condition

tickers_arg = [
    "GGAL.BA", "YPFD.BA", "BMA.BA", "BBAR.BA", "PAMP.BA",
    "TGSU2.BA", "TXAR.BA", "SUPV.BA", "COME.BA", "BYMA.BA",
    "CEPU.BA", "ALUA.BA", "TRAN.BA", "LOMA.BA", "EDN.BA",
    "VALO.BA", "METR.BA", "IRSA.BA", "TECO2.BA", "TGNO4.BA",
    "CRES.BA", "MIRG.BA", "BOLT.BA", "AUSO.BA", "SAMI.BA",
    "MOLI.BA", "RICH.BA", "LEDE.BA", "CVH.BA", "BPAT.BA",
    "DGCU2.BA", "BHIP.BA", "CELU.BA", "AGRO.BA", "PATA.BA",
    "CECO2.BA", "A3.BA", "GRIM.BA", "MORI.BA", "HARG.BA",
    "GBAN.BA", "CGPA2.BA",
]


def generar_alerta_aleatoria_arg():
    return search_alert_condition(tickers_arg)


if __name__ == "__main__":
    alerta = generar_alerta_aleatoria_arg()
    if alerta:
        print(alerta)
    else:
        print("No hay alertas en este momento.")
