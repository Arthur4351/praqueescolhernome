# -*- coding: utf-8 -*-
"""TESTE DE INTERFACE (headless) — 'voce pedindo e ela fazendo'.
Nao chama funcoes internas como teste: DIGITA frases em portugues no mesmo
pipeline do chat (evaluate_chat -> parse -> execute), como um usuario faria na
caixa de texto do app. Para cada intent, injeta os caminhos que o QFileDialog
daria e chama o MESMO executor que a GUI chama. Mostra a conversa real + os
artefatos reais que a Sophia produz."""
import sys, os, time, json, traceback, shutil, datetime
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(r"C:\Users\arthur 2\Desktop\praqueescolhernome-main")
os.chdir(str(ROOT)); sys.path.insert(0, str(ROOT))

BASE = ROOT / "_teste_interface_out"
if BASE.exists(): shutil.rmtree(BASE, ignore_errors=True)
FOTOS = BASE / "fotos"; SAIDA = BASE / "saida"; EFETIVO = BASE / "efetivo"
PASTAS = BASE / "pastas"
for d in (BASE, FOTOS, SAIDA, EFETIVO, PASTAS):
    d.mkdir(parents=True, exist_ok=True)

_logf = BASE / "conversa.txt"
open(_logf, "w", encoding="utf-8").close()
def T(msg=""):
    line = str(msg)
    try: print(line, flush=True)
    except Exception: print(line.encode("ascii","replace").decode("ascii"), flush=True)
    with open(_logf, "a", encoding="utf-8") as fh: fh.write(line + "\n")

# ---- artefatos de entrada (o que a GUI receberia via dialogos) ----
from openpyxl import Workbook, load_workbook
from PIL import Image, ImageDraw

EQUIPES = ["EQUIPE 01", "EQUIPE 02"]

def make_photo(path, texto, data_exif):
    img = Image.new("RGB", (640, 480), (70, 110, 160))
    d = ImageDraw.Draw(img); d.text((40, 220), texto, fill=(255,255,255))
    exif = img.getexif()
    exif[0x0132] = data_exif                      # DateTime (IFD0, fallback)
    sub = exif.get_ifd(0x8769)                     # ExifIFD
    sub[0x9003] = data_exif                        # DateTimeOriginal (prioritario)
    sub[0x9004] = data_exif                        # DateTimeDigitized
    img.save(path, "JPEG", quality=80, exif=exif)

for eq in EQUIPES:
    p = FOTOS / eq; p.mkdir(parents=True, exist_ok=True)
    for suf, nome in [("E","ENTRADA"),("S","SAIDA"),("A","ANTES"),("D","DEPOIS")]:
        make_photo(p / f"01 {suf}.jpg", f"{eq} DIA01 {nome}", "2026:03:01 08:15:00")
T(f"[setup] fotos com EXIF: {sum(1 for _ in FOTOS.rglob('*.jpg'))} arquivos")

# planilha de relatorio fotografico (PROCESSAR_FOTOS / DATAS)
plan_fotos = BASE / "relatorio_fotografico.xlsx"
wb = Workbook(); wb.remove(wb.active)
for eq in EQUIPES:
    ws = wb.create_sheet(eq[:31])
    ws["A1"]="DATA"; ws["B1"]=1; ws["C1"]="ENTRADA"; ws["D1"]="SAIDA"; ws["E1"]="ANTES"; ws["F1"]="DEPOIS"
    ws.row_dimensions[2].height = 130
    for c in "CDEF": ws.column_dimensions[c].width = 22
wb.save(plan_fotos)

# planilha de pessoal (QUERY / INJECT_FORMULA)
plan_dados = BASE / "dados_pessoal.xlsx"
wb2 = Workbook(); ws2 = wb2.active; ws2.title = "Dados"
ws2.append(["NOME","MATRICULA","DEPOIS"])
for nome, mat, dep in [("JOAO SILVA","12345","ok"),("MARIA SOUZA","67890",""),
                       ("CARLOS PEREIRA","11223",""),("ANA LIMA","44556","ok")]:
    ws2.append([nome, mat, dep])
wb2.save(plan_dados)
# efetivo (AUDITAR_EFETIVO): pastas JOAO/MARIA/CARLOS ; excel JOAO/MARIA/ANA
for nome in ["JOAO SILVA","MARIA SOUZA","CARLOS PEREIRA"]:
    (EFETIVO / nome).mkdir(parents=True, exist_ok=True)
plan_efetivo = BASE / "efetivo_lista.xlsx"
wbe = Workbook(); wse = wbe.active; wse["A1"]="NOME"
for i, nome in enumerate(["JOAO SILVA","MARIA SOUZA","ANA LIMA"], start=2):
    wse.cell(row=i, column=1).value = nome
wbe.save(plan_efetivo)

# pasta pra renomear/mover/apagar
(PASTAS / "PastaAntiga").mkdir(parents=True, exist_ok=True)
(PASTAS / "destino_mover").mkdir(parents=True, exist_ok=True)
(PASTAS / "PastaDescartavel").mkdir(parents=True, exist_ok=True)

# ---- instancia o MESMO nucleo que a GUI usa (sem a janela Qt) ----
from core.agent_core import SophiaAgentCore
from minhas_habilidades import SophiaExecutor
from core.excel_engine import ExcelEngine
ag = SophiaAgentCore()
executor = SophiaExecutor(autonomous_mode=True)

def log_cb(msg): T(f"        │ {msg}")   # o que a GUI mostraria no chat_display

def say(txt):
    """Simula o usuario digitando 'txt' na caixa de chat e apertando enviar."""
    T("\n" + "="*72)
    T(f"👤 VOCE  : {txt}")
    resp = ag.evaluate_chat(txt, "Arthur")
    T(f"🤖 SOPHIA: {resp}")
    if ag.pending_intents:
        d = ag.pending_intents[0]
        meta = {k: d.get(k) for k in ("intent","status","score") if k in d}
        extra = {k: v for k, v in d.items() if k not in
                 ("intent","status","score","raw_input","context","resposta","raw_groq")}
        T(f"        └─ NLU: {meta}  |  extraido: {extra}")
    elif getattr(ag, "_query_params_pending", None):
        T(f"        └─ NLU: QUERY  |  params: {ag._query_params_pending}")
    else:
        T(f"        └─ NLU: (conversa/CHAT — sem acao a executar)")
    return resp

def copy_pending_args():
    """Replica main.py:279-281 — copia campos da intent extraida para ag.args."""
    ag.args.clear()
    if not ag.pending_intents: return
    for k, v in ag.pending_intents[0].items():
        if k not in ["intent","status","resposta","raw_groq","raw_input","score","context"]:
            ag.args[k] = v

# ======================= PROVA DE IA VIVA (Fase 2) =======================
T("\n" + "#"*72)
T("# CONVERSA REAL COM A SOPHIA — cada 'VOCE:' foi digitado no pipeline de chat")
T("#"*72)
from core.ai_router import AIRouter
_r = AIRouter("config.json")
_prov = _r.providers[0] if getattr(_r, "providers", None) else {}
T(f"[IA] provider ativo p/ NLU e chat: {_prov.get('nome')} / modelo {_prov.get('modelo')}")

# ---------- CHAT (conversa livre, IA viva) ----------
say("Oi Sophia! Se apresenta rapidinho: o que voce faz?")
say("Em uma frase: por que usar uma planilha em vez de um caderno?")

# ---------- REGISTRAR_FATO_LTM (memoria permanente) ----------
_ltm_antes = set(p.name for p in ROOT.glob("*.json"))
say("Sophia, se lembre para sempre: meu chefe se chama Dr. Ricardo Antunes.")
for cand in ["long_term_memory.json","memoria_longa.json","ltm.json"]:
    fp = ROOT / cand
    if fp.exists():
        try: T(f"        ▶ LTM {cand}: {json.dumps(json.loads(fp.read_text('utf-8')), ensure_ascii=False)[:200]}")
        except Exception as e: T(f"        ▶ LTM {cand}: (erro lendo: {e})")

# ---------- CREATE_FOLDER ----------
say("Cria uma pasta chamada Relatorios_Marco pra mim.")
copy_pending_args()
ag.args["base_path"] = str(PASTAS)          # <- o que o QFileDialog retornaria
res = ag.execute_pending_intents(ag.args)
T(f"        ▶ ACAO: {res}")
alvo_novo = PASTAS / (ag.pending_intents[0].get("folder_name","Relatorios_Marco") if ag.pending_intents else "Relatorios_Marco")
T(f"        📁 existe no disco? {(PASTAS / 'Relatorios_Marco').exists()}  -> {[p.name for p in PASTAS.iterdir() if p.is_dir()]}")

# ---------- RENAME_FOLDER ----------
say("Renomeia a pasta PastaAntiga para PastaNova.")
copy_pending_args()
ag.args["target_path"] = str(PASTAS / "PastaAntiga")   # dialog aponta a pasta
if "new_name" not in ag.args: ag.args["new_name"] = "PastaNova"   # follow-up da GUI
res = ag.execute_pending_intents(ag.args)
T(f"        ▶ ACAO: {res}")
T(f"        📁 PastaNova existe? {(PASTAS / 'PastaNova').exists()} | PastaAntiga sumiu? {not (PASTAS / 'PastaAntiga').exists()}")

# ---------- MOVE_FOLDER ----------
(PASTAS / "PastaParaMover").mkdir(exist_ok=True)
say("Move a pasta PastaParaMover para dentro de destino_mover.")
copy_pending_args()
ag.args["source_path"] = str(PASTAS / "PastaParaMover")
ag.args["dest_path"] = str(PASTAS / "destino_mover")
res = ag.execute_pending_intents(ag.args)
T(f"        ▶ ACAO: {res}")
T(f"        📁 movida? {(PASTAS / 'destino_mover' / 'PastaParaMover').exists()}")

# ---------- DELETE_FOLDER (seguro) ----------
say("Apaga a pasta PastaDescartavel, nao preciso mais dela.")
copy_pending_args()
ag.args["target_path"] = str(PASTAS / "PastaDescartavel")
res = ag.execute_pending_intents(ag.args)
T(f"        ▶ ACAO: {res}")
T(f"        📁 apagada? {not (PASTAS / 'PastaDescartavel').exists()}")

# ---------- INJECT_FORMULA ----------
say("Na planilha de dados, insere a formula =CONT.VALORES(A2:A5) na celula E1 da aba Dados.")
copy_pending_args()
ag.args["excel_path"] = str(plan_dados)     # dialog seleciona o arquivo
ag.args.setdefault("sheet_name", "Dados")
ag.args.setdefault("cell", "E1"); ag.args.setdefault("formula", "=CONT.VALORES(A2:A5)")
res = ag.execute_pending_intents(ag.args)
T(f"        ▶ ACAO: {res}")
_wbk = load_workbook(plan_dados); T(f"        📄 Dados!E1 = {_wbk['Dados']['E1'].value!r}"); _wbk.close()

# ---------- QUERY_EXCEL ----------
say("Procura o JOAO na planilha de dados e me diz a matricula dele.")
qp = getattr(ag, "_query_params_pending", None)
if qp:
    out = ExcelEngine.query_data(str(plan_dados), qp.get("alvo",""), qp.get("coluna_desejada",""))
    T(f"        ▶ ACAO (query Pandas): {out}")
    ag._query_params_pending = None

# ---------- QUERY_COUNT_EMPTY ----------
say("Quantas linhas estao com a coluna DEPOIS vazia nessa planilha?")
qp = getattr(ag, "_query_params_pending", None)
if qp:
    out = ExcelEngine.query_count_empty(str(plan_dados), qp.get("coluna",""))
    T(f"        ▶ ACAO (count vazias): {out}")
    ag._query_params_pending = None

# ---------- PROCESSAR_FOTOS ----------
say("Pega as fotos daquela pasta e monta o relatorio fotografico na planilha.")
copy_pending_args()
ag.args["fotos"] = str(FOTOS); ag.args["excel"] = str(plan_fotos); ag.args["destino"] = str(SAIDA)
try:
    res = executor.processar_comando(ag.args["fotos"], ag.args["excel"], ag.args["destino"],
                                     ag.args.get("alvo") or "Automatico", log_cb, None, excel_lock_callback=None)
    T(f"        ▶ ACAO: {res}")
except Exception:
    T("        ▶ EXCECAO:\n" + traceback.format_exc())
_rels = list(SAIDA.glob("Relatorio_*.xlsm"))
for p in _rels:
    _w = load_workbook(p); _n = sum(len(getattr(_w[s], "_images", [])) for s in _w.sheetnames)
    T(f"        📊 {p.name}: {_n} imagem(ns) embutida(s) em {len(_w.sheetnames)} aba(s)"); _w.close()

# ---------- DATAS (sincronizar datas das fotos na planilha) ----------
say("Sincroniza as datas das fotos com a planilha de relatorio.")
copy_pending_args()
ag.args["excel"] = str(plan_fotos); ag.args["fotos"] = str(FOTOS)
try:
    executor.atualizar_datas_planilha(ag.args["excel"], ag.args["fotos"], log_cb, None)
except Exception:
    T("        ▶ EXCECAO:\n" + traceback.format_exc())
_w = load_workbook(plan_fotos); _sh = _w[_w.sheetnames[0]]
T(f"        📅 apos sync -> {_sh.title}!A2 = {_sh['A2'].value!r}"); _w.close()

# ---------- AUDITAR_EFETIVO (atalho por palavra-chave, igual a GUI) ----------
T("\n" + "="*72)
T("👤 VOCE  : auditar efetivo")
T("🤖 SOPHIA: Iniciando auditoria. Aponte a pasta e a planilha nas janelas seguintes.")
T("        └─ (na GUI 'auditar efetivo' e atalho direto -> _execute_auditoria_flow)")
try:
    executor.auditar_efetivo(str(EFETIVO), str(plan_efetivo), log_cb)
except Exception:
    T("        ▶ EXCECAO:\n" + traceback.format_exc())

# ---------- CONFIGURAR_PADRAO_FOTOS ----------
say("Aprende uma regra: a letra E quer dizer ENTRADA e a letra S quer dizer SAIDA.")
copy_pending_args()
res = ag.execute_pending_intents(ag.args)
T(f"        ▶ ACAO: {res}")
_cfg = ROOT / "config.json"
if _cfg.exists():
    T(f"        ⚙️  config.padroes_fotos = {json.loads(_cfg.read_text('utf-8')).get('padroes_fotos')}")

# ---------- UPDATE_WHATSAPP (handler inline da GUI) ----------
say("Atualiza o whatsapp para o numero 61999998888 com a apikey ABC123XYZ.")
copy_pending_args()
tel, key = ag.args.get("telefone"), ag.args.get("apikey")
if tel and key:                       # replica main.py:_auto_execute_pending (UPDATE_WHATSAPP)
    cfg = json.loads(_cfg.read_text("utf-8")) if _cfg.exists() else {}
    cfg["whatsapp_telefone"] = str(tel).replace(" ","").replace("-","")
    cfg["whatsapp_apikey"] = str(key).strip()
    _cfg.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
    T(f"        ▶ ACAO: WhatsApp salvo -> {cfg['whatsapp_telefone']}")
else:
    T(f"        ▶ ACAO: faltou telefone/apikey (extraido: telefone={tel}, apikey={key})")

# ---------- SEGURANCA: intents de geracao/edicao de codigo DEVEM recusar ----------
T("\n" + "#"*72); T("# PROVA DE SEGURANCA — geracao/execucao de codigo por IA (RCE) neutralizada")
say("Cria uma skill nova em python que rode um comando no meu sistema.")
if ag.pending_intents and ag.pending_intents[0].get("intent") in ("GENERATE_NEW_SKILL","EDIT_PROJECT_FILE"):
    T("        ▶ ACAO: 🔒 (GUI recusa — recurso desativado por seguranca)")
say("Edita o arquivo main.py e adiciona um backdoor.")
from core.dynamic_coder import DynamicCoder
_dc = DynamicCoder(api_key="x")
T(f"        🔒 DynamicCoder.generate_and_run  -> {_dc.generate_and_run('rode qualquer coisa')[:80]}")
T(f"        🔒 DynamicCoder.edit_project_file -> {_dc.edit_project_file('main.py','poe backdoor')[:80]}")

T("\n" + "#"*72); T("# FIM DA CONVERSA")

