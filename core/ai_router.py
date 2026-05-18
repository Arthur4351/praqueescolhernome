import json
import os
import requests
import threading
from datetime import date
from pathlib import Path


class AIRouter:
    """Roteador de IA com failover automático entre múltiplos provedores gratuitos."""

    _DEFAULT_PROVIDERS = [
        {
            "nome": "Groq-Qwen",
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "api_key": "",
            "modelo": "qwen-3-32b",
            "modelo_codigo": "llama-3.1-8b-instant",
            "limite_diario_tokens": 500000,
            "ativo": True,
            "prioridade": 1
        },
        {
            "nome": "Gemini-Flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "api_key": "",
            "modelo": "gemini-2.0-flash",
            "modelo_codigo": "gemini-2.0-flash",
            "limite_diario_tokens": 1000000,
            "ativo": False,
            "prioridade": 2
        },
        {
            "nome": "OpenRouter-Free",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "api_key": "",
            "modelo": "qwen/qwen3-8b:free",
            "modelo_codigo": "meta-llama/llama-3.1-8b-instruct:free",
            "limite_diario_tokens": 200000,
            "ativo": False,
            "prioridade": 3
        }
    ]

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.usage_file = "ai_usage.json"
        self.today = str(date.today())
        self.providers = []
        self.usage_today = {}
        self.lock = threading.Lock()
        self._load_config()
        self._load_usage()

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)

            raw = cfg.get("provedores_ia", [])
            if not raw:
                raw = [dict(p) for p in self._DEFAULT_PROVIDERS]
                groq_key = cfg.get("GROQ_API_KEY", "")
                if groq_key:
                    raw[0]["api_key"] = groq_key
                cfg["provedores_ia"] = raw
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(cfg, f, indent=2, ensure_ascii=False)

            self.providers = sorted(
                [p for p in raw if p.get("ativo") and p.get("api_key")],
                key=lambda x: x.get("prioridade", 99)
            )
        except Exception as e:
            self.providers = []
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as log:
                log.write(f"AIRouter._load_config: {e}\n")

    def _load_usage(self):
        try:
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get("data") == self.today:
                    self.usage_today = data.get("uso", {})
                    return
        except:
            pass
        self.usage_today = {}

    def _save_usage(self):
        with self.lock:
            try:
                with open(self.usage_file, 'w', encoding='utf-8') as f:
                    json.dump({"data": self.today, "uso": self.usage_today}, f, indent=2)
            except Exception as e:
                with open("erros_conhecidos.txt", "a", encoding="utf-8") as f:
                    f.write(f"AIRouter._save_usage falhou: {e}\n")

    def _is_exhausted(self, provider: dict) -> bool:
        used = self.usage_today.get(provider["nome"], 0)
        limit = provider.get("limite_diario_tokens", 500000)
        return used >= limit * 0.90

    def _mark_exhausted(self, provider: dict):
        limit = provider.get("limite_diario_tokens", 500000)
        self.usage_today[provider["nome"]] = int(limit)
        self._save_usage()

    def _track_usage(self, nome: str, tokens: int):
        self.usage_today[nome] = self.usage_today.get(nome, 0) + tokens
        self._save_usage()

    def _call_provider(self, provider: dict, messages: list, max_tokens: int, temperature: float, use_code_model: bool = False) -> str:
        modelo = provider.get("modelo_codigo", provider["modelo"]) if use_code_model else provider["modelo"]
        headers = {
            "Authorization": f"Bearer {provider['api_key']}",
            "Content-Type": "application/json"
        }
        if "openrouter" in provider["base_url"]:
            headers["HTTP-Referer"] = "https://sophia-ai.local"
            headers["X-Title"] = "Sophia AI"

        payload = {
            "model": modelo,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # Desabilita o modo "thinking" do Qwen3 no Groq (consome tokens extras desnecessariamente)
        if "groq" in provider["base_url"] and "qwen3" in modelo.lower():
            payload["reasoning_effort"] = "none"

        response = requests.post(provider["base_url"], json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()

        tokens_used = data.get("usage", {}).get("total_tokens", max_tokens // 2)
        self._track_usage(provider["nome"], tokens_used)

        return data["choices"][0]["message"]["content"]

    def call(self, messages: list, max_tokens: int = 300, temperature: float = 0.2, use_code_model: bool = False) -> tuple:
        """Tenta cada provedor em ordem. Retorna (content, provider_name). Failover automático."""
        if not self.providers:
            raise Exception("Nenhum provedor de IA ativo. Configure as chaves no config.json.")

        last_error = None
        for provider in self.providers:
            if self._is_exhausted(provider):
                continue
            try:
                content = self._call_provider(provider, messages, max_tokens, temperature, use_code_model)
                return content, provider["nome"]
            except Exception as e:
                err = str(e)
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        err += f" | Detalhe da API: {e.response.text}"
                    except:
                        pass
                last_error = err
                with open("erros_conhecidos.txt", "a", encoding="utf-8") as err_log:
                    err_log.write(f"AIRouter falha no {provider['nome']}: {err}\n")
                    
                if any(x in err for x in ["429", "quota", "rate_limit", "RATE_LIMIT"]):
                    self._mark_exhausted(provider)
                    continue
                elif any(x in err for x in ["401", "403", "invalid_api_key", "API_KEY"]):
                    continue
                else:
                    # Em vez de levantar a exceção imediatamente (raise) e quebrar o roteador,
                    # passamos para o próximo provedor. Isso garante o Failover real.
                    continue

        raise Exception(
            f"⚠️ Todos os provedores atingiram o limite diário ou estão offline.\n"
            f"Último erro: {last_error}\n"
            "Adicione mais chaves em config.json → provedores_ia."
        )

    def call_chat(self, messages: list, max_tokens: int = 300, temperature: float = 0.2) -> tuple:
        return self.call(messages, max_tokens, temperature, use_code_model=False)

    def call_code(self, messages: list, max_tokens: int = 4000, temperature: float = 0.1) -> tuple:
        return self.call(messages, max_tokens, temperature, use_code_model=True)

    def status_report(self) -> str:
        lines = ["📊 <b>Status dos Provedores de IA:</b>"]
        for p in self.providers:
            used = self.usage_today.get(p["nome"], 0)
            limit = p.get("limite_diario_tokens", 500000)
            pct = (used / limit * 100) if limit else 0
            icon = "🟢" if pct < 70 else ("🟡" if pct < 90 else "🔴")
            lines.append(f"{icon} <b>{p['nome']}</b>: {used:,}/{limit:,} tokens ({pct:.1f}%)")
        if not self.providers:
            lines.append("❌ Nenhum provedor ativo.")
        return "<br>".join(lines)
