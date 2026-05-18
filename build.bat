@echo off
echo Iniciando compilacao da SOPHIA AI...
pyinstaller --noconfirm --windowed --name "SOPHIA" --icon="SOPHIA.png" --splash="SOPHIA.png" --add-data "SOPHIA.png;." --add-data "config.json;." --add-data "brain.json;." --add-data "core;core" --add-data "ui;ui" --add-data "assets;assets" --add-data ".agent;.agent" --add-data "dynamic_skills;dynamic_skills" main.py
echo Compilacao finalizada com sucesso!
