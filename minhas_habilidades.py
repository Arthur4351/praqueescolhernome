import os, re, gc, datetime, uuid, io, concurrent.futures, difflib
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as ExcelImage
from PIL import Image as PILImage, ImageOps, ImageEnhance
from core.metadata_inspector import MetadataInspector
from core.ocr_engine import OCREngine
import pandas as pd
from core.file_handler import FileHandler

class UnclosableBytesIO(io.BytesIO):
    def close(self): pass

class SophiaExecutor:
    def __init__(self):
        self.tamanho_foto = (100, 100)
        self._ocr_disponivel = OCREngine.is_available()

    def definir_dimensoes(self, largura_cm, altura_cm):
        self.tamanho_foto = (int(largura_cm * 37.795), int(altura_cm * 37.795))

    def extrair_dia(self, valor):
        if isinstance(valor, datetime.datetime): return str(valor.day)
        m = re.search(r'(\d{1,2})', str(valor))
        return str(int(m.group(1))) if m else None

    def preparar_foto(self, caminho_foto, extrair_ocr=False):
        try:
            selo = None
            if extrair_ocr and self._ocr_disponivel:
                with open(caminho_foto, "rb") as f: selo = OCREngine.extract_stamp_from_bytes(f.read())
            img_io = UnclosableBytesIO()
            with PILImage.open(caminho_foto) as img:
                img = ImageOps.exif_transpose(img)
                if extrair_ocr:
                    img = ImageEnhance.Contrast(img.convert('L')).enhance(2.0)
                img.resize(self.tamanho_foto, PILImage.LANCZOS).save(img_io, format="PNG")
            img_io.seek(0)
            gc.collect()
            return img_io, selo
        except: return None, None

    def atualizar_datas_planilha(self, excel_path, pasta_fotos, log_func):
        try:
            wb = load_workbook(excel_path, keep_vba=True)
            for nome_aba in wb.sheetnames:
                ws = wb[nome_aba]
                for img in getattr(ws, '_images', []):
                    try: OCREngine.extract_stamp_from_bytes(io.BytesIO(img.ref.read()).getvalue())
                    except: pass
                gc.collect()
            try: wb.save(excel_path)
            except PermissionError: log_func('❌ ERRO: Feche o Excel!')
            wb.close()
            gc.collect()
        except: pass

    def _injetar_foto_segura(self, ws, img_io, r, c):
        if not c: return 0
        ws.add_image(ExcelImage(img_io), ws.cell(row=r, column=c).coordinate)
        gc.collect()
        return 1

    def _injetar_km_dinamico(self, ws, r_base, selo, tipo):
        if not selo or not selo.get('km'): return
        km_cols = []
        for r_atual in range(max(1, r_base - 2), r_base + 6):
            for c in range(1, ws.max_column + 1):
                v = ws.cell(row=r_atual, column=c).value
                if not v: continue
                vn = str(v).upper().replace(" ", "")
                if 'KM' in vn or 'HODOMETRO' in vn: km_cols.append((r_atual, c))
        if not km_cols: return
        km_cols.sort(key=lambda x: (x[0], x[1]))
        t_cell = km_cols[0] if tipo == 'INICIAL' or len(km_cols) == 1 else km_cols[1]
        try: ws.cell(row=t_cell[0], column=t_cell[1] + 1).value = int(selo['km'])
        except: ws.cell(row=t_cell[0], column=t_cell[1] + 1).value = selo['km']

    def processar_comando(self, pasta_raiz_fotos, excel_path, destino_path, nome_usuario, log_func):
        try:
            destino_path = Path(destino_path)
            if not destino_path.exists(): destino_path.mkdir(parents=True)
            cache = {}
            tasks = []
            for pasta in [d for d in Path(pasta_raiz_fotos).iterdir() if d.is_dir()]:
                eq = pasta.name.strip().upper()
                cache[eq] = {}
                for f in list(pasta.rglob("*.[jJ][pP]*[gG]")) + list(pasta.rglob("*.[pP][nN][gG]")):
                    nm = f.stem.upper()
                    m = re.search(r'(\d+)', nm)
                    if not m: continue
                    dia = str(int(m.group(1)))
                    if dia not in cache[eq]: cache[eq][dia] = {}
                    t = 'ENTRADA' if re.search(r'\bE\b|\bENTRADA\b', nm) else 'SAIDA' if re.search(r'\bS\b|\bSAIDA\b', nm) else 'ANTES' if re.search(r'\bA\b|\(A\)|\bANTES\b', nm) else 'DEPOIS' if re.search(r'\bD\b|\(D\)|\bDEPOIS\b|\(2\)', nm) else None
                    if not t: t = 'ANTES' if 'ANTES' not in cache[eq][dia] else 'DEPOIS'
                    tasks.append((eq, dia, t, f, t in ['ENTRADA','SAIDA']))
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 1)) as pool:
                future_to_task = {pool.submit(self.preparar_foto, tk[3], tk[4]): tk for tk in tasks}
                for future in concurrent.futures.as_completed(future_to_task):
                    tk = future_to_task[future]
                    res = future.result()
                    if res and res[0]: cache[tk[0]][tk[1]][tk[2]] = {'p': res[0], 's': res[1]}
            wb = load_workbook(excel_path, keep_vba=True)
            fotos_total = 0
            relatorio_faltas = []
            for nm_aba in wb.sheetnames:
                aba = nm_aba.strip().upper()
                if aba not in cache: continue
                ws = wb[nm_aba]
                dia_atual = None
                max_r = ws.max_row + 1
                max_c = min(ws.max_column + 1, 200)
                linhas_em_branco_seguidas = 0
                for r in range(1, max_r):
                    linha_tem_dados = False
                    for c in range(1, max_c):
                        v = ws.cell(row=r, column=c).value
                        if not v: continue
                        linha_tem_dados = True
                        v_norm = str(v).upper().replace(" ", "").replace(".", "").replace("Ç", "C")
                        if 'DATA' in v_norm or 'DIA' in v_norm:
                            for off in range(1, 6):
                                if c + off >= max_c: break
                                v_off = ws.cell(row=r, column=c+off).value
                                if v_off:
                                    d = self.extrair_dia(v_off)
                                    if d: dia_atual = d; break
                        if dia_atual and dia_atual in cache[aba]:
                            fots = cache[aba][dia_atual]
                            if not fots.get('_verificado'): fots['_verificado'] = True
                            match_antes = any(m in v_norm for m in ['ANTES', 'SERVICO01', 'FOTODEANTES', 'ATIVIDADEREALISADA', 'ATIVIDADEREALIZADA'])
                            match_depois = any(m in v_norm for m in ['DEPOIS', 'SERVICO02', 'FOTODEDEPOIS', 'ATIVIDADEREALISADA', 'ATIVIDADEREALIZADA'])
                            if any(m in v_norm for m in ['FOTO01', 'ENTRADA', 'FOTODEENTRADA']):
                                if 'ENTRADA' in fots and not fots['ENTRADA'].get('_injetada'):
                                    fots['ENTRADA']['p'].seek(0)
                                    fotos_total += self._injetar_foto_segura(ws, fots['ENTRADA']['p'], r+1, c)
                                    fots['ENTRADA']['_injetada'] = True
                                    self._injetar_km_dinamico(ws, r, fots['ENTRADA']['s'], 'INICIAL')
                            elif any(m in v_norm for m in ['FOTO02', 'SAIDA', 'SAÍDA', 'FOTODESAIDA']):
                                if 'SAIDA' in fots and not fots['SAIDA'].get('_injetada'):
                                    fots['SAIDA']['p'].seek(0)
                                    fotos_total += self._injetar_foto_segura(ws, fots['SAIDA']['p'], r+1, c)
                                    fots['SAIDA']['_injetada'] = True
                                    self._injetar_km_dinamico(ws, r, fots['SAIDA']['s'], 'FINAL')
                            elif match_antes and 'ANTES' in fots and not fots['ANTES'].get('_injetada'):
                                fots['ANTES']['p'].seek(0)
                                fotos_total += self._injetar_foto_segura(ws, fots['ANTES']['p'], r+1, c)
                                fots['ANTES']['_injetada'] = True
                            elif match_depois and 'DEPOIS' in fots and not fots['DEPOIS'].get('_injetada'):
                                fots['DEPOIS']['p'].seek(0)
                                fotos_total += self._injetar_foto_segura(ws, fots['DEPOIS']['p'], r+1, c)
                                fots['DEPOIS']['_injetada'] = True
                    if not linha_tem_dados:
                        linhas_em_branco_seguidas += 1
                        if linhas_em_branco_seguidas >= 50: break
                    else: linhas_em_branco_seguidas = 0
            for aba, dias_cache in cache.items():
                for dia, fots in dias_cache.items():
                    if not fots.get('_verificado'): relatorio_faltas.append(f"Aba {aba} | Dia {dia}: ❌ Nao na planilha.")
                    else:
                        faltas = [tipo for tipo in ['ENTRADA', 'SAIDA', 'ANTES', 'DEPOIS'] if tipo not in fots]
                        if faltas: relatorio_faltas.append(f"Aba {aba} | Dia {dia}: ⚠️ Faltam: {', '.join(faltas)}.")
            if relatorio_faltas:
                log_func("⚠️ LOG DE ERROS ⚠️")
                for falta in relatorio_faltas: log_func(f" {falta}")
            if fotos_total > 0:
                try: 
                    wb.save(destino_path / f"Relatorio_{uuid.uuid4().hex[:4]}.xlsm")
                    log_func(f"✅ SUCESSO! {fotos_total} fotos injetadas.")
                except PermissionError: log_func('❌ ERRO: Feche o Excel!')
            wb.close()
            gc.collect()
        except Exception as e:
            log_func(f"❌ Erro Crítico: {e}")

    def auditar_efetivo(self, pasta_efetivo: str, excel_path: str, log_func):
        try:
            pastas_fisicas = [FileHandler.normalize_string(p.name) for p in Path(pasta_efetivo).iterdir()]
            df = pd.read_excel(excel_path, engine='openpyxl', dtype=str)
            colunas_possiveis = [c for c in df.columns if any(k in str(c).lower() for k in ['nome', 'funcionario', 'equipe', 'colaborador'])]
            coluna_alvo = colunas_possiveis[0] if colunas_possiveis else df.columns[0]
            nomes_excel = [FileHandler.normalize_string(str(x)) for x in df[coluna_alvo].dropna().unique()]
            del df; gc.collect()
            faltam_no_excel = []
            faltam_na_pasta = []
            def contains_fuzzy(nome, lista):
                for n in lista:
                    if nome in n or n in nome or difflib.SequenceMatcher(None, nome, n).ratio() > 0.8: return True
                return False
            for p in pastas_fisicas:
                if not contains_fuzzy(p, nomes_excel): faltam_no_excel.append(p.title())
            for n in nomes_excel:
                if not contains_fuzzy(n, pastas_fisicas) and len(n) > 2: faltam_na_pasta.append(n.title())
            log_func("<br><b>=== RESULTADO DA AUDITORIA ===</b><br>")
            if faltam_no_excel:
                log_func("⚠️ <b>Na Pasta, mas NÃO no Excel:</b><br>" + "<br>".join(faltam_no_excel) + "<br>")
            if faltam_na_pasta:
                log_func("❌ <b>No Excel, mas NÃO mandou a pasta:</b><br>" + "<br>".join(faltam_na_pasta) + "<br>")
            if not faltam_no_excel and not faltam_na_pasta:
                log_func("✅ <b>Tudo 100% batendo! Nenhum GAP encontrado.</b>")
        except Exception as e:
            gc.collect()
            log_func(f"❌ Erro na auditoria: {e}")