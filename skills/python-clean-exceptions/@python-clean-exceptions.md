---
name: python-clean-exceptions
description: Tratamento e propagação robusta de erros em Python.
contract: input: try_except_blocks, output: secure_error_flow, version: "1.0"
---
# 🚨 @python-clean-exceptions
- **Diretriz**: Nunca capture exceções genéricas de forma silenciosa (`except: pass`). Trate exceções específicas e registre o traceback completo em caso de falha crítica.
- **Fluxo**: Mapear pontos de falha (I/O, rede) → encapsular em blocos try/except específicos → registrar logs → acionar fallback ou lançar exceção humanizada.
- **Validação**: Verificar se todos os recursos abertos (arquivos, sockets) são limpos no bloco `finally` ou via gerenciador de contexto `with`.
- **Anti-Padrão**: `except Exception: return None` sem nenhum registro de log do erro original.
