# -*- coding: utf-8 -*-
"""Demo AO VIVO do recurso Forms: planilha de referencia -> preenche/marca -> PDF.
Roda contra o formulario LOCAL _teste_forms/fake_form.html (sem tocar em rede/corporativo).
"""
import io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # raiz do projeto no path
import openpyxl
from core.forms_submitter import FormsSubmitter

BASE = Path(__file__).resolve().parent
FORM = (BASE / "fake_form.html").as_uri()   # file:// com espacos ja escapados
OUT = BASE / "pdfs_demo"

# 1) Monta a PLANILHA DE REFERENCIA (o que a Sophia le): A=PERGUNTA, B=TIPO, C=VALOR
ref = BASE / "_ref_demo.xlsx"
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["PERGUNTA", "TIPO", "VALOR"])
ws.append(["URL", "", FORM])                       # linha especial: define o link do form
ws.append(["Nome completo", "texto", "Arthur Pereira"])
ws.append(["Data do serviço", "texto", "01/03/2026"])
ws.append(["Turno", "opcao", "Diurno"])            # radio
ws.append(["Escopo", "dropdown", "Manutenção"])    # <select>
ws.append(["Itens verificados", "checkbox", "Pneus;Freios;Luzes"])  # marca 3, deixa Escapamento
wb.save(ref)
print("PLANILHA DE REFERENCIA criada:", ref.name)

# 2) Chama o METODO REAL de producao (o mesmo que a GUI usa)
ok, motivo = FormsSubmitter.is_available()
print("is_available:", ok, "|", motivo)
fs = FormsSubmitter(output_dir=str(OUT))
r = fs.fill_from_spreadsheet(str(ref), submit=False, log=lambda m: print("  [sophia]", m))
print()
print("RESULTADO:")
print("  ok        :", r.get("ok"))
print("  preenchidos:", r.get("preenchidos"))
print("  faltas    :", r.get("faltas"))
print("  pdf       :", r.get("pdf"))
print("  msg       :", r.get("msg"))
pdf = r.get("pdf")
if pdf and os.path.exists(pdf):
    print("  PDF existe: SIM, %d bytes" % os.path.getsize(pdf))
else:
    print("  PDF existe: NAO")

# 3) READBACK do DOM: reabre o form, aplica os mesmos campos e LE o que ficou gravado
print()
print("LEITURA DO QUE FICOU NO FORMULARIO (prova de que escreveu/marcou certo):")
plano = FormsSubmitter.parse_reference_sheet(str(ref))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_page(); pg.goto(FORM)
    for campo in plano["campos"]:
        fs._preencher_campo(pg, campo)
    estado = pg.evaluate("""() => ({
        nome: document.getElementById('nome').value,
        data: document.getElementById('data').value,
        diurno: document.getElementById('t_d').checked,
        noturno: document.getElementById('t_n').checked,
        escopo: document.getElementById('escopo').value,
        pneus: document.getElementById('c_p').checked,
        freios: document.getElementById('c_f').checked,
        luzes: document.getElementById('c_l').checked,
        escapamento: document.getElementById('c_e').checked,
    })""")
    b.close()
for k, v in estado.items():
    print(f"   {k:12}: {v}")

esperado = dict(nome="Arthur Pereira", data="01/03/2026", diurno=True, noturno=False,
                escopo="Manutenção", pneus=True, freios=True, luzes=True, escapamento=False)
acertou = all(estado.get(k) == v for k, v in esperado.items())
print()
print("ESCREVEU E MARCOU O CERTO:", "SIM ✅" if acertou else "NAO ❌")
print("GEROU O PDF:", "SIM ✅" if (pdf and os.path.exists(pdf)) else "NAO ❌")
