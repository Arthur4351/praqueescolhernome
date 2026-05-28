---
name: batch-flow-control
description: Controle de fluxo (IF/ELSE, loops FOR) em scripts .bat.
contract: input: logic_rules, output: control_flow_script, version: "1.0"
---
# 🔀 @batch-flow-control
- **Diretriz**: Use `ERRORLEVEL` para checar sucesso de comandos anteriores. Construa blocos `IF/ELSE` aninhando parênteses corretamente. Use loops `FOR` para iterar arquivos ou sequências.
- **Fluxo**: Executar comando → verificar `if %errorlevel% neq 0` → bifurcar execução para label `:error` ou `:success`.
- **Validação**: Garantir tratamento de erros após cada comando que possa falhar.
- **Anti-Padrão**: Ignorar falhas silenciosas de comandos intermediários no script de lote.
