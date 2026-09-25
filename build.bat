@echo off
echo Iniciando compilacao da SOPHIA AI...

REM NAO empacotar .env (contem segredos) nem arquivos gerados em runtime
REM (config.json, brain.json, long_term_memory.json, ai_usage.json): eles
REM ficam ao lado do .exe e sao criados/lidos em tempo de execucao.
REM Tambem removidas pastas inexistentes (models, dynamic_skills) que faziam
REM o PyInstaller falhar.
pyinstaller --noconfirm --windowed --name "SOPHIA" --icon="SOPHIA.png" --splash="SOPHIA.png" ^
  --add-data "SOPHIA.png;." ^
  --add-data "core;core" ^
  --add-data "ui;ui" ^
  --add-data "assets;assets" ^
  --add-data "bin;bin" ^
  --add-data "skills;skills" ^
  main.py

echo Compilacao finalizada.
