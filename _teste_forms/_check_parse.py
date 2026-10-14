# -*- coding: utf-8 -*-
"""Prova offline: o leitor generico entende o layout VERTICAL de 2 colunas
(CAMPO | VALOR) sem confundir o valor com 'tipo' e sem chumbar nome de campo."""
import io, sys, os, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import openpyxl
from core.forms_submitter import FormsSubmitter

# 2 colunas: CAMPO | VALOR (sem TIPO, sem linha de URL) — formato vertical generico
wb = openpyxl.Workbook(); ws = wb.active
dados = [
    ("EMPRESA", "guarana dissel"),
    ("COORDENADOR CONTRATO", "bruno duarte"),
    ("DATA DO SERVICO", 27),
    ("HORARIO DO SERVICO", "diurno"),
    ("KM INICIAL", 14),
    ("KM final", 15),
    ("SENTIDO DA OBRA", "N/S"),
    ("Revisao de Solicitacao", "NAO"),
]
for r in dados:
    ws.append(r)
tmp = os.path.join(tempfile.gettempdir(), "_chk_2col.xlsx"); wb.save(tmp)

plano = FormsSubmitter.parse_reference_sheet(tmp)
print("URL   :", plano["url"])
print("CAMPOS (%d):" % len(plano["campos"]))
for c in plano["campos"]:
    print(f"   {c['pergunta']:24} | tipo={c['tipo']!r:8} | valor={c['valor']!r}")

ok = (len(plano["campos"]) == len(dados)
      and all(c["tipo"] == "" for c in plano["campos"])          # tipo autodetectado depois
      and plano["campos"][0]["valor"] == "guarana dissel"        # valor veio da COLUNA B
      and plano["campos"][2]["valor"] == "27"                    # numero vira string
      and plano["url"] is None)                                  # sem linha de URL -> None
print("\nLEITURA 2-COLUNAS (CAMPO|VALOR) OK:", "SIM" if ok else "NAO")
os.remove(tmp)
