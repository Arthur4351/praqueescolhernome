---
name: batch-file-handler
description: Manipulação de arquivos e caminhos no prompt do Windows via .bat.
contract: input: path_operation, output: file_op_script, version: "1.0"
---
# 📂 @batch-file-handler
- **Diretriz**: Valide a existência de caminhos usando `if exist` antes de manipular. Use caminhos absolutos ou relativos qualificados. Aspas obrigatórias em caminhos com espaços.
- **Fluxo**: Validar origem (`if exist "%SRC%"`) → criar destino se necessário (`mkdir "%DST%"`) → executar operação (copy/move/del).
- **Validação**: Verificar integridade do arquivo após movimentações críticas.
- **Anti-Padrão**: Tentar ler ou copiar arquivos sem checar permissões de acesso do terminal.
