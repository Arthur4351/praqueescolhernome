# -*- coding: utf-8 -*-
"""Prova OFFLINE da DATA do serviço: 1 dia, intervalo (8 a 20) e lista (7 e 8),
mais a multiplicação (data × combinação). Sem navegador. Sai 0 se tudo ok."""
import io
import os
import sys
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.forms_submitter import FormsSubmitter as FS

falhas = []
HOJE = date(2026, 10, 1)  # outubro/2026 (31 dias) — fixa p/ teste determinístico


def ok(cond, msg):
    print(("  OK  " if cond else " FALHA ") + msg)
    if not cond:
        falhas.append(msg)


def dias(texto):
    return [d.day for d in FS.parse_datas(texto, hoje=HOJE)]


print("\n[1] UM dia")
ok(dias("8") == [8], f"'8' -> {dias('8')}")
ok(dias("dia 8") == [8], f"'dia 8' -> {dias('dia 8')}")

print("\n[2] INTERVALO (faz todo o range)")
ok(dias("8 a 20") == list(range(8, 21)), f"'8 a 20' -> {dias('8 a 20')}")
ok(dias("8 até 20") == list(range(8, 21)), "'8 até 20'")
ok(dias("8-20") == list(range(8, 21)), "'8-20'")
ok(dias("do dia 8 ao dia 20 desse mês") == list(range(8, 21)), "'do dia 8 ao dia 20 desse mês'")
ok(dias("20 a 8") == list(range(8, 21)), "'20 a 8' (invertido) normaliza")

print("\n[3] LISTA (só esses dias)")
ok(dias("7 e 8") == [7, 8], f"'7 e 8' -> {dias('7 e 8')}")
ok(dias("7, 8") == [7, 8], "'7, 8'")
ok(dias("8 e 10 e 12") == [8, 10, 12], f"'8 e 10 e 12' -> {dias('8 e 10 e 12')}")

print("\n[4] COMBINAÇÃO intervalo + lista")
ok(dias("8 a 10 e 15") == [8, 9, 10, 15], f"'8 a 10 e 15' -> {dias('8 a 10 e 15')}")

print("\n[5] bordas: vazio, dia inválido, range estourando o mês")
ok(dias("") == [], "'' -> []")
ok(dias("40") == [], "'40' (não existe em out) -> []")
ok(dias("8 a 40") == list(range(8, 32)), "'8 a 40' limita ao fim do mês (31)")

print("\n[6] expansão (data × combinação): 2 combinações × 2 dias = 4 preenchimentos")
combos = [[{"pergunta": "Serviço", "tipo": "", "valor": "Limpeza"}],
          [{"pergunta": "Serviço", "tipo": "", "valor": "Conserva"}]]
datas = FS.parse_datas("8 e 9", hoje=HOJE)
exp = FS._expandir_por_data(combos, datas, label="Data")
ok(len(exp) == 4, f"4 preenchimentos -> {len(exp)}")
pares = []
for c in exp:
    d = {x["pergunta"]: x["valor"] for x in c}
    pares.append((d.get("Data"), d.get("Serviço")))
esperado = [("08/10/2026", "Limpeza"), ("08/10/2026", "Conserva"),
            ("09/10/2026", "Limpeza"), ("09/10/2026", "Conserva")]
ok(pares == esperado, f"cada dia repete as combinações -> {pares}")

print("\n[7] data da planilha é SOBRESCRITA pela data perguntada (sem duplicar)")
combos2 = [[{"pergunta": "Data do serviço", "tipo": "", "valor": "01/01/2000"},
            {"pergunta": "Serviço", "tipo": "", "valor": "Limpeza"}]]
exp2 = FS._expandir_por_data(combos2, FS.parse_datas("8", hoje=HOJE), label="Data")
c = exp2[0]
datas_no_combo = [x["valor"] for x in c if "data" in x["pergunta"].lower()]
ok(datas_no_combo == ["08/10/2026"], f"só a data nova, sem duplicar -> {datas_no_combo}")

print("\n[8] sem data informada -> combinações intactas (comportamento atual)")
ok(FS._expandir_por_data(combos, [], label="Data") == combos, "datas vazio -> idem")

print("\n[9] label_campo_data default = 'Data'")
ok(FS.label_campo_data(config_path=os.path.join(os.path.dirname(__file__), "nao_existe.json")) == "Data",
   "default 'Data'")


def primeiro(texto):
    r = FS.parse_datas(texto, hoje=HOJE)
    return r[0] if r else None


print("\n[10] MÊS por extenso (default = mês de hoje quando omitido)")
ok(dias("8 de novembro") == [8], f"'8 de novembro' -> dia {dias('8 de novembro')}")
ok(primeiro("8 de novembro").month == 11, "mês 'novembro' = 11")
ok(primeiro("8 de nov").month == 11, "abreviação 'nov' = 11")
ok(dias("8 a 10 de novembro") == [8, 9, 10], f"'8 a 10 de novembro' -> {dias('8 a 10 de novembro')}")
ok(primeiro("8 a 10 de novembro").month == 11, "intervalo mantém o mês nov")
ok(primeiro("15 de marco").month == 3, "'marco' (sem acento) = 3")
ok(primeiro("8").month == HOJE.month, "sem mês -> mês de hoje (out=10)")

print("\n[11] MÊS por número (barra 'DD/MM'); barra não vira dia")
ok(dias("8/11") == [8] and primeiro("8/11").month == 11, "'8/11' -> dia 8, mês 11")
ok(dias("8 a 20/11") == list(range(8, 21)), f"'8 a 20/11' -> {dias('8 a 20/11')}")
ok(primeiro("8 a 20/11").month == 11, "'8 a 20/11' mês = 11")
ok(dias("7 e 8/11") == [7, 8], f"'7 e 8/11' -> {dias('7 e 8/11')}")

print("\n[12] ANO explícito (4 dígitos) — não é confundido com dia")
ok(primeiro("8/11/2027").year == 2027, "'8/11/2027' ano = 2027")
ok((primeiro("8/11/2027").day, primeiro("8/11/2027").month) == (8, 11), "'8/11/2027' dia/mês = 8/11")
ok(primeiro("8 de novembro de 2027").year == 2027, "'... de 2027' ano = 2027")
ok(dias("8 a 10 de 2030") == [8, 9, 10], f"ano sem mês -> só dias, mês de hoje {dias('8 a 10 de 2030')}")

print("\n[13] fim de mês respeita o mês escolhido")
ok(dias("28 a 30/02") == [28], "'28 a 30/02' -> fev/2026 vai só até 28 (não bissexto)")
ok(dias("28 a 31/11") == [28, 29, 30], "'28 a 31/11' -> novembro tem 30 dias")

print("\n" + ("TODOS OS TESTES PASSARAM ✅" if not falhas else f"{len(falhas)} FALHA(S) ❌"))
sys.exit(0 if not falhas else 1)
