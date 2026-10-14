@echo off
REM SOPHIA AI — build oficial via spec versionado (one-file, windowed).
REM Saida: dist\SOPHIA.exe
REM
REM NAO empacotar .env (contem segredos) nem arquivos gerados em runtime
REM (config.json, brain.json, long_term_memory.json, ai_usage.json):
REM eles ficam AO LADO do .exe e sao criados/lidos em tempo de execucao.
REM bin\tesseract tambem fica de fora (pesado; instale no Windows ou
REM copie a pasta bin\ para o lado do .exe).
echo Iniciando compilacao da SOPHIA AI...
py -3 -m PyInstaller --noconfirm --clean SOPHIA.spec
echo Compilacao finalizada. O executavel esta em dist\SOPHIA.exe
