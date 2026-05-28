import json
import os
import requests
import threading
from datetime import date
from pathlib import Path
from core.file_handler import FileHandler

# Carrega .env automaticamente se disponível
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


class TaskType:
    """Tipos de tarefa para roteamento inteligente de modelos."""
    CHAT      = "chat"        # Bate-papo, conversa rápida
    CODE      = "code"        # Geração / edição de scripts Python
    REASONING = "reasoning"   # Explicações, análise, raciocínio longo
    INTENT    = "intent"      # Detectar intenção do usuário (NLP)


class AIRouter:
    """Roteador de IA com failover automático e roteamento por tipo de tarefa.

    Roteamento inteligente:
    - CHAT      → compound-beta        (rápido, conversacional)
    - CODE      → llama-3.3-70b        (preciso em código)
    - REASONING → qwen-qwq-32b         (raciocínio em cadeia)
    - INTENT    → compound-beta        (eficiente para NLP)

    Failover automático quando o provedor primário atinge 90% do limite diário.
    """

    # Mapa: TaskType → nome do modelo preferido para aquela tarefa
    _TASK_MODEL_MAP = {
        TaskType.CHAT:      "llama-3.3-70b-versatile",
        TaskType.CODE:      "llama-3.3-70b-versatile",
        TaskType.REASONING: "groq/compound",
        TaskType.INTENT:    "llama-3.3-70b-versatile",
    }

    _DEFAULT_PROVIDERS = [
        {
            "nome": "Groq-Llama3.3-Versatile",
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "env_key": "GROQ_API_KEY_1",
            "modelo": "llama-3.3-70b-versatile",
            "modelo_codigo": "llama-3.3-70b-versatile",
            "modelo_reasoning": "groq/compound",
            "modelo_intent": "llama-3.3-70b-versatile",
            "limite_diario_tokens": 500000,
            "ativo": True,
            "prioridade": 1
        },
        {
            "nome": "Groq-Llama3.1-Instant",
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "env_key": "GROQ_API_KEY_1",
            "modelo": "llama-3.1-8b-instant",
            "modelo_codigo": "llama-3.3-70b-versatile",
            "modelo_reasoning": "groq/compound",
            "modelo_intent": "llama-3.3-70b-versatile",
            "limite_diario_tokens": 800000,
            "ativo": True,
            "prioridade": 2
        },
        {
            "nome": "Groq-Compound",
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "env_key": "GROQ_API_KEY_2",
            "modelo": "groq/compound",
            "modelo_codigo": "llama-3.3-70b-versatile",
            "modelo_reasoning": "groq/compound",
            "modelo_intent": "llama-3.3-70b-versatile",
            "limite_diario_tokens": 500000,
            "ativo": True,
            "prioridade": 3
        },
        {
            "nome": "Groq-Qwen3",
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "env_key": "GROQ_API_KEY_3",
            "modelo": "qwen/qwen3-32b",
            "modelo_codigo": "llama-3.3-70b-versatile",
            "modelo_reasoning": "qwen/qwen3-32b",
            "modelo_intent": "llama-3.3-70b-versatile",
            "limite_diario_tokens": 500000,
            "ativo": True,
            "prioridade": 4
        },
        {
            "nome": "OpenRouter-DeepSeek-R1",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "env_key": "OPENROUTER_API_KEY",
            "modelo": "deepseek/deepseek-r1",
            "modelo_codigo": "deepseek/deepseek-r1",
            "modelo_reasoning": "deepseek/deepseek-r1",
            "modelo_intent": "deepseek/deepseek-r1",
            "limite_diario_tokens": 200000,
            "ativo": True,
            "prioridade": 5
        },
        {
            "nome": "OpenRouter-Llama4",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "env_key": "OPENROUTER_API_KEY",
            "modelo": "meta-llama/llama-4-maverick",
            "modelo_codigo": "meta-llama/llama-4-scout",
            "modelo_reasoning": "meta-llama/llama-4-maverick",
            "modelo_intent": "meta-llama/llama-4-maverick",
            "limite_diario_tokens": 200000,
            "ativo": True,
            "prioridade": 6
        },
    ]


    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.usage_file = "ai_usage.json"
        self.today = str(date.today())
        self.providers = []
        self.usage_today = {}
        self.lock = threading.Lock()
        self.last_was_truncated = False
        self._load_config()
        self._load_usage()

    def _resolve_api_key(self, provider: dict) -> str:
        """Resolve a chave da API: primeiro tenta .env, depois config.json legado."""
        env_key = provider.get("env_key", "")
        if env_key:
            val = os.getenv(env_key, "")
            if val:
                return val
        # Fallback: chave direta no provider (compatibilidade retroativa)
        return provider.get("api_key", "")

    def _load_config(self):
        try:
            cfg = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)

            raw = cfg.get("provedores_ia", [])

            # Se não há provedores no config, usa os defaults e injeta as chaves do .env
            if not raw:
                raw = [dict(p) for p in self._DEFAULT_PROVIDERS]

            modelos_ia = cfg.get("modelos_ia", {})
            m_chat = modelos_ia.get("chat") or cfg.get("modelo_chat")
            m_code = modelos_ia.get("code") or cfg.get("modelo_codigo")
            m_reasoning = modelos_ia.get("reasoning")
            m_intent = modelos_ia.get("intent")

            # Injeta chaves de API via env vars (substitui qualquer plaintext legado)
            for p in raw:
                if m_chat: p["modelo"] = m_chat
                if m_code: p["modelo_codigo"] = m_code
                if m_reasoning: p["modelo_reasoning"] = m_reasoning
                if m_intent: p["modelo_intent"] = m_intent

                env_key = p.get("env_key", "")
                if env_key:
                    resolved = os.getenv(env_key, "")
                    if resolved:
                        p["api_key"] = resolved
                elif not p.get("api_key"):
                    # Tenta GROQ_API_KEY genérico como último recurso
                    p["api_key"] = os.getenv("GROQ_API_KEY", "")

            self.providers = sorted(
                [p for p in raw if p.get("ativo") and p.get("api_key")],
                key=lambda x: x.get("prioridade", 99)
            )

        except Exception as e:
            self.providers = []
            FileHandler.log_error(f"AIRouter._load_config: {e}")

    def _load_usage(self):
        try:
            if os.path.exists(self.usage_file):
                with open(self.usage_file, "r", encoding="utf-8") as f:
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
                with open(self.usage_file, "w", encoding="utf-8") as f:
                    json.dump({"data": self.today, "uso": self.usage_today}, f, indent=2)
            except Exception as e:
                FileHandler.log_error(f"AIRouter._save_usage falhou: {e}")

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

    def _call_provider(
        self,
        provider: dict,
        messages: list,
        max_tokens: int,
        temperature: float,
        task_type: str = TaskType.CHAT,
    ) -> str:
        """Seleciona o modelo certo do provider com base no tipo de tarefa."""
        if task_type == TaskType.CODE:
            modelo = provider.get("modelo_codigo", provider["modelo"])
        elif task_type == TaskType.REASONING:
            modelo = provider.get("modelo_reasoning", provider["modelo"])
        elif task_type == TaskType.INTENT:
            modelo = provider.get("modelo_intent", provider["modelo"])
        else:
            # CHAT usa o modelo principal do provider
            modelo = provider["modelo"]

        api_key = self._resolve_api_key(provider)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if "openrouter" in provider["base_url"]:
            headers["HTTP-Referer"] = "https://sophia-ai.local"
            headers["X-Title"] = "Sophia AI"

        # Temperature adaptada por tarefa se não sobrescrita
        if task_type == TaskType.REASONING:
            temperature = min(temperature, 0.4)  # mais determinístico para raciocínio
        elif task_type == TaskType.CODE:
            temperature = min(temperature, 0.1)  # máxima precisão para código

        payload = {
            "model": modelo,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # Ativa reasoning effort em modelos que suportam
        if "groq" in provider["base_url"]:
            if "qwq" in modelo.lower() or "deepseek" in modelo.lower():
                payload["reasoning_effort"] = "default"

        response = requests.post(
            provider["base_url"], json=payload, headers=headers, timeout=25
        )
        response.raise_for_status()
        data = response.json()

        tokens_used = data.get("usage", {}).get("total_tokens", max_tokens // 2)
        self._track_usage(provider["nome"], tokens_used)

        choice = data["choices"][0]
        finish_reason = choice.get("finish_reason")
        if finish_reason == "length":
            self.last_was_truncated = True
            FileHandler.log_error(
                f"AIRouter warning: A resposta do modelo '{modelo}' (provider: '{provider['nome']}') "
                f"foi truncada devido ao limite de max_tokens ({max_tokens})."
            )
        else:
            self.last_was_truncated = False
        msg_data = choice["message"]
        content = msg_data.get("content") or ""
        reasoning = msg_data.get("reasoning") or ""
        return (content if content.strip() else reasoning) or ""

    def call(
        self,
        messages: list,
        max_tokens: int = 300,
        temperature: float = 0.2,
        task_type: str = TaskType.CHAT,
    ) -> tuple:
        self.last_was_truncated = False
        """Roteamento inteligente por tarefa + failover automático.

        Retorna (content, provider_name).
        O modelo escolhido dentro de cada provider depende do task_type.
        """
        if not self.providers:
            raise Exception(
                "Nenhum provedor de IA ativo. Configure as chaves no arquivo .env."
            )

        last_error = None
        for provider in self.providers:
            if self._is_exhausted(provider):
                continue
            try:
                content = self._call_provider(
                    provider, messages, max_tokens, temperature, task_type
                )
                return content, provider["nome"]
            except Exception as e:
                err = str(e)
                if hasattr(e, "response") and e.response is not None:
                    try:
                        err += f" | API: {e.response.text}"
                    except:
                        pass
                last_error = err
                FileHandler.log_error(f"AIRouter falha no {provider['nome']} [{task_type}]: {err}")

                # Apenas marca como esgotado se for erro de cota/limite diário permanente (evita falsos positivos com TPM/RPM temporários)
                if any(x in err.lower() for x in ["quota_exceeded", "daily_limit", "billing_limit", "insufficient_balance", "quota exceeded"]):
                    self._mark_exhausted(provider)
                continue

        raise Exception(
            f"⚠️ Todos os provedores atingiram o limite ou estão offline.\n"
            f"Último erro: {last_error}\n"
            "Configure mais chaves no arquivo .env"
        )

    def call_chat(self, messages: list, max_tokens: int = 300, temperature: float = 0.2) -> tuple:
        return self.call(messages, max_tokens, temperature, task_type=TaskType.CHAT)

    def call_code(self, messages: list, max_tokens: int = 4000, temperature: float = 0.1) -> tuple:
        return self.call(messages, max_tokens, temperature, task_type=TaskType.CODE)

    def call_reasoning(self, messages: list, max_tokens: int = 2000, temperature: float = 0.1) -> tuple:
        return self.call(messages, max_tokens, temperature, task_type=TaskType.REASONING)

    def call_intent(self, messages: list, max_tokens: int = 300, temperature: float = 0.1) -> tuple:
        return self.call(messages, max_tokens, temperature, task_type=TaskType.INTENT)

    def status_report(self) -> str:
        lines = ["📊 <b>Status dos Provedores de IA:</b>"]
        for p in self.providers:
            used = self.usage_today.get(p["nome"], 0)
            limit = p.get("limite_diario_tokens", 500000)
            pct = (used / limit * 100) if limit else 0
            icon = "🟢" if pct < 70 else ("🟡" if pct < 90 else "🔴")
            lines.append(
                f"{icon} <b>{p['nome']}</b> ({p['modelo']}): "
                f"{used:,}/{limit:,} tokens ({pct:.1f}%)"
            )
        if not self.providers:
            lines.append("❌ Nenhum provedor ativo. Verifique o arquivo .env")
        return "<br>".join(lines)
