# -*- coding: utf-8 -*-
"""SONDAGEM SOMENTE-LEITURA das OPÇÕES de cada pergunta do formulário permanente.
Rola cada bloco até a viewport (força o MS Forms a renderizar as opções
virtualizadas) e LÊ o texto de cada 'bolinha'/campo. NÃO preenche, NÃO marca,
NÃO clica em opção, NÃO envia — só rola e lê."""
import io, sys, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

URL = ("https://forms.cloud.microsoft/pages/responsepage.aspx?id=C7B9v8xt9EGBSIZTuz1lN8mqmt2-"
       "0_BIt9QpzkZI3y5UOEpNMDZBNUJPU1E1UlpYWkxDTk01Q0RKRy4u&route=shorturl")

from playwright.sync_api import sync_playwright

JS = r"""(c) => {
  const resolve = (el) => {
    const al = el.getAttribute('aria-label'); if (al) return al.trim();
    const lb = el.getAttribute('aria-labelledby');
    if (lb) return lb.split(/\s+/).map(id => {
      const n = document.getElementById(id); return n ? (n.innerText||'').trim() : '';
    }).filter(Boolean).join(' ').trim();
    return '';
  };
  const tEl = c.querySelector("[class*='text-format-content'],[class*='question-title'],[role='heading'],label");
  const titulo = tEl ? (tEl.innerText||'').trim().replace(/\s+/g,' ') : (c.innerText||'').trim().slice(0,60);
  const radios = [...c.querySelectorAll("[role='radio'],input[type='radio']")];
  const opcoes = [...new Set(radios.map(resolve).filter(Boolean))];
  const texts = [...c.querySelectorAll("input[data-automation-id='textInput'],textarea,input[role='combobox']")]
                  .map(e => (e.getAttribute('placeholder')||e.getAttribute('aria-label')||'').trim());
  const combos = c.querySelectorAll("[role='combobox'],select").length;
  let tipo = 'desconhecido';
  if (radios.length) tipo = 'radio';
  else if (combos) tipo = 'combobox/date';
  else if (texts.length) tipo = 'texto';
  return {titulo, tipo, n_radio: radios.length, opcoes, campos_texto: texts};
}"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    pg = b.new_context(locale="pt-BR").new_page()
    pg.set_default_timeout(30000)
    pg.goto(URL, wait_until="domcontentloaded")
    try:
        pg.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    pg.wait_for_timeout(2000)
    boxes = pg.locator("[data-automation-id='questionItem']")
    n = boxes.count()
    out = []
    for i in range(n):
        bx = boxes.nth(i)
        try:
            bx.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        pg.wait_for_timeout(350)
        try:
            out.append(bx.evaluate(JS))
        except Exception as e:
            out.append({"erro": str(e)})
    b.close()

print("PERGUNTAS E OPÇÕES REAIS (%d):" % len(out))
print(json.dumps(out, ensure_ascii=False, indent=2))
