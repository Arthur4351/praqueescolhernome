import os
import re
import datetime
import uuid
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as ExcelImage
from PIL import Image as PILImage, ImageOps

class SophiaExecutor:
    def __init__(self):
        # Medida exata para manter a proporção de 10,6cm
        largura_px = int(10.6 * 37.795) 
        altura_px = int(6.22 * 37.795)  
        self.tamanho_foto = (largura_px, altura_px) 
        self.lista_temps = []
        self.reader = None

    def carregar_ocr(self, log_func):
        """Ativa o EasyOCR apenas quando necessário"""
        if self.reader is None:
            try:
                import easyocr
                log_func("🧠 SOPHIA: Ativando visão para leitura de carimbos...")
                self.reader = easyocr.Reader(['pt', 'en'], gpu=False)
            except Exception as e:
                log_func(f"⚠️ Erro ao carregar visão: {e}")

    def extrair_data_inteligente(self, pasta_raiz, log_func):
        """Descobre Mês e Ano lendo as fotos ou metadados"""
        extensoes = ("*.[jJ][pP][gG]", "*.[jJ][pP][eE][gG]", "*.[pP][nN][gG]")
        arquivos = []
        for ext in extensoes:
            arquivos.extend(list(Path(pasta_raiz).rglob(ext)))
        
        if not arquivos: return None

        self.carregar_ocr(log_func)
        if self.reader:
            for f in arquivos[:5]:
                try:
                    res = self.reader.readtext(str(f), detail=0)
                    texto = " ".join(res).upper()
                    match = re.search(r'(\d{1,2})[/\.](\d{1,2})[/\.](\d{2,4})', texto)
                    if match:
                        mes, ano = int(match.group(2)), int(match.group(3))
                        if ano < 100: ano += 2000
                        return {"mes": mes, "ano": ano}
                except: continue

        dt = datetime.datetime.fromtimestamp(arquivos[0].stat().st_mtime)
        return {"mes": dt.month, "ano": dt.year}

    def extrair_dia(self, valor):
        """Extrai o número do dia de uma data do Excel ou string"""
        if isinstance(valor, datetime.datetime): return str(valor.day)
        match = re.search(r'(\d{1,2})', str(valor))
        return str(int(match.group(1))) if match else None

    def preparar_foto(self, caminho_foto, destino_path):
        """Redimensiona a foto mantendo o padrão do seu projeto"""
        try:
            temp_path = Path(destino_path) / f"srv_{uuid.uuid4().hex[:6]}.png"
            with PILImage.open(caminho_foto) as img:
                img = ImageOps.exif_transpose(img) 
                img = img.resize(self.tamanho_foto, PILImage.LANCZOS)
                img.save(temp_path, "PNG")
            self.lista_temps.append(temp_path)
            return temp_path
        except: return None

    def atualizar_datas_planilha(self, excel_path, pasta_fotos, log_func):
        """Comando 'datas': Lê o mês/ano das fotos e atualiza a planilha"""
        try:
            log_func("📅 SOPHIA: Iniciando sincronização de datas...")
            info_data = self.extrair_data_inteligente(pasta_fotos, log_func)
            if not info_data:
                log_func("❌ Não detectei fotos para basear o mês.")
                return

            wb = load_workbook(excel_path, keep_vba=True)
            alteracoes = 0
            for nome_aba in wb.sheetnames:
                ws = wb[nome_aba]
                for r in range(1, 500):
                    for c in range(1, 15):
                        cell = ws.cell(row=r, column=c)
                        txt = str(cell.value).upper() if cell.value else ""
                        if "DATA" in txt:
                            for off in range(1, 6):
                                target = ws.cell(row=r, column=c+off)
                                dia = self.extrair_dia(target.value)
                                if dia:
                                    try:
                                        target.value = datetime.datetime(info_data['ano'], info_data['mes'], int(dia))
                                        target.number_format = 'DD/MM/YYYY'
                                        alteracoes += 1
                                    except: pass
                                    break
            wb.save(excel_path)
            log_func(f"✅ SUCESSO! {alteracoes} datas sincronizadas.")
        except Exception as e: log_func(f"❌ Erro em datas: {e}")

    def processar_comando(self, pasta_raiz_fotos, excel_path, destino_path, log_func):
        """Sua lógica original de inserção de fotos"""
        try:
            log_func("🚀 SOPHIA: Iniciando processamento...")
            raiz_fotos, destino_path = Path(pasta_raiz_fotos), Path(destino_path)
            if not destino_path.exists(): destino_path.mkdir(parents=True)

            cache_fotos = {}
            extensoes = ("*.[jJ][pP][gG]", "*.[jJ][pP][eE][gG]", "*.[pP][nN][gG]")
            for pasta in [d for d in raiz_fotos.iterdir() if d.is_dir()]:
                equipe = pasta.name.strip().upper()
                cache_fotos[equipe] = {}
                lista_f = []
                for ext in extensoes: lista_f.extend(list(pasta.glob(ext)))
                for f in lista_f:
                    m = re.search(r'(\d+)', f.stem)
                    if m:
                        dia = str(int(m.group(1)))
                        if dia not in cache_fotos[equipe]: cache_fotos[equipe][dia] = {}
                        tipo = 'depois' if '+' in f.stem else 'antes'
                        cache_fotos[equipe][dia][tipo] = self.preparar_foto(f, destino_path)

            wb = load_workbook(excel_path, keep_vba=True)
            fotos_total = 0
            for nome_aba in wb.sheetnames:
                aba_key = nome_aba.strip().upper()
                if aba_key not in cache_fotos: continue
                ws = wb[nome_aba]
                dia_atual = None
                for r in range(1, 800):
                    for c in range(1, 15):
                        cell = ws.cell(row=r, column=c)
                        txt = str(cell.value).upper() if cell.value else ""
                        if "DATA" in txt:
                            for off in range(1, 6):
                                val = ws.cell(row=r, column=c+off).value
                                if val: dia_atual = self.extrair_dia(val); break
                        
                        if dia_atual and dia_atual in cache_fotos[aba_key]:
                            fots = cache_fotos[aba_key][dia_atual]
                            if "SERVIÇO 01" in txt and 'antes' in fots:
                                ws.add_image(ExcelImage(fots['antes']), ws.cell(row=r+1, column=c).coordinate)
                                fotos_total += 1
                            elif "SERVIÇO 02" in txt and 'depois' in fots:
                                ws.add_image(ExcelImage(fots['depois']), ws.cell(row=r+1, column=c).coordinate)
                                fotos_total += 1
            
            if fotos_total > 0:
                final_path = destino_path / f"Relatorio_Finalizado_{uuid.uuid4().hex[:4]}.xlsm"
                wb.save(final_path)
                log_func(f"✅ SUCESSO! {fotos_total} fotos inseridas.")
            
            for t in self.lista_temps: 
                if t.exists(): os.remove(t)
            self.lista_temps.clear()
        except Exception as e: log_func(f"❌ Erro: {e}")