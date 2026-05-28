---
name: batch-windows-syntax
description: Sintaxe base de scripts de lote (.bat) no Windows.
contract: input: cmd_commands, output: batch_script, version: "1.0"
---
# ⌨️ @batch-windows-syntax
- **Diretriz**: Use `@echo off` no topo para limpar a saída. Utilize `setlocal enabledelayedexpansion` para expansão dinâmica de variáveis. Declare variáveis localmente.
- **Fluxo**: Declarar variáveis (`set VAR=val`) → executar comandos do sistema → finalizar escopo local.
- **Validação**: Testar comportamento com espaços nos caminhos usando aspas duplas (ex: `"%VAR%"`).
- **Anti-Padrão**: Executar scripts sem pausar ou sem resetar variáveis de ambiente locais.
