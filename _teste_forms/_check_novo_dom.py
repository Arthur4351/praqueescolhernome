# -*- coding: utf-8 -*-
"""Prova OFFLINE (sem rede) de que _preencher_campo acerta o DOM do MS Forms NOVO
e, principalmente, que o ESCOPO por bloco impede a colisão de rótulos repetidos
("N/A" existe em CONTORNO e em INTERDIÇÃO — cada uma tem que marcar o SEU)."""
import io, sys, os, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import openpyxl
from core.forms_submitter import FormsSubmitter

BASE = Path(__file__).resolve().parent
FORM = (BASE / "fake_forms_novo.html").as_uri()

# 1) planilha de referência 2-colunas (CAMPO | VALOR) — nomes = títulos do form
wb = openpyxl.Workbook(); ws = wb.active
dados = [
    ("EMPRESA", "guarana dissel"),
    ("DATA DO SERVIÇO", "27/09/2026"),
    ("HORÁRIO DO SERVIÇO", "diurno"),
    ("CONTORNO ICONHA?", "SIM"),
    ("INTERDIÇÃO", "N/A"),
    ("KM INICIAL", "14"),
]
for r in dados:
    ws.append(r)
ref = os.path.join(tempfile.gettempdir(), "_ref_novo.xlsx"); wb.save(ref)

plano = FormsSubmitter.parse_reference_sheet(ref)
fs = FormsSubmitter(output_dir=str(BASE / "pdfs_demo"))

from playwright.sync_api import sync_playwright
res = {}
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(locale="pt-BR").new_page()
    pg.goto(FORM)
    for campo in plano["campos"]:
        ok = fs._preencher_campo(pg, campo)
        res[campo["pergunta"]] = ok
    estado = pg.evaluate("""() => ({
        empresa: document.getElementById('in_empresa').value,
        data: document.getElementById('in_data').value,
        km: document.getElementById('in_km').value,
        h_diurno: document.getElementById('r_h_diurno').checked,
        h_noturno: document.getElementById('r_h_noturno').checked,
        c_sim: document.getElementById('r_c_sim').checked,
        c_na: document.getElementById('r_c_na').checked,
        i_sim: document.getElementById('r_i_sim').checked,
        i_na: document.getElementById('r_i_na').checked,
    })""")
    b.close()
os.remove(ref)

print("PREENCHEU CADA CAMPO?")
for k, v in res.items():
    print(f"   {k:22}: {'OK' if v else 'FALHOU'}")
print("\nESTADO LIDO DO DOM:")
for k, v in estado.items():
    print(f"   {k:10}: {v}")

esperado = dict(empresa="guarana dissel", data="27/09/2026", km="14",
                h_diurno=True, h_noturno=False,
                c_sim=True,  c_na=False,     # CONTORNO marcou SIM (seu N/A fica off)
                i_sim=False, i_na=True)      # INTERDIÇÃO marcou o SEU N/A (não o do CONTORNO)
acertou = all(estado.get(k) == v for k, v in esperado.items())
print("\nTUDO CERTO (incl. anti-colisão N/A):", "SIM" if acertou else "NAO")
if not acertou:
    for k, v in esperado.items():
        if estado.get(k) != v:
            print(f"   DIVERGE {k}: esperado {v!r}, veio {estado.get(k)!r}")
