---
name: batch-error-redirect
description: Redirecionamento de saída (stdout/stderr) e logs em .bat.
contract: input: execution_log, output: redirected_stream, version: "1.0"
---
# 📝 @batch-error-redirect
- **Diretriz**: Redirecione a saída padrão (`> log.txt`) e erros (`2>&1`) para arquivos de log claros. Valide códigos de saída em scripts automatizados de CI/CD.
- **Fluxo**: Rodar comando → redirecionar fluxos `> stdout.log 2> stderr.log` → ler log de erro se `ERRORLEVEL` for diferente de zero.
- **Validação**: Garantir que logs sejam limpos ou rotacionados para não ocupar espaço infinito em disco.
- **Anti-Padrão**: Ocultar erros redirecionando para `NUL` (`2>nul`) em processos críticos sem tratamento posterior.
