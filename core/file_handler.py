from pathlib import Path
import unicodedata
import re
import shutil
class FileHandler:
    @staticmethod
    def normalize_string(text: str) -> str:
        """Limpa acentos, espacos duplos e padroniza para lowercase."""
        if not text or not isinstance(text, str): 
            return ""
        
        # Strip e lowercase
        text = text.strip().lower()
        
        # Remove acentos
        text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
        
        # Remove espacos duplos e quebras de linha
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text

    @staticmethod
    def scan_directory(directory_path: str, keywords: list) -> list:
        """Retorna uma lista de arquivos que contem as palavras-chave no nome."""
        matched_files = []
        try:
            path = Path(directory_path)
            if not path.exists(): return matched_files
            
            normalized_keywords = [FileHandler.normalize_string(k) for k in keywords]
            
            for file in path.rglob("*"):
                if file.is_file():
                    norm_name = FileHandler.normalize_string(file.stem)
                    if any(k in norm_name for k in normalized_keywords):
                        matched_files.append(file)
            return matched_files
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as f:
                f.write(f"FileHandler: Falha ao escanear pasta {directory_path} - {e}\n")
            return []

    @staticmethod
    def create_folder(base_path: str, folder_name: str, subfolders: list = None) -> bool:
        try:
            target = Path(base_path) / folder_name
            target.mkdir(parents=True, exist_ok=True)
            if subfolders:
                for sub in subfolders:
                    sub_clean = sub.strip()
                    if sub_clean and sub_clean.lower() != "nao" and sub_clean.lower() != "não":
                        (target / sub_clean).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as f:
                f.write(f"FileHandler: Erro ao criar pasta {folder_name} - {e}\n")
            return False

    @staticmethod
    def list_subfolders(directory_path: str) -> list:
        try:
            path = Path(directory_path)
            if not path.exists() or not path.is_dir(): return []
            return [sub.name for sub in path.iterdir() if sub.is_dir()]
        except:
            return []

    @staticmethod
    def rename_folders_advanced(target_path: str, scope: str, logic_prompt: str, excel_path: str = "") -> bool:
        """Motor Generativo de Renomeação. Avalia o prompt do usuário para aplicar a lógica correta."""
        try:
            target = Path(target_path)
            if not target.exists() or not target.is_dir(): return False
            
            logic_lower = FileHandler.normalize_string(logic_prompt)
            subs = sorted([s for s in target.iterdir() if s.is_dir()])
            
            # 2-Pass Rename: Evita WinError 183 (Colisão de nomes existentes)
            import uuid
            temp_mapping = []
            if "sub" in scope.lower():
                for sub in subs:
                    temp_path = target / f"{uuid.uuid4().hex}"
                    temp_mapping.append((sub.rename(temp_path), sub.name))
            
            # Padrão 1: IGUAL ABAS DO EXCEL
            if "excel" in logic_lower or "aba" in logic_lower:
                import openpyxl
                if not excel_path or not Path(excel_path).exists(): return False
                wb = openpyxl.load_workbook(excel_path, read_only=True)
                sheet_names = wb.sheetnames
                
                # Se escopo for subpastas
                if "sub" in scope.lower():
                    for i, (temp_sub, orig_name) in enumerate(temp_mapping):
                        if i < len(sheet_names):
                            novo_nome = FileHandler.normalize_string(sheet_names[i]).title()
                            temp_sub.rename(target / novo_nome)
                        else:
                            temp_sub.rename(target / orig_name) # Restaura original se faltar aba
                # Se escopo for raiz
                else:
                    if len(sheet_names) > 0:
                        target.rename(target.parent / sheet_names[0])
                return True
                
            # Padrão 2: SEQUENCIAL (ex: "ordem equipe 01 ate 20")
            match = re.search(r'([a-z]+)\s*0*1', logic_lower) # Ex: "equipe 01" -> group(1) = "equipe"
            prefixo = match.group(1).title() if match else logic_prompt.split()[0].title()
            
            if "sub" in scope.lower():
                for i, (temp_sub, _) in enumerate(temp_mapping):
                    temp_sub.rename(target / f"{prefixo} {str(i+1).zfill(2)}")
            else:
                target.rename(target.parent / f"{prefixo} 01")
                
            return True
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as f:
                f.write(f"FileHandler: Erro ao renomear avancado em {target_path} - {e}\n")
            return False

    @staticmethod
    def move_folder(source_path: str, dest_path: str) -> str:
        """Move o arquivo/pasta. Se colidir, adiciona o sufixo _copia."""
        try:
            src = Path(source_path)
            dst_dir = Path(dest_path)
            
            if not src.exists():
                return ""
            
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst_file = dst_dir / src.name
            
            # Zero Data Loss: Evita colisão
            counter = 1
            while dst_file.exists():
                dst_file = dst_dir / f"{src.stem}_copia{counter}{src.suffix}"
                counter += 1
                
            shutil.move(str(src), str(dst_file))
            return str(dst_file)
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as f:
                f.write(f"FileHandler: Erro ao mover {source_path} - {e}\n")
            return ""

    @staticmethod
    def delete_folder(target_path: str) -> bool:
        try:
            target = Path(target_path)
            if target.exists() and target.is_dir():
                shutil.rmtree(target)
                return True
            return False
        except Exception as e:
            with open("erros_conhecidos.txt", "a", encoding="utf-8") as f:
                f.write(f"FileHandler: Erro ao deletar pasta {target_path} - {e}\n")
            return False
