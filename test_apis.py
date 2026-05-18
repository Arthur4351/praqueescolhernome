import json
import requests
import os

def testar_apis():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    provedores = config.get("provedores_ia", [])
    
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 10
    }

    for prov in provedores:
        nome = prov.get("nome")
        url = prov.get("base_url")
        key = prov.get("api_key")
        modelo = prov.get("modelo")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}"
        }
        
        # Gemini usa formato diferente para API KEY na URL, mas via OpenAI compability pode usar Bearer ou x-goog-api-key?
        if "generativelanguage" in url:
            # Compatibilidade OpenAI no Gemini
            pass
            
        payload["model"] = modelo
        
        print(f"Testando {nome} ({modelo})...")
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=10)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                print("  OK: Resposta recebida.")
            else:
                print(f"  ERRO: {resp.text[:200]}")
        except Exception as e:
            print(f"  FALHA DE REDE: {e}")
        print("-" * 40)

if __name__ == "__main__":
    testar_apis()
