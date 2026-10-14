# -*- coding: utf-8 -*-
"""RECON somente-leitura de um MS Forms: renderiza no Edge headless, lê perguntas,
tira print. NAO preenche, NAO envia, NAO clica em nada."""
import io, sys, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE.parent))

URL = ("https://forms.cloud.microsoft/pages/responsepage.aspx?id=C7B9v8xt9EGBSIZTuz1lN8mqmt2-"
       "0_BIt9QpzkZI3y5UOEpNMDZBNUJPU1E1UlpYWkxDTk01Q0RKRy4u&route=shorturl")

from playwright.sync_api import sync_playwright
shot = BASE / "forms_real_view.png"
with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(locale="pt-BR").new_page()
    pg.set_default_timeout(30000)
    pg.goto(URL, wait_until="domcontentloaded")
    try:
        pg.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    pg.wait_for_timeout(2500)

    final_url = pg.url
    titulo = pg.title()
    host = final_url.split("/")[2] if "//" in final_url else final_url
    login = any(k in final_url.lower() for k in ["login.microsoftonline", "login.live", "/login", "signin"])

    # tenta varios seletores de titulo de pergunta (classico + variacoes novas)
    seletores = [".office-form-question-title", "[class*='question-title']",
                 "[class*='questionTitle']", "[class*='question_title']",
                 "div[role='heading']", "h2", "h3"]
    perguntas = pg.evaluate("""(sels) => {
        const out = [];
        for (const s of sels) {
            document.querySelectorAll(s).forEach(e => {
                const t = (e.innerText || '').trim();
                if (t && t.length > 1 && t.length < 200) out.push(t);
            });
            if (out.length) break;
        }
        return [...new Set(out)];
    }""", seletores)

    # contagem de controles preenchiveis
    controles = pg.evaluate("""() => ({
        textbox: document.querySelectorAll("input[type='text'], textarea, input:not([type])").length,
        radio: document.querySelectorAll("[role='radio'], input[type='radio']").length,
        checkbox: document.querySelectorAll("[role='checkbox'], input[type='checkbox']").length,
        combobox: document.querySelectorAll("[role='combobox'], select").length,
        botoes: [...document.querySelectorAll("button, [role='button']")].map(b=>(b.innerText||'').trim()).filter(Boolean).slice(0,10)
    })""")

    # dump curto do texto visivel (pra ver do que se trata)
    corpo = pg.evaluate("() => (document.body.innerText || '').trim().slice(0, 1200)")

    pg.screenshot(path=str(shot), full_page=True)
    b.close()

print("URL final :", final_url)
print("host      :", host)
print("titulo    :", titulo)
print("CAIU EM LOGIN?:", "SIM ⚠️ (precisa estar logado)" if login else "NAO — abriu o formulario")
print()
print("PERGUNTAS DETECTADAS (%d):" % len(perguntas))
for q in perguntas:
    print("   •", q.replace("\n", " / "))
print()
print("CONTROLES PREENCHIVEIS:", json.dumps(controles, ensure_ascii=False))
print()
print("TEXTO VISIVEL (inicio):")
print(corpo)
print()
print("PRINT salvo em:", shot if shot.exists() else "(falhou)")
