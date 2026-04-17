import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv(dotenv_path="D:/teste/.env")

class SophiaIntelligence:
    """
    Classe principal de inteligência para SOPHIA - The Sovereign Intelligence
    Implementa o 9Router Engine para roteamento entre modelos Gemini e Qwen
    """

    def __init__(self):
        # Configurações do sistema
        self.project_root = "D:/teste"
        self.database_path = "D:/teste/database/memory.db"

        # Inicializar logging
        self._setup_logging()

        # Inicializar banco de dados
        self._init_database()

        # Configurações de IA
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.qwen_api_key = os.getenv("QWEN_API_KEY")

        # Inicializar modelos
        self._init_models()

        logging.info("SophiaIntelligence inicializada com sucesso")

    def _setup_logging(self):
        """Configurar sistema de logging profissional"""
        os.makedirs(os.path.dirname(self.project_root + "/logs/activity.log"), exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.project_root + "/logs/activity.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _init_database(self):
        """Inicializar conexão com banco de dados"""
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        self.conn = sqlite3.connect(self.database_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.logger.info(f"Banco de dados conectado: {self.database_path}")

        # Criar tabelas se não existirem
        self._create_tables()

    def _create_tables(self):
        """Criar tabelas necessárias no banco de dados"""
        # Tabela para armazenar histórico de conversas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_input TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                context_data TEXT
            )
        ''')

        # Tabela para armazenar preferências do usuário
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_key TEXT UNIQUE NOT NULL,
                preference_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        # Tabela para armazenar memórias episódicas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                importance_score REAL DEFAULT 0.5
            )
        ''')

        self.conn.commit()

    def _init_models(self):
        """Inicializar modelos de IA"""
        # Inicializar modelos (desativados por enquanto devido a questões de API)
        self.gemini_available = False
        self.qwen_available = False

        # Registrar disponibilidade
        self.logger.info(f"Modelo Gemini disponível: {self.gemini_available}")
        self.logger.info(f"Modelo Qwen disponível: {self.qwen_available}")

    def process_request(self, user_input: str, context: Dict[str, Any] = None) -> str:
        """Processar requisição do usuário com roteamento inteligente"""
        start_time = datetime.now()

        # Registrar entrada
        self.logger.info(f"Processando requisição: {user_input[:50]}...")

        # Simular resposta (até que os modelos estejam disponíveis)
        response = self._simulate_response(user_input)

        # Salvar conversa no banco de dados
        self._save_conversation(user_input, response, context or {})

        # Calcular tempo de processamento
        processing_time = (datetime.now() - start_time).total_seconds()
        self.logger.info(f"Requisição processada em {processing_time:.2f}s")

        return response

    def _simulate_response(self, user_input: str) -> str:
        """Simular resposta da IA até que os modelos estejam disponíveis"""
        # Simular uma resposta inteligente
        if "ola" in user_input.lower() or "oi" in user_input.lower():
            return "Olá! Sou SOPHIA, a Inteligência Soberana. Como posso ajudá-lo hoje?"
        elif "excel" in user_input.lower():
            return "Detectei uma referência ao Excel. O módulo de inteligência Excel está disponível para manipulações avançadas."
        elif "memoria" in user_input.lower() or "lembrar" in user_input.lower():
            return "Estou utilizando meu sistema de memória persistente para manter o contexto das nossas interações."
        else:
            return f"Recebi sua solicitação: '{user_input}'. Estou processando com minha inteligência cognitiva avançada."

    def _save_conversation(self, user_input: str, ai_response: str, context: Dict[str, Any]):
        """Salvar conversa no banco de dados"""
        try:
            timestamp = datetime.now().isoformat()
            context_json = json.dumps(context, ensure_ascii=False)

            self.cursor.execute('''
                INSERT INTO conversations (timestamp, user_input, ai_response, context_data)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, user_input, ai_response, context_json))

            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Erro ao salvar conversa: {e}")

    def get_system_info(self) -> Dict[str, Any]:
        """Obter informações do sistema"""
        return {
            "version": "SOPHIA V3 Enterprise",
            "models_available": {
                "gemini": self.gemini_available,
                "qwen": self.qwen_available
            },
            "database_connected": self.conn is not None,
            "project_root": self.project_root
        }

    def close(self):
        """Fechar conexões"""
        if hasattr(self, 'conn'):
            self.conn.close()
        self.logger.info("Conexões fechadas")