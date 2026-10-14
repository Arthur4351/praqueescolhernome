# -*- coding: utf-8 -*-
"""SONDAGEM SOMENTE-LEITURA do DOM do formulario PERMANENTE.
Abre no Edge headless, LE a estrutura de cada bloco de pergunta (titulo + controles
com seus atributos) para eu adaptar os seletores de forma generica.
NAO preenche, NAO envia, NAO clica em nada."""
import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from pathlib import Path
BASE = Path(__file__).resolve().parent

URL = ("https://forms.cloud.microsoft/pages/responsepage.aspx?id=C7B9v8xt9EGBSIZTuz1lN8mqmt2-"
       "0_BIt9QpzkZI3y5UOEpNMDZBNUJPU1E1UlpYWkxDTk01Q0RKRy4u&route=shorturl")

from playwright.sync_api import sync_playwright
shot = BASE / "forms_dom_probe.png"
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
    login = any(k in final_url.lower() for k in ["login.microsoftonline", "login.live", "/login", "signin"])

    # 1) quantos elementos cada seletor de CONTAINER de pergunta acha
    cont_sel = ["[data-automation-id='questionItem']", "[class*='question']",
                "[class*='Question']", "div[role='listitem']", "[role='group']"]
    cont_counts = pg.evaluate("""(sels) => Object.fromEntries(
        sels.map(s => [s, document.querySelectorAll(s).length]))""", cont_sel)

    # 2) estrutura dos primeiros blocos de pergunta: titulo + controles internos c/ atributos
    estrutura = pg.evaluate("""() => {
        const pick = (el, attrs) => Object.fromEntries(
            attrs.map(a => [a, el.getAttribute(a)]).filter(([,v]) => v != null));
        // acha os containers mais provaveis de "uma pergunta"
        let conts = [...document.querySelectorAll("[data-automation-id='questionItem']")];
        if (!conts.length) conts = [...document.querySelectorAll("[class*='question-item'],[class*='questionItem'],[class*='question_item']")];
        if (!conts.length) conts = [...document.querySelectorAll("div[role='listitem']")];
        const out = [];
        for (const c of conts.slice(0, 14)) {
            // titulo: 1o descendente com cara de titulo
            const tEl = c.querySelector("[class*='question-title'],[class*='questionTitle'],[class*='text-format-content'],[role='heading'],h2,h3,label");
            const titulo = tEl ? (tEl.innerText||'').trim().slice(0,120) : null;
            const ctrls = [...c.querySelectorAll("input,textarea,select,[role='radio'],[role='checkbox'],[role='combobox'],[role='textbox']")]
                .slice(0, 8).map(e => ({
                    tag: e.tagName.toLowerCase(),
                    ...pick(e, ["type","role","aria-label","aria-labelledby","placeholder","data-automation-id","name"])
                }));
            out.push({
                container_class: (c.className||'').toString().slice(0,90),
                data_automation_id: c.getAttribute('data-automation-id'),
                titulo, controles: ctrls
            });
        }
        return out;
    }""")

    # 3) contagem global de controles (sanity)
    controles = pg.evaluate("""() => ({
        textbox: document.querySelectorAll("input[type='text'],textarea,input:not([type]),[role='textbox']").length,
        radio: document.querySelectorAll("[role='radio'],input[type='radio']").length,
        checkbox: document.querySelectorAll("[role='checkbox'],input[type='checkbox']").length,
        combobox: document.querySelectorAll("[role='combobox'],select").length
    })""")

    pg.screenshot(path=str(shot), full_page=True)
    b.close()

print("URL final     :", final_url)
print("CAIU EM LOGIN?:", "SIM (precisa login)" if login else "NAO (form publico)")
print("\nCONTAGEM DE CONTAINERS por seletor:")
print(json.dumps(cont_counts, ensure_ascii=False, indent=2))
print("\nCONTROLES GLOBAIS:", json.dumps(controles, ensure_ascii=False))
print("\nESTRUTURA DOS BLOCOS DE PERGUNTA (%d):" % len(estrutura))
print(json.dumps(estrutura, ensure_ascii=False, indent=2))
print("\nPRINT:", shot if shot.exists() else "(falhou)")
