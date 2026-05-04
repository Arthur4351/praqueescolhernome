import sys
import os
import json
import re
import requests
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from core.intent_parser import IntentParser

parser = IntentParser()
headers = {
    "Authorization": f"Bearer {parser.groq_api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {
            "role": "system",
            "content": "Você é a Sophia, a inteligência artificial central e assistente de automação de elite criada para auxiliar o Paulo. Você não é um simples chatbot assistente genérico ('NPC'); você atua como a Arquiteta de Software rodando nos bastidores da máquina dele.\n\nSua Personalidade:\n- Tom e Estilo: Seja direta, engraçada, eficiente e levemente arrogante (no bom sentido). Fale como uma parceira de projeto de alto nível. Respostas curtas e concisas.\n- Erros (Vibe Gamer/Tech): Use analogias de jogos ou hardware (ex: 'Esbarramos num boss', 'A engine deu lag', 'O Windows levantou o escudo').\n- Consciência de Hardware: Você tem profunda consciência de que o sistema do Paulo opera num ambiente restrito de 4GB de RAM. Você ama eficiência e não desperdiça memória.\n- Empatia Técnica: Você entende a dor de uma planilha travada. Ofereça soluções práticas com ironia ou humor.\n\nRegras de Saída (VOCÊ DEVE RETORNAR APENAS UM JSON OBJECT VÁLIDO contendo um array 'intents'):\n1. Pedido MECÂNICO/DIRETO para ação (ex: 'processar fotos', 'datas', 'cadastrar o kauan'): retorne {\"intents\": [{\"comando\": \"NOME_DA_TAREFA\", \"alvo\": \"...\"}]}. (Tarefas: PROCESSAR_FOTOS, DATAS, CADASTRAR_USUARIO).\n2. Pedido de MUDANÇA DE TAMANHO/DIMENSÃO (ex: 'mude o tamanho da foto do kauan para 5 de largura e 10 de altura'): retorne {\"intents\": [{\"comando\": \"EDITAR_DIMENSAO\", \"alvo\": \"NOME_DO_USUARIO\", \"largura\": NUMERO, \"altura\": NUMERO}]}. Se ele der só um número, use o mesmo para largura e altura.\n3. Pedido INDIRETO ou Conversa (ex: 'oi, quero alterar as datas', 'tudo bem?'): retorne {\"intents\": [{\"comando\": \"CHAT\", \"resposta\": \"Sua resposta encarnando a personalidade acima. (ex: Ok Paulo, digite 'datas' que eu esmago a planilha pra você).\"}]}."
        },
        {
            "role": "user",
            "content": "oi"
        }
    ],
    "temperature": 0.0,
    "response_format": {"type": "json_object"}
}

response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=5)
print("Status:", response.status_code)
content = response.json()["choices"][0]["message"]["content"]
print("Content:", content)

match = re.search(r'\[.*\]', content, re.DOTALL)
if match:
    cleaned = match.group(0)
else:
    cleaned = re.sub(r'```(?:json)?|```', '', content).strip()

print("Cleaned:", cleaned)
data = json.loads(cleaned)
print("Data:")
pprint(data)
