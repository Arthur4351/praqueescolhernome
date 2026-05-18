import os
import re
import time
from playwright.sync_api import sync_playwright

class FormsSubmitter:
    def __init__(self, output_dir="relatorios"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def submit_forms(self, data_str, escopo, interdicao, kms, test_mode=False):
        """
        Preenche os formulários usando Playwright.
        Retorna uma lista de caminhos dos PDFs gerados.
        """
        url = "https://forms.office.com/pages/responsepage.aspx?id=C7B9v8xt9EGBSIZTuz1lN8mqmt2-0_BIt9QpzkZI3y5UOEpNMDZBNUJPU1E1UlpYWkxDTk01Q0RKRy4u&route=shorturl"
        pdfs_gerados = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            for km in kms:
                km = str(km).strip()
                km_final = str(int(km) + 1)
                print(f"Preenchendo forms para KM {km} a {km_final}...")
                
                page.goto(url, wait_until="networkidle")
                time.sleep(2)
                
                # Helper function to open dropdowns
                def select_dropdown(title, search_text):
                    # Localiza o bloco da pergunta pelo título e clica no combobox (Select your answer)
                    box = page.locator('.office-form-question-title', has_text=title).locator('..')
                    box.locator('[role="combobox"], [role="listbox"], i[data-icon-name="ChevronDown"]').first.click()
                    time.sleep(0.5)
                    # Clica na opção
                    page.locator('.ms-Dropdown-item, .ms-ComboBox-option, [role="option"]').filter(has_text=re.compile(search_text, re.IGNORECASE)).first.click()
                
                # 1. Empresa (Dropdown)
                select_dropdown("EMPRESA", r"Guaran")
                
                # 2. Coordenador (Dropdown)
                select_dropdown("COORDENADOR CONTRATO", r"Bruno")
                
                # 3. Data
                page.locator('input[aria-label="DATA DO SERVIÇO"]').fill(data_str)
                
                # 4. Horário (Dropdown)
                select_dropdown("HORÁRIO DO SERVIÇO", r"Diurno")
                
                # 5. Escopo (Radio ou Dropdown - A lista de opções apareceu no dump)
                try:
                    page.get_by_role("radio", name=re.compile(escopo, re.IGNORECASE)).click(timeout=2000)
                except:
                    select_dropdown("ESCOPO SERVIÇO", escopo)
                
                # Sentido (Norte/Sul) -> Radio
                page.locator('label', has_text=re.compile(r"n/s|norte/sul", re.IGNORECASE)).first.click()
                
                # Interdição -> Dropdown ou Radio
                try:
                    page.get_by_role("radio", name=re.compile(interdicao, re.IGNORECASE)).click(timeout=2000)
                except:
                    select_dropdown("INTERDIÇÃO", interdicao)
                
                # Contorno Mestre Alvaro (NAO) e Iconha (NAO)
                # Como existem múltiplos "NÃO", clicamos em todos os labels que contém "NÃO"
                nao_labels = page.locator('label', has_text=re.compile(r"^n.o$", re.IGNORECASE))
                count_nao = nao_labels.count()
                for i in range(count_nao):
                    nao_labels.nth(i).click()
                
                # Preencher Data (Geralmente é um input focado clicando no calendário, ou digitando no input)
                # O placeholder de data no MS Forms em português costuma ser "Formato M/d/aaaa" ou "Insira a data"
                # Podemos buscar pelo texto ou apenas usar os inputs de texto genéricos.
                # No Forms, campos de texto têm aria-label correspondente ao título.
                page.locator('input[aria-label="DATA DO SERVIÇO"]').fill(data_str)
                
                # Preencher KMs
                page.locator('input[aria-label="KM INICIAL"]').fill(km)
                page.locator('input[aria-label="KM FINAL"]').fill(km_final)
                
                # Esperar 1 segundo para visualização
                time.sleep(1)
                
                # Gerar PDF *antes* de enviar
                pdf_filename = f"Forms_KM_{km}_{km_final}.pdf"
                pdf_path = os.path.join(self.output_dir, pdf_filename)
                page.pdf(path=pdf_path, print_background=True)
                pdfs_gerados.append(pdf_path)
                print(f"PDF salvo: {pdf_path}")
                
                if not test_mode:
                    # Encontrar e clicar no botão Enviar (Submit)
                    page.get_by_role("button", name=re.compile(r"Enviar|Submit", re.IGNORECASE)).click()
                    # Esperar pela tela de sucesso
                    page.get_by_text(re.compile(r"Sua resposta foi enviada|Your response was submitted", re.IGNORECASE)).wait_for()
                    print(f"Enviado com sucesso para KM {km}.")
                else:
                    print(f"[TEST MODE] Botão Enviar ignorado para KM {km}.")
                
            browser.close()
            return pdfs_gerados
