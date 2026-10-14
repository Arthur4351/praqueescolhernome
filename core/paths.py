"""Caminhos de runtime da SOPHIA (dev + .exe congelado).

- Em dev: arquivos de runtime (.env, config.json, brain.json,
  long_term_memory.json, ai_usage.json, erros_conhecidos.txt) ficam na
  raiz do projeto.
- No .exe (PyInstaller one-file): ``__file__`` aponta para a pasta
  temporaria ``_MEIPASS`` (somente leitura). Por isso esses arquivos
  precisam ser resolvidos ao lado do executavel: ``sys.executable``.
"""
import os
import sys


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> str:
    """Pasta onde ficam os arquivos de runtime editaveis pelo usuario."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return _project_root()


def runtime_path(name: str) -> str:
    """Caminho absoluto de um arquivo de runtime (leitura e escrita)."""
    return os.path.join(app_dir(), name)


def resource_path(relative_path: str) -> str:
    """Caminho de um dado EMPACOTADO no .exe (somente leitura)."""
    if is_frozen():
        try:
            base_path = sys._MEIPASS  # type: ignore[attr-defined]
        except AttributeError:
            base_path = app_dir()
    else:
        base_path = _project_root()
    return os.path.join(base_path, relative_path)
