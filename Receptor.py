"""
SISTEMA RECEPTOR - Estoque e Logística
Expõe o endpoint POST /webhook/pedido-pago, que recebe a notificação
da loja virtual, valida os dados e responde com HTTP 200 (sucesso) ou
com um código de erro (falha).

Executar:  python receptor.py   (porta 5000)
"""
import hashlib
import hmac
from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)

# Segredo compartilhado entre emissor e receptor (assinatura HMAC)
SEGREDO = "segredo-compartilhado-123"

# Campos obrigatórios do evento e o tipo esperado de cada um
CAMPOS_OBRIGATORIOS = {
    "evento": str,
    "pedido_id": int,
    "cliente": dict,
    "itens": list,
    "valor_total": (int, float),
    "data_pagamento": str,
}

# "Banco de dados" em memória com os pedidos já processados
pedidos_recebidos = []


def assinatura_valida(corpo_bruto: bytes, assinatura_recebida: str) -> bool:
    esperada = hmac.new(SEGREDO.encode(), corpo_bruto, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, assinatura_recebida or "")


def validar(dados: dict) -> list:
    """Retorna a lista de erros encontrados (vazia = payload válido)."""
    erros = []
    for campo, tipo in CAMPOS_OBRIGATORIOS.items():
        if campo not in dados:
            erros.append(f"Campo obrigatório ausente: '{campo}'")
        elif not isinstance(dados[campo], tipo):
            erros.append(f"Campo '{campo}' com tipo inválido")

    if not erros:
        if dados["evento"] != "pedido.pago":
            erros.append("Evento não suportado (esperado: 'pedido.pago')")
        if not dados["itens"]:
            erros.append("A lista 'itens' não pode estar vazia")
        for i, item in enumerate(dados["itens"]):
            for c in ("sku", "descricao", "quantidade"):
                if c not in item:
                    erros.append(f"Item {i}: campo '{c}' ausente")
    return erros


@app.post("/webhook/pedido-pago")
def webhook_pedido_pago():
    # 1) Autenticidade: confere a assinatura enviada pelo emissor
    if not assinatura_valida(request.get_data(), request.headers.get("X-Assinatura")):
        print("[RECEPTOR] Requisição rejeitada: assinatura inválida")
        return jsonify(status="erro", mensagem="Assinatura inválida"), 401

    # 2) Interpreta o JSON
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify(status="erro", mensagem="Corpo não é um JSON válido"), 400

    # 3) Valida os campos obrigatórios
    erros = validar(dados)
    if erros:
        print(f"[RECEPTOR] Payload inválido: {erros}")
        return jsonify(status="erro", mensagem="Dados inválidos", erros=erros), 400

    # 4) Processa: separa os itens do pedido para expedição
    pedidos_recebidos.append(dados)
    print("\n" + "=" * 55)
    print(f"[RECEPTOR] Pedido #{dados['pedido_id']} recebido e pago")
    print(f"  Cliente : {dados['cliente'].get('nome')} ({dados['cliente'].get('email')})")
    for item in dados["itens"]:
        print(f"  - {item['quantidade']}x {item['descricao']} (SKU {item['sku']})")
    print(f"  Total   : R$ {dados['valor_total']:.2f}")
    print("  Ação    : itens reservados no estoque, envio liberado")
    print("=" * 55)

    # 5) Responde ao emissor com sucesso
    return jsonify(
        status="sucesso",
        mensagem=f"Pedido {dados['pedido_id']} recebido; separação de estoque iniciada",
        recebido_em=datetime.now().isoformat(timespec="seconds"),
    ), 200


@app.get("/pedidos")
def listar_pedidos():
    """Rota auxiliar para conferir o que o receptor já processou."""
    return jsonify(total=len(pedidos_recebidos), pedidos=pedidos_recebidos)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)