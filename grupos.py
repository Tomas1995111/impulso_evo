import requests

URL_GRUPOS = "http://localhost:8080/group/fetchAllGroups/Impulso?getParticipants=false"
HEADERS = {"apikey": "Impulso2025!"}

try:
    res = requests.get(URL_GRUPOS, headers=HEADERS)
    if res.status_code == 200:
        grupos = res.json()
        print(f"\n✅ Se encontraron {len(grupos)} grupos:\n")
        print(f"{'NOMBRE DEL GRUPO':<40} | {'ID (@g.us)':<30}")
        print("-" * 75)
        
        for g in grupos:
            # Dependiendo de la versión de Evolution, los campos pueden ser 'subject' o 'name'
            nombre = g.get("subject") or g.get("name") or "Sin Nombre"
            jid = g.get("id")
            print(f"{nombre:<40} | {jid:<30}")
    else:
        print(f"❌ Error {res.status_code}: {res.text}")
except Exception as e:
    print(f"❌ No se pudo conectar a la API: {e}")