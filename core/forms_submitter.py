"""
core/forms_submitter.py

Preenchedor de formulários (Microsoft Forms / formulários web) guiado por uma
PLANILHA DE REFERÊNCIA. A planilha diz, linha a linha, QUAL pergunta preencher e
O QUE escrever ou marcar; ao final é gerado um PDF do formulário preenchido.

AUTOSSUFICIENTE NO PC CORPORATIVO:
- Usa o Microsoft Edge JÁ instalado no Windows (channel="msedge"): NÃO baixa
  Chromium nem exige instalar navegador. O driver do Playwright é embutido no .exe
  em tempo de build (como o Tesseract), não em tempo de execução.
- Se Playwright/Edge não estiverem disponíveis, degrada com mensagem honesta (sem crash).
- O import do Playwright é adiado para dentro dos métodos: importar este módulo
  NUNCA quebra a aplicação, mesmo sem o Playwright instalado.

Formato da planilha de referência (1ª aba):
  Coluna A: PERGUNTA  (título da pergunta como aparece no formulário)
  Coluna B: TIPO      (opcional: texto|data|opcao|dropdown|checkbox — autodetecta se vazio)
  Coluna C: VALOR     (o que escrever, ou o rótulo da opção a marcar; várias com ';')
Linha especial: PERGUNTA em {URL, LINK, FORMULARIO} -> VALOR = link do formulário.
"""
import os
import re
from datetime import datetime

# Chaves que, na coluna PERGUNTA, indicam a URL do formulário em vez de um campo.
_URL_KEYS = {"URL", "LINK", "FORMULARIO", "FORMULÁRIO", "FORM"}
# Caminhos padrão do Microsoft Edge (componente de 1ª parte do Windows corporativo).
_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


class FormsSubmitter:
    def __init__(self, output_dir="relatorios"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Disponibilidade (degrada com honestidade, nunca quebra o app)
    # ------------------------------------------------------------------ #
    @staticmethod
    def is_available():
        """Retorna (ok: bool, motivo: str). Não importa o Playwright de fato."""
        import importlib.util
        if importlib.util.find_spec("playwright") is None:
            return False, "Playwright não disponível — recurso de Forms desativado nesta instalação."
        if not any(os.path.isfile(p) for p in _EDGE_PATHS):
            return False, "Microsoft Edge não encontrado neste computador."
        return True, "OK"

    # ------------------------------------------------------------------ #
    # Leitura da planilha de referência (Python puro — testável offline)
    # ------------------------------------------------------------------ #
    @staticmethod
    def parse_reference_sheet(xlsx_path):
        """Lê a planilha e devolve {'url': str|None, 'campos': [{pergunta,tipo,valor}]}."""
        from openpyxl import load_workbook
        wb = load_workbook(xlsx_path, data_only=True, read_only=True)
        ws = wb.active
        url = None
        campos = []
        for row in ws.iter_rows(values_only=True):
            if not row:
                continue
            pergunta = str(row[0]).strip() if row[0] is not None else ""
            if not pergunta:
                continue
            tipo = str(row[1]).strip().lower() if len(row) > 1 and row[1] is not None else ""
            valor = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
            chave = pergunta.upper().rstrip(":").strip()
            # linha de configuração da URL
            if chave in _URL_KEYS:
                url = valor or (row[1] if len(row) > 1 and row[1] else None)
                url = str(url).strip() if url else None
                continue
            # ignora um cabeçalho literal "PERGUNTA | TIPO | VALOR"
            if chave == "PERGUNTA" and valor.upper() in ("VALOR", "RESPOSTA", ""):
                continue
            campos.append({"pergunta": pergunta, "tipo": tipo, "valor": valor})
        wb.close()
        return {"url": url, "campos": campos}

    # ------------------------------------------------------------------ #
    # Preenche o formulário a partir da planilha e gera o PDF
    # ------------------------------------------------------------------ #
    def fill_from_spreadsheet(self, xlsx_path, url=None, submit=False, log=None, timeout_ms=15000):
        """Abre o formulário no Edge, preenche/marca conforme a planilha e salva um PDF.

        Retorna {'ok', 'pdf', 'msg', 'preenchidos', 'faltas'}.
        """
        log = log or (lambda m: None)
        ok, motivo = self.is_available()
        if not ok:
            return {"ok": False, "pdf": None, "msg": f"🔒 {motivo}", "preenchidos": 0, "faltas": []}

        plano = self.parse_reference_sheet(xlsx_path)
        alvo = (url or plano.get("url") or "").strip()
        campos = plano.get("campos", [])
        if not alvo:
            return {"ok": False, "pdf": None, "msg": "❌ Sem URL do formulário (defina 'URL' na planilha ou passe o link).", "preenchidos": 0, "faltas": []}
        if not campos:
            return {"ok": False, "pdf": None, "msg": "❌ A planilha de referência não tem campos para preencher.", "preenchidos": 0, "faltas": []}

        from playwright.sync_api import sync_playwright
        pdf_path = os.path.join(self.output_dir, f"Forms_{datetime.now():%Y%m%d_%H%M%S}.pdf")
        preenchidos, faltas = 0, []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=True)
                page = browser.new_context().new_page()
                page.set_default_timeout(timeout_ms)
                page.goto(alvo, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                for campo in campos:
                    try:
                        if self._preencher_campo(page, campo):
                            preenchidos += 1
                            log(f"✅ '{campo['pergunta']}' → {campo['valor'] or '(marcado)'}")
                        else:
                            faltas.append(campo["pergunta"])
                            log(f"⚠️ campo não localizado: '{campo['pergunta']}'")
                    except Exception as e:
                        faltas.append(campo["pergunta"])
                        log(f"⚠️ erro em '{campo['pergunta']}': {e}")
                page.wait_for_timeout(400)
                page.pdf(path=pdf_path, print_background=True)
                if submit:
                    try:
                        page.get_by_role("button", name=re.compile(r"enviar|submit", re.I)).first.click()
                        page.get_by_text(re.compile(r"resposta foi enviada|response was submitted", re.I)).wait_for()
                        log("📨 Formulário enviado.")
                    except Exception as e:
                        log(f"⚠️ PDF gerado, mas não consegui enviar: {e}")
                browser.close()
            return {"ok": True, "pdf": pdf_path,
                    "msg": f"📄 PDF gerado ({preenchidos}/{len(campos)} campos preenchidos). Faltas: {faltas or 'nenhuma'}",
                    "preenchidos": preenchidos, "faltas": faltas}
        except Exception as e:
            return {"ok": False, "pdf": None, "msg": f"❌ Falha ao operar o Edge: {e}", "preenchidos": preenchidos, "faltas": faltas}

    # ------------------------------------------------------------------ #
    # Localiza e preenche/marca UM campo (resiliente: MS Forms e HTML genérico)
    # ------------------------------------------------------------------ #
    def _preencher_campo(self, page, campo):
        t = (campo.get("pergunta") or "").strip()
        tp = (campo.get("tipo") or "").lower().strip()
        v = (campo.get("valor") or "").strip()
        rx_t = re.compile(re.escape(t), re.I)

        def try_text():
            if not v:
                return False
            # 1) rótulo acessível (label for=, aria-label, aria-labelledby)
            try:
                loc = page.get_by_label(rx_t)
                if loc.count() and loc.first.is_visible():
                    el = loc.first
                    if (el.evaluate("e => e.tagName") or "").lower() == "select":
                        el.select_option(label=v)
                    else:
                        el.fill(v)
                    return True
            except Exception:
                pass
            # 2) aria-label parcial
            try:
                loc = page.locator(f'input[aria-label*="{t}"], textarea[aria-label*="{t}"]')
                if loc.count():
                    loc.first.fill(v)
                    return True
            except Exception:
                pass
            # 3) MS Forms: título da pergunta -> input dentro do bloco
            try:
                box = page.locator('.office-form-question-title', has_text=rx_t).locator('..')
                inp = box.locator('input[type="text"], textarea, input:not([type])')
                if inp.count():
                    inp.first.fill(v)
                    return True
            except Exception:
                pass
            return False

        def try_choice(role):
            if not v:
                return False
            opcoes = [x.strip() for x in v.split(";") if x.strip()] or [v]
            marcou = False
            for opt in opcoes:
                rx_o = re.compile(re.escape(opt), re.I)
                feito = False
                try:
                    loc = page.get_by_role(role, name=rx_o)
                    if loc.count():
                        loc.first.check()
                        feito = True
                except Exception:
                    pass
                if not feito:
                    try:
                        lbl = page.locator("label", has_text=rx_o)
                        if lbl.count():
                            lbl.first.click()
                            feito = True
                    except Exception:
                        pass
                marcou = marcou or feito
            return marcou

        def try_dropdown():
            if not v:
                return False
            try:  # <select> nativo por rótulo
                loc = page.get_by_label(rx_t)
                if loc.count() and (loc.first.evaluate("e => e.tagName") or "").lower() == "select":
                    loc.first.select_option(label=v)
                    return True
            except Exception:
                pass
            try:  # combobox estilo MS Forms
                box = page.locator('.office-form-question-title', has_text=rx_t).locator('..')
                box.locator('[role="combobox"], [role="listbox"], i[data-icon-name="ChevronDown"]').first.click()
                page.wait_for_timeout(300)
                page.locator('[role="option"], .ms-Dropdown-item').filter(
                    has_text=re.compile(re.escape(v), re.I)).first.click()
                return True
            except Exception:
                pass
            return False

        if tp in ("texto", "text", "data", "date", "numero", "número", "number"):
            return try_text()
        if tp in ("opcao", "opção", "radio", "escolha", "unica", "única"):
            return try_choice("radio") or try_choice("checkbox")
        if tp in ("checkbox", "caixa", "multipla", "múltipla", "marcar"):
            return try_choice("checkbox") or try_choice("radio")
        if tp in ("dropdown", "lista", "select", "combo", "combobox"):
            return try_dropdown()
        # autodetecção: texto -> radio -> checkbox -> dropdown
        return try_text() or try_choice("radio") or try_choice("checkbox") or try_dropdown()

