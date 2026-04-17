import os
import sys
import threading
import queue
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable
import time

class SystemKernel:
    """
    Kernel de sistema e segurança para SOPHIA
    Gerencia threads, logging profissional e segurança
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.project_root = "D:/teste"

        # Inicializar diretórios
        self._init_directories()

        # Configurar logging profissional
        self._setup_professional_logging()

        # Gerenciador de threads
        self.thread_manager = ThreadManager()

        # Gerenciador de filas
        self.task_queue = queue.Queue()

        # Eventos do sistema
        self.system_events = {}

        self.logger.info("SystemKernel inicializado com sucesso")

    def _init_directories(self):
        """Inicializar diretórios necessários"""
        dirs_to_create = [
            "D:/teste/logs",
            "D:/teste/database",
            "D:/teste/assets",
            "D:/teste/excel",
            "D:/teste/core",
            "D:/teste/ui",
            "D:/teste/utils"
        ]

        for dir_path in dirs_to_create:
            os.makedirs(dir_path, exist_ok=True)

        self.logger.info("Diretórios do sistema inicializados")

    def _setup_professional_logging(self):
        """Configurar logging profissional"""
        log_file = "D:/teste/logs/activity.log"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Formatar handler para arquivo
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        # Configurar logger raiz
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        self.logger.info("Logging profissional configurado")

    def register_event(self, event_name: str, callback: Callable):
        """Registrar evento do sistema"""
        self.system_events[event_name] = callback
        self.logger.info(f"Evento registrado: {event_name}")

    def trigger_event(self, event_name: str, *args, **kwargs):
        """Disparar evento do sistema"""
        if event_name in self.system_events:
            try:
                result = self.system_events[event_name](*args, **kwargs)
                self.logger.info(f"Evento disparado: {event_name}")
                return result
            except Exception as e:
                self.logger.error(f"Erro ao disparar evento {event_name}: {e}")
        else:
            self.logger.warning(f"Evento não encontrado: {event_name}")

    def execute_task_async(self, task_func: Callable, *args, **kwargs):
        """Executar tarefa de forma assíncrona"""
        return self.thread_manager.execute_async(task_func, *args, **kwargs)

    def execute_task_sync(self, task_func: Callable, *args, **kwargs):
        """Executar tarefa de forma síncrona"""
        return self.thread_manager.execute_sync(task_func, *args, **kwargs)

    def get_system_info(self) -> Dict[str, Any]:
        """Obter informações do sistema"""
        import psutil
        import platform

        info = {
            "project_root": self.project_root,
            "platform": platform.platform(),
            "python_version": sys.version,
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage(self.project_root).percent,
            "thread_count": threading.active_count(),
            "uptime": getattr(self, '_start_time', datetime.now()),
            "active_tasks": self.thread_manager.get_active_tasks_count()
        }

        return info

    def shutdown(self):
        """Desligar o kernel de forma segura"""
        self.logger.info("Iniciando desligamento do SystemKernel")

        # Parar todas as threads
        self.thread_manager.shutdown_all()

        # Salvar estado do sistema
        self._save_system_state()

        self.logger.info("SystemKernel desligado com sucesso")

    def _save_system_state(self):
        """Salvar estado do sistema"""
        state_file = "D:/teste/database/system_state.json"
        state = {
            "last_shutdown": datetime.now().isoformat(),
            "active_threads": threading.active_count(),
            "tasks_completed": getattr(self, '_tasks_completed', 0)
        }

        import json
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


class ThreadManager:
    """Gerenciador de threads para garantir 120Hz de fluidez"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.active_threads = {}
        self.results = {}
        self.lock = threading.Lock()

        # Initialize logger
        self.logger = logging.getLogger(__name__)

        # Pool de threads
        self.worker_threads = []
        self.task_queue = queue.Queue()
        self.stop_event = threading.Event()

        self._start_worker_threads()

    def _start_worker_threads(self):
        """Iniciar threads de trabalho"""
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"SophiaWorker-{i}",
                daemon=True
            )
            worker.start()
            self.worker_threads.append(worker)

    def _worker_loop(self):
        """Loop de trabalho das threads"""
        while not self.stop_event.is_set():
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:
                    break

                task_id, func, args, kwargs, result_queue = task

                try:
                    result = func(*args, **kwargs)
                    result_queue.put(("success", result))
                except Exception as e:
                    result_queue.put(("error", e))

                self.task_queue.task_done()

            except queue.Empty:
                continue

    def execute_async(self, func: Callable, *args, **kwargs) -> str:
        """Executar função de forma assíncrona"""
        task_id = f"task_{int(time.time() * 1000000)}"
        result_queue = queue.Queue()

        # Adicionar tarefa à fila
        self.task_queue.put((task_id, func, args, kwargs, result_queue))

        # Armazenar referência para acompanhamento
        with self.lock:
            self.active_threads[task_id] = {
                'result_queue': result_queue,
                'start_time': time.time(),
                'function': func.__name__ if hasattr(func, '__name__') else str(func)
            }

        return task_id

    def execute_sync(self, func: Callable, *args, **kwargs):
        """Executar função de forma síncrona"""
        return func(*args, **kwargs)

    def get_result(self, task_id: str, timeout: float = 10.0):
        """Obter resultado de tarefa assíncrona"""
        with self.lock:
            if task_id not in self.active_threads:
                return None, "Task not found"

        try:
            status, result = self.active_threads[task_id]['result_queue'].get(timeout=timeout)

            # Remover da lista de ativas
            with self.lock:
                del self.active_threads[task_id]

            if status == "success":
                return result, None
            else:
                return None, result

        except queue.Empty:
            return None, "Timeout"

    def get_active_tasks_count(self) -> int:
        """Obter número de tarefas ativas"""
        with self.lock:
            return len(self.active_threads)

    def shutdown_all(self):
        """Desligar todas as threads"""
        self.stop_event.set()

        # Enviar sinal de parada para todas as threads
        for _ in range(len(self.worker_threads)):
            self.task_queue.put(None)

        # Aguardar término das threads
        for thread in self.worker_threads:
            thread.join(timeout=2.0)

        self.logger.info("ThreadManager desligado")


class SecurityManager:
    """Gerenciador de segurança do sistema"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.access_logs = []

    def validate_path_access(self, path: str) -> bool:
        """Validar acesso a caminho"""
        # Garantir que o caminho está dentro do diretório permitido
        project_root = os.path.abspath("D:/teste")
        abs_path = os.path.abspath(path)

        return abs_path.startswith(project_root)

    def log_access_attempt(self, path: str, operation: str, success: bool):
        """Registrar tentativa de acesso"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "path": path,
            "operation": operation,
            "success": success
        }
        self.access_logs.append(log_entry)

        self.logger.info(f"Acesso {'permitido' if success else 'negado'}: {operation} {path}")

    def sanitize_filename(self, filename: str) -> str:
        """Sanitizar nome de arquivo"""
        # Remover caracteres perigosos
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        sanitized = filename

        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')

        return sanitized