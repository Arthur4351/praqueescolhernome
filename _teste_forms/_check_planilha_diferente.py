# -*- coding: utf-8 -*-
"""Prova OFFLINE dos LIMITES de generalidade: e se a planilha for TOTALMENTE diferente?
Roda 2 planilhas contra o MESMO mock do DOM novo (fake_forms_novo.html):
  CASO A = estrutura totalmente diferente (3 colunas c/ TIPO, ordem trocada,
           linha de cabecalho, linha URL, linhas em branco, outros valores),
           MAS os NOMES dos campos batem com os titulos do form.
  CASO B = NOMES sinonimos (companhia/quilometragem/periodo) que um humano
           entende mas NAO batem textualmente com os titulos do form.
Le o DOM de volta em cada caso e mostra o que entrou de fato."""
import io, sys, os, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import openpyxl
from core.forms_submitter import FormsSubmitter

BASE = Path(__file__).resolve().parent
FORM = (BASE / "fake_forms_novo.html").as_uri()
fs = FormsSubmitter(output_dir=str(BASE / "pdfs_demo"))


def montar(nome, linhas):
    wb = openpyxl.Workbook(); ws = wb.active
    for r in linhas:
        ws.append(r)
    p = os.path.join(tempfile.gettempdir(), nome); wb.save(p)
    return p


def ler_dom(pg):
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


# CASO A: estrutura MUITO diferente, porem NOMES batem com os titulos do form
caso_a = montar("_ref_difA.xlsx", [
    ("PERGUNTA", "TIPO", "VALOR"),                 # cabecalho -> deve ser ignorado
    ("LINK", "", "https://exemplo/form"),          # linha de URL -> vira url, nao campo
    ("KM INICIAL", "numero", 999),                 # ordem trocada + tipo explicito + numero
    ("", "", ""),                                  # linha em branco
    ("EMPRESA", "texto", "outra empresa sa"),
    ("INTERDIÇÃO", "opcao", "N/A"),
    ("CONTORNO ICONHA?", "opcao", "SIM"),
    ("HORÁRIO DO SERVIÇO", "opcao", "noturno"),
    ("DATA DO SERVIÇO", "data", "01/01/2027"),
])

# CASO B: NOMES sinonimos que NAO aparecem nos titulos do form (valores nao colidem com opcoes)
caso_b = montar("_ref_difB.xlsx", [
    ("COMPANHIA", "guarana"),                      # form diz "EMPRESA"
    ("QUILOMETRAGEM DE PARTIDA", 500),             # form diz "KM INICIAL"
    ("PERÍODO", "tarde"),                          # form diz "HORÁRIO"; "tarde" nao e opcao
])

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(locale="pt-BR").new_page()

    for rotulo, ref, esperado in [
        ("CASO A (estrutura diferente, nomes batem)", caso_a,
         dict(empresa="outra empresa sa", data="01/01/2027", km="999",
              h_noturno=True, c_sim=True, i_na=True)),
        ("CASO B (nomes sinonimos, nao batem)", caso_b, {}),
    ]:
        plano = FormsSubmitter.parse_reference_sheet(ref)
        pg.goto(FORM)  # reseta o DOM
        res = {}
        for campo in plano["campos"]:
            res[campo["pergunta"]] = fs._preencher_campo(pg, campo)
        estado = ler_dom(pg)

        print("=" * 64)
        print(rotulo)
        print(f"  url lida da planilha: {plano['url']!r}")
        print("  PREENCHEU CADA CAMPO?")
        for k, v in res.items():
            print(f"     {k:26}: {'OK' if v else 'NAO LOCALIZADO'}")
        print("  ESTADO LIDO DO DOM:", {k: v for k, v in estado.items() if v not in ('', False)} or "(nada mudou)")
        if esperado:
            ok = all(estado.get(k) == v for k, v in esperado.items())
            print("  CONFERE O ESPERADO:", "SIM" if ok else "NAO")
            if not ok:
                for k, v in esperado.items():
                    if estado.get(k) != v:
                        print(f"     DIVERGE {k}: esperado {v!r}, veio {estado.get(k)!r}")
    b.close()

for f in (caso_a, caso_b):
    os.remove(f)
