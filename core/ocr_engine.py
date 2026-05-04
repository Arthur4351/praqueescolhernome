import sys, os, re, gc, io
from PIL import Image, ImageEnhance, ImageOps

if getattr(sys, 'frozen', False): _BASE_DIR = sys._MEIPASS
else: _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_TESSERACT_PATH = os.path.join(_BASE_DIR, 'bin', 'tesseract', 'tesseract.exe')
_FALLBACK_PATHS = [r'C:\Program Files\Tesseract-OCR\tesseract.exe', r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe']

class OCREngine:
    _initialized, _available = False, False

    @classmethod
    def _init_tesseract(cls):
        if cls._initialized: return cls._available
        cls._initialized = True
        try:
            import pytesseract
            if os.path.isfile(_TESSERACT_PATH):
                pytesseract.pytesseract.tesseract_cmd = _TESSERACT_PATH
                cls._available = True; return True
            for path in _FALLBACK_PATHS:
                if os.path.isfile(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    cls._available = True; return True
            try: pytesseract.get_tesseract_version(); cls._available = True; return True
            except: pass
            cls._available = False; return False
        except: cls._available = False; return False

    @staticmethod
    def extract_stamp_data(image_path: str) -> dict:
        try:
            with open(image_path, "rb") as f: return OCREngine.extract_stamp_from_bytes(f.read())
        except: gc.collect(); return {"data": None, "hora": None, "km": None}

    @staticmethod
    def extract_stamp_from_bytes(image_bytes: bytes) -> dict:
        res = {"data": None, "hora": None, "km": None}
        if not OCREngine._init_tesseract(): return res
        try:
            import pytesseract
            with Image.open(io.BytesIO(image_bytes)) as img:
                img_g = img.convert('L')
                try: img_i = ImageOps.invert(img_g)
                except: img_i = img_g
                img_e = ImageEnhance.Contrast(img_i).enhance(2.0)
                txt = pytesseract.image_to_string(img_e)
                del img_g, img_i, img_e
            if not txt: gc.collect(); return res
            md = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})', txt)
            if md:
                ano = f"20{md.group(3)}" if len(md.group(3))==2 else md.group(3)
                res["data"] = f"{md.group(1).zfill(2)}/{md.group(2).zfill(2)}/{ano}"
            mh = re.search(r'(\d{1,2}):(\d{2})', txt)
            if mh: res["hora"] = f"{mh.group(1).zfill(2)}:{mh.group(2)}"
            mk = re.search(r'(?:KM|HODOMETRO)[\s:\-]*(\d[\d.,]*)', txt, re.IGNORECASE)
            if not mk:
                nums = re.findall(r'\b(\d{4,6})\b', txt)
                if nums: res["km"] = str(max([int(n) for n in nums]))
            else: res["km"] = mk.group(1).replace('.', '').replace(',', '')
            del txt; gc.collect()
        except: gc.collect()
        return res

    @staticmethod
    def is_available() -> bool: return OCREngine._init_tesseract()
