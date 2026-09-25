import os
from PIL import Image
from PIL.ExifTags import TAGS
import datetime
from core.file_handler import FileHandler

class MetadataInspector:
    @staticmethod
    def extract_full_metadata(image_path: str) -> dict:
        """Extrai Data, Hora e Modelo da Camera via EXIF, com fallback no relógio do SO.

        Prioriza DateTimeOriginal (quando a foto foi TIRADA) sobre DateTime (última
        edição). DateTimeOriginal fica no sub-IFD Exif (0x8769), que NÃO aparece no
        getexif() base — por isso é lido separadamente."""
        info = {"data": "Desconhecida", "hora": "Desconhecida", "camera": "Desconhecida"}
        try:
            with Image.open(image_path) as img:
                exif_data = img.getexif()
                if exif_data:
                    # IFD0 (base): DateTime, Make, Model
                    base = {TAGS.get(tid, tid): val for tid, val in exif_data.items()}
                    # Sub-IFD Exif (0x8769): DateTimeOriginal, DateTimeDigitized
                    sub = {}
                    try:
                        sub_ifd = exif_data.get_ifd(0x8769)
                        sub = {TAGS.get(tid, tid): val for tid, val in sub_ifd.items()}
                    except Exception:
                        pass

                    model = base.get('Model')
                    make = base.get('Make')
                    if model:
                        info["camera"] = str(model).strip()
                    elif make:
                        info["camera"] = str(make).strip()

                    # Ordem de prioridade: original > digitalizada > modificação.
                    dt_value = (sub.get('DateTimeOriginal')
                                or sub.get('DateTimeDigitized')
                                or base.get('DateTime'))
                    if dt_value:
                        # Formato EXIF padrao: '2023:05:14 15:30:00'
                        parts = str(dt_value).split(" ")
                        if len(parts) == 2:
                            info["data"] = parts[0].replace(":", "/")
                            info["hora"] = parts[1]
                        else:
                            info["data"] = str(dt_value)

        except Exception:
            pass

        if info["data"] == "Desconhecida":
            try:
                # Fallback no relogio de modificacao do OS
                timestamp = os.path.getmtime(image_path)
                dt = datetime.datetime.fromtimestamp(timestamp)
                info["data"] = dt.strftime('%Y/%m/%d')
                info["hora"] = dt.strftime('%H:%M:%S')
                info["camera"] = "Dispositivo do Sistema Operacional"
            except Exception as e:
                FileHandler.log_error(f"MetadataInspector: Falha fallback OS em {image_path} - {e}")

        return info
