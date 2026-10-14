# -*- coding: utf-8 -*-
"""Prova OFFLINE do uso REAL: planilha com VARIOS DIAS (layout largo) -> o form e
preenchido UMA VEZ POR DIA, gerando 1 PDF por combinacao. Roda contra o mock do
DOM novo (fake_forms_novo.html), relendo o DOM a cada dia para provar que cada
combinacao entrou com os SEUS valores (inclusive SIM/N/A por pergunta e por dia)."""
import io, sys, os, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import openpyxl
from core.forms_submitter import FormsSubmitter

BASE = Path(__file__).resolve().parent
FORM = (BASE / "fake_forms_novo.html").as_uri()
fs = FormsSubmitter(output_dir=str(BASE / "pdfs_demo"))

# planilha LARGA: 1a linha = titulos (perguntas do form), cada linha = 1 dia
wb = openpyxl.Workbook(); ws = wb.active
ws.append(["EMPRESA", "DATA DO SERVIÇO", "HORÁRIO DO SERVIÇO",
           "CONTORNO ICONHA?", "INTERDIÇÃO", "KM INICIAL"])
ws.append(["guarana",  "27/09/2026", "diurno",  "SIM", "N/A", 14])   # dia 1
ws.append(["cocacola", "28/09/2026", "noturno", "N/A", "SIM", 30])   # dia 2
ws.append(["pepsi",    "29/09/2026", "diurno",  "SIM", "SIM", 55])   # dia 3
ref = os.path.join(tempfile.gettempdir(), "_ref_multidia.xlsx"); wb.save(ref)

plano = FormsSubmitter.parse_reference_sheet_multi(ref)
combos = plano["combinacoes"]
print("COMBINACOES LIDAS DA PLANILHA:", len(combos), "(esperado 3)")

esperado = [
    dict(empresa="guarana",  data="27/09/2026", km="14", h_diurno=True,  c_sim=True, i_na=True),
    dict(empresa="cocacola", data="28/09/2026", km="30", h_noturno=True, c_na=True,  i_sim=True),
    dict(empresa="pepsi",    data="29/09/2026", km="55", h_diurno=True,  c_sim=True, i_sim=True),
]

def ler(pg):
    return pg.evaluate("""() => ({
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

from playwright.sync_api import sync_playwright
tudo_ok = True
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(locale="pt-BR").new_page()
    for i, campos in enumerate(combos):
        pg.goto(FORM)  # cada dia parte do form em branco
        for campo in campos:
            fs._preencher_campo(pg, campo)
        st = ler(pg)
        ok = all(st.get(k) == v for k, v in esperado[i].items())
        tudo_ok = tudo_ok and ok
        print(f"\nDIA {i+1}: {'OK' if ok else 'DIVERGIU'}")
        print("   entrou:", {k: v for k, v in st.items() if v not in ('', False)})
        if not ok:
            for k, v in esperado[i].items():
                if st.get(k) != v:
                    print(f"   DIVERGE {k}: esperado {v!r}, veio {st.get(k)!r}")
    b.close()

# e o metodo de ponta-a-ponta (gera 1 PDF por dia, reaproveitando o mesmo Edge)
r = fs.fill_all_from_spreadsheet(ref, url=FORM)
os.remove(ref)

print("\n" + "=" * 56)
print("CADA DIA COM SEUS PROPRIOS VALORES:", "SIM" if tudo_ok else "NAO")
print("fill_all_from_spreadsheet ->", r["msg"])
print("   PDFs gerados:", len(r.get("pdfs", [])))
for res in r.get("resultados", []):
    print(f"   comb {res['comb']}: {res['preenchidos']}/{res['total']} campos, faltas={res['faltas'] or 'nenhuma'}")
