# -*- coding: utf-8 -*-
"""BATERIA SUPREMA — regressao de SEGURANCA (RCE morto, code-gen estacionado,
eval sandbox). Prova ao vivo: (1) main.py recusa executar .py arbitrario
(exit 2) mas ainda compila via py_compile; (2) DynamicCoder recusa gerar/editar
(🔒) sem escrever/rodar nada; (3) o eval do dynamic_filter so aceita expressao
segura (allowlist de AST) e bloqueia escapes classicos."""
import io, sys, os, tempfile, shutil, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TMP = tempfile.mkdtemp(prefix="sophia_seg_")
PY = sys.executable
passes, fails = 0, 0
def check(nome, cond, ev=""):
    global passes, fails
    passes += bool(cond); fails += (not cond)
    print(f"  [{'OK' if cond else 'FALHOU'}] {nome}" + (f"  ->  {ev}" if ev else ""))

print("=" * 74)
print("1) main.py — Caso 2 (executar .py arbitrario) DEVE ser RECUSADO")
print("=" * 74)
sentinela = os.path.join(TMP, "malicioso.py")
Path(sentinela).write_text("print('SENTINELA_RCE_DISPAROU')\n", encoding="utf-8")
r = subprocess.run([PY, str(ROOT / "main.py"), sentinela],
                   capture_output=True, text=True, cwd=str(TMP))
check("returncode == 2 (recusa)", r.returncode == 2, f"rc={r.returncode}")
check("sentinela NAO executou", "SENTINELA_RCE_DISPAROU" not in (r.stdout or ""),
      f"stdout={r.stdout!r}")
check("mensagem de recusa presente", "desativada por seguran" in (r.stderr or "").lower(),
      f"stderr={r.stderr.strip()!r}")

print("\n" + "=" * 74)
print("2) main.py — Caso 1 (-m py_compile) continua funcionando (inofensivo)")
print("=" * 74)
bom = os.path.join(TMP, "bom.py")
Path(bom).write_text("x = 1 + 1\n", encoding="utf-8")
r1 = subprocess.run([PY, str(ROOT / "main.py"), "-m", "py_compile", bom],
                    capture_output=True, text=True, cwd=str(TMP))
check("py_compile de arquivo valido -> rc 0", r1.returncode == 0, f"rc={r1.returncode}")
ruim = os.path.join(TMP, "ruim.py")
Path(ruim).write_text("def (:\n", encoding="utf-8")
r2 = subprocess.run([PY, str(ROOT / "main.py"), "-m", "py_compile", ruim],
                    capture_output=True, text=True, cwd=str(TMP))
check("py_compile de arquivo invalido -> rc != 0", r2.returncode != 0, f"rc={r2.returncode}")

print("\n" + "=" * 74)
print("3) DynamicCoder — geracao/edicao ESTACIONADA (🔒), nada escrito/rodado")
print("=" * 74)
existia_skills = (ROOT / "dynamic_skills").exists()
from core.dynamic_coder import DynamicCoder
dc = DynamicCoder("chave_fake_nao_usada")
r_gen = dc.generate_and_run("crie uma macro VBA e rode na planilha")
check("generate_and_run recusa com 🔒", "🔒" in r_gen, r_gen[:60])
alvo = os.path.join(TMP, "arquivo_alvo.txt")  # nao deve ser criado/alterado
r_edit = dc.edit_project_file(alvo, "injete um backdoor")
check("edit_project_file recusa com 🔒", "🔒" in r_edit, r_edit[:60])
check("edit_project_file NAO criou/alterou o alvo", not os.path.exists(alvo))
# limpeza do dir criado so pela construcao do coder
if not existia_skills and (ROOT / "dynamic_skills").exists():
    shutil.rmtree(ROOT / "dynamic_skills", ignore_errors=True)

print("\n" + "=" * 74)
print("4) dynamic_filter — eval sob allowlist de AST")
print("=" * 74)
from core.dynamic_filter import DynamicFilter
# expressoes SEGURAS: compilam e avaliam
seg = DynamicFilter("int(dia) in [1, 2, 3]")
check("expr segura compila", seg.code_obj is not None)
check("expr segura avalia (dia=2 -> True)", seg.evaluate({"dia": "2"}) is True)
seg2 = DynamicFilter("nome.lower().startswith('jo')")
check("metodo de string seguro compila", seg2.code_obj is not None)
check("metodo seguro avalia (nome=JOAO -> True)", seg2.evaluate({"nome": "JOAO"}) is True)
# expressoes MALICIOSAS: rejeitadas na allowlist -> code_obj None (nunca chega ao eval)
maliciosas = [
    "().__class__.__bases__[0]",                 # escape classico
    "__import__('os').system('dir')",            # import + system
    "open('segredo.txt')",                       # funcao fora da whitelist
    "dia.__class__",                             # dunder via atributo
    "nome.format(x)",                            # format nao permitido
    "[c for c in nome]",                         # compreensao nao permitida
]
for m in maliciosas:
    df = DynamicFilter(m)
    check(f"REJEITA {m}", df.code_obj is None)

shutil.rmtree(TMP, ignore_errors=True)
print("\n" + "=" * 74)
print(f"RESUMO SEGURANCA: {passes} passaram, {fails} falharam.")
print("=" * 74)
sys.exit(1 if fails else 0)
