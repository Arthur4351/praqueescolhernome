---
name: batch-python-runner
description: Inicialização e orquestração de scripts Python a partir de arquivos .bat.
contract: input: python_script_path, output: run_status, version: "1.0"
---
# 🚀 @batch-python-runner
- **Diretriz**: Use scripts de lote para ativar ambientes virtuais (`.venv\Scripts\activate.bat`) antes de rodar comandos `python`. Verifique se a versão mínima do python existe no PATH.
- **Fluxo**: Checar se virtualenv existe → ativar ambiente → instalar dependências se `requirements.txt` mudar → rodar `python script.py %*` → desativar venv.
- **Validação**: Retornar o código de saída (`exit /b %errorlevel%`) do processo Python de volta para o chamador do script Batch.
- **Anti-Padrão**: Rodar python globalmente sem ambiente virtual isolado em sistemas de produção.
