import hashlib
import hmac
import json
import sys
from datetime import datetime

import requests

URL_RECEPTOR = "http://127.0.0.1:5000/webhook/pedido-pago"
SEGREDO = "segredo-compartilhado-123"  # mesmo segredo do receptor


def gerar_evento_pedido_pago() -> dict:
   
    return {
        "evento": "pedido.pago",
        "pedido_id": 1042,
        "cliente": {"nome": "Maria Souza", "email": "maria@email.com"},
        "itens": [
            {"sku": "TEN-001", "descricao": "Tênis de corrida", "quantidade": 1},
            {"sku": "MEI-010", "descricao": "Par de meias", "quantidade": 2},
        ],
        "valor_total": 389.80,
        "data_pagamento": datetime.now().isoformat(timespec="seconds"),
    }


def enviar_webhook(evento: dict) -> None:
    corpo = json.dumps(evento, ensure_ascii=False).encode("utf-8")
    assinatura = hmac.new(SEGREDO.encode(), corpo, hashlib.sha256).hexdigest()
    headers = {"Content-Type": "application/json", "X-Assinatura": assinatura}

    print("[EMISSOR] Enviando evento para", URL_RECEPTOR)
    print(json.dumps(evento, indent=2, ensure_ascii=False))

    try:
        resp = requests.post(URL_RECEPTOR, data=corpo, headers=headers, timeout=5)
    except requests.exceptions.RequestException as e:
        print(f"[EMISSOR] Falha de conexão com o receptor: {e}")
        sys.exit(1)

    print(f"\n[EMISSOR] Status HTTP: {resp.status_code}")
    print("[EMISSOR] Resposta do receptor:")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    evento = gerar_evento_pedido_pago()
    if "--invalido" in sys.argv:
        del evento["cliente"]       
        del evento["valor_total"]
    enviar_webhook(evento)