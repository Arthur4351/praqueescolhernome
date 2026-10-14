# -*- coding: utf-8 -*-
"""Prova OFFLINE do "Imprimir -> Salvar como PDF".

Exercita o caminho REAL do FormsSubmitter (emulate_media('print') + page.pdf)
contra um FORMULÁRIO HTML LOCAL — nada de MS Form ao vivo, nada de envio.
Prova que a Sophia gera, em disco, o mesmo PDF que a opção "Imprimir" do
navegador produziria (cabeçalho %PDF). Sem Edge/Playwright, faz SKIP (sai 0).
"""
import io
import os
import sys
import tempfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import Workbook
from core.forms_submitter import FormsSubmitter

falhas = []


def ok(cond, msg):
    print(("  OK  " if cond else " FALHA ") + msg)
    if not cond:
        falhas.append(msg)


tmp = tempfile.mkdtemp(prefix="printpdf_")

# formulário HTML local (um input com rótulo "Observação")
html = Path(tmp) / "form.html"
html.write_text(
    "<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>"
    "<title>Form Local</title></head><body>"
    "<h1>Programação (teste local)</h1>"
    "<label for='obs'>Observação</label>"
    "<input id='obs' name='obs' type='text'>"
    "</body></html>",
    encoding="utf-8",
)

# planilha de referência vertical: URL do form local + 1 campo
xlsx = os.path.join(tmp, "ref.xlsx")
wb = Workbook(); ws = wb.active
ws.append(["URL", html.as_uri()])
ws.append(["Observação", "teste123"])
wb.save(xlsx)

print("\n[0] disponibilidade do Edge/Playwright")
disp, motivo = FormsSubmitter.is_available()
print(f"      is_available() = {disp}  ({motivo})")
if not disp:
    print("\nSKIP: Edge/Playwright ausente neste ambiente — nada a provar aqui.")
    print("      (A lógica de datas/fixos é provada pelos outros _check_*.py.)")
    sys.exit(0)

print("\n[1] fill_from_spreadsheet gera PDF via Imprimir->Salvar como PDF (submit=False)")
fs = FormsSubmitter(output_dir=tmp)
r = fs.fill_from_spreadsheet(xlsx, submit=False, log=lambda m: print("     ", m))
ok(r.get("ok") is True, f"retorno ok -> {r.get('msg')}")
pdf = r.get("pdf")
ok(bool(pdf) and os.path.exists(pdf), f"arquivo PDF existe -> {pdf}")
if pdf and os.path.exists(pdf):
    with open(pdf, "rb") as f:
        head = f.read(5)
    size = os.path.getsize(pdf)
    ok(head.startswith(b"%PDF"), f"cabeçalho %PDF válido -> {head!r}")
    ok(size > 800, f"PDF não-vazio -> {size} bytes")
    print(f"      (campo preenchido no form local: {r.get('preenchidos')}/1)")

print("\n" + ("TODOS OS TESTES PASSARAM ✅" if not falhas else f"{len(falhas)} FALHA(S) ❌"))
sys.exit(0 if not falhas else 1)
