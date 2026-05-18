import os
from PIL import Image
from PIL.ExifTags import TAGS
import datetime

class MetadataInspector:
    @staticmethod
    def extract_full_metadata(image_path: str) -> dict:
        """Extrai Data, Hora e Modelo da Camera de forma leve via EXIF ou SO."""
        info = {"data": "Desconhecida", "hora": "Desconhecida", "camera": "Desconhecida"}
        try:
            with Image.open(image_path) as img:
                exif_data = img.getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag in ('DateTime', 'DateTimeOriginal'):
                            # Formato EXIF padrao: '2023:05:14 15:30:00'
                            parts = str(value).split(" ")
                            if len(parts) == 2:
                                info["data"] = parts[0].replace(":", "/")
                                info["hora"] = parts[1]
                            else:
                                info["data"] = str(value)
                        elif tag == 'Model':
                            info["camera"] = str(value).strip()
                        elif tag == 'Make' and info["camera"] == "Desconhecida":
                            info["camera"] = str(value).strip()

            if info["data"] == "Desconhecida":
                # Fallback no relogio de modificacao do OS
                timestamp = os.path.getmtime(image_path)
                dt = datetime.datetime.fromtimestamp(timestamp)
                info["data"] = dt.strftime('%Y/%m/%d')
                info["hora"] = dt.strftime('%H:%M:%S')
                info["camera"] = "Dispositivo do Sistema Operacional"
                
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as f:
                f.write(f"MetadataInspector: Falha EXIF em {image_path} - {e}\n")
        
        return info
