@echo off
echo Iniciando compilacao da SOPHIA AI...
pyinstaller --noconfirm --windowed --name "SOPHIA" --icon="SOPHIA.png" --splash="SOPHIA.png" --add-data "SOPHIA.png;." --add-data "config.json;." --add-data "brain.json;." --add-data "core;core" --add-data "ui;ui" --add-data "assets;assets" --add-data "dynamic_skills;dynamic_skills" --add-data "bin;bin" --add-data "models;models" --add-data "skills;skills" --add-data ".env;." --add-data "long_term_memory.json;." --add-data "ai_usage.json;." main.py
echo Compilacao finalizada com sucesso!
