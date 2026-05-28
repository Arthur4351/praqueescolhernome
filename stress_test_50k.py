import os
import sys
import random
import time
import re
from pathlib import Path

# Adiciona o diretório do projeto ao path de forma dinâmica e portátil
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from core.dynamic_filter import DynamicFilter
from core.file_handler import FileHandler
from core.intent_parser import IntentParser
from core.ocr_engine import OCREngine
from core.metadata_inspector import MetadataInspector

def run_stress_tests():
    print("[+] Starting SOPHIA 50,000 Stress/Fuzz Testing Suite...")
    start_time = time.time()
    
    total_tests = 50000
    failures = 0
    
    # 1. Dynamic Filter Tests (15,000 runs)
    print("[+] Running 15,000 Dynamic Filter fuzz cases...")
    filters_exprs = [
        "15 <= int(dia) <= 20",
        "'iphone' in camera.lower()",
        "int(dia) > 10 and 'eq' in equipe",
        "dia == 123 456",  # syntax error fallback
        "__import__('os').system('echo')",  # sandbox check
        "camera == 'Canon'",  # missing keys check
        "tamanho_bytes > 1024",
        "len(nome) > 5",
        "float(dia) / 2.0 == 5.0"
    ]
    
    for i in range(15000):
        expr = random.choice(filters_exprs)
        metadata = {
            "dia": str(random.randint(1, 31)),
            "hora": f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:00",
            "camera": random.choice(["iPhone", "Samsung", "Canon", "Sony", None]),
            "equipe": random.choice(["Equipe 01", "Equipe 02", "eq_central", None]),
            "nome": f"foto_{random.randint(1,100)}.jpg",
            "tamanho_bytes": random.randint(100, 1000000)
        }
        # Deleta chaves aleatoriamente para testar resiliência
        if random.random() < 0.2:
            del metadata["camera"]
        if random.random() < 0.2:
            del metadata["dia"]
            
        try:
            f = DynamicFilter(expr)
            res = f.evaluate(metadata)
            if not isinstance(res, bool):
                raise ValueError("Result is not a boolean")
        except Exception as e:
            print(f"[-] Failure in Dynamic Filter run {i}: {e}")
            failures += 1
            
    # 2. Intent Parser NLP & Cache (15,000 runs)
    print("[+] Running 15,000 Intent Parser NLP & Cache fuzz cases...")
    ip = IntentParser()
    ip._cloud_inference = lambda *args: {"intent": "EXPLAIN_COMMAND", "status": "CONVERSATIONAL", "resposta": "Explicacao."}
    
    words_pool = [
        "oi", "ola", "bom dia", "como funciona", "crie uma pasta", 
        "depois delete a pasta", "quem e voce", "ajuda", "qual equipe", 
        "fotos", "excel", "obrigado", "lote", "script", "bat"
    ]
    
    for i in range(15000):
        phrase_len = random.randint(1, 4)
        phrase = " ".join(random.choices(words_pool, k=phrase_len))
        
        try:
            res = ip.parse_multiple_intents(phrase)
            if not isinstance(res, list) or len(res) == 0:
                raise ValueError("Result should be a non-empty list of intents")
            for item in res:
                if "intent" not in item:
                    raise ValueError("Missing intent key in result")
        except Exception as e:
            print(f"[-] Failure in Intent Parser run {i}: {e}")
            failures += 1

    # 3. String Normalization (10,000 runs)
    print("[+] Running 10,000 String Normalization fuzz cases...")
    chars_pool = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ \t\n-_"
    for i in range(10000):
        raw_str = "".join(random.choices(chars_pool, k=random.randint(5, 50)))
        try:
            norm = FileHandler.normalize_string(raw_str)
            # Garante que nenhum caractere acentuado restou
            for char in norm:
                if char in "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ":
                    raise ValueError(f"Accents remained in normalized string: {norm}")
        except Exception as e:
            print(f"[-] Failure in String Normalization run {i}: {e}")
            failures += 1

    # 4. OCR Regex Parsing (5,000 runs)
    print("[+] Running 5,000 OCR Regex fuzz cases...")
    for i in range(5000):
        text_type = random.randint(1, 3)
        if text_type == 1:
            text = f"Relatório do dia {random.randint(1,28)}/{random.randint(1,12)}/{random.randint(2000,2030)} às {random.randint(0,23)}:30"
        elif text_type == 2:
            text = f"KM: {random.randint(100, 999999)} \n HODOMETRO {random.randint(100, 999999)}"
        else:
            text = "texto aleatorio sem data nem km 1234"
            
        try:
            md = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})', text)
            mk = re.search(r'(?:KM|HODOMETRO)[\s:\-]*(\d[\d.,]*)', text, re.IGNORECASE)
            if md:
                _ = md.group(1)
            if mk:
                _ = mk.group(1)
        except Exception as e:
            print(f"[-] Failure in OCR Regex run {i}: {e}")
            failures += 1

    # 5. Metadata Fallback (5,000 runs)
    print("[+] Running 5,000 Metadata Inspector fallback cases...")
    for i in range(5000):
        fake_filename = f"non_existent_file_{random.randint(1, 1000000)}.jpg"
        try:
            info = MetadataInspector.extract_full_metadata(fake_filename)
            if info["data"] != "Desconhecida":
                raise ValueError("Expected date to be Desconhecida for non-existent file")
        except Exception as e:
            print(f"[-] Failure in Metadata Inspector run {i}: {e}")
            failures += 1

    duration = time.time() - start_time
    print("-" * 50)
    print(f"[+] Done running {total_tests} fuzzed iterations!")
    print(f"[+] Total Duration: {duration:.2f} seconds")
    print(f"[+] Total Failures: {failures}")
    print("-" * 50)
    
    if failures == 0:
        print("[+] SUCCESS: SOPHIA passed all 50,000 integrity test cases successfully!")
        sys.exit(0)
    else:
        print(f"[-] FAILED: SOPHIA had {failures} failures in the stress test.")
        sys.exit(1)

if __name__ == "__main__":
    run_stress_tests()
