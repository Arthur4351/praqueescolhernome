import os
import sys
import shutil
import tempfile
import unittest
import re
from pathlib import Path

# Adiciona o diretório do projeto ao path de forma dinâmica e portátil
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from core.dynamic_filter import DynamicFilter
from core.file_handler import FileHandler
from core.excel_engine import ExcelEngine
from core.intent_parser import IntentParser
from core.ai_router import AIRouter, TaskType
from core.ocr_engine import OCREngine
from core.metadata_inspector import MetadataInspector
from core.response_generator import ResponseGenerator
from core.agent_core import SophiaAgentCore

class SophiaIntegrationTestSuite(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp(prefix="sophia_test_")
        cls.test_excel_path = os.path.join(cls.temp_dir, "teste.xlsx")
        
        # Cria uma planilha Excel básica para testes do ExcelEngine
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Planilha1"
        ws.cell(row=1, column=1, value="Nome")
        ws.cell(row=1, column=2, value="Equipe")
        ws.cell(row=1, column=3, value="FOTO01")
        
        ws.cell(row=2, column=1, value="Arthur")
        ws.cell(row=2, column=2, value="Equipe 01")
        
        ws.cell(row=3, column=1, value="Paulo")
        ws.cell(row=3, column=2, value="Equipe 02")
        
        wb.save(cls.test_excel_path)
        wb.close()

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(cls.temp_dir)
        except:
            pass

    # =========================================================================
    # DYNAMIC FILTER TESTS (1-7)
    # =========================================================================
    
    def test_01_dynamic_filter_simple_bool(self):
        f = DynamicFilter("True")
        self.assertTrue(f.evaluate({}))

    def test_02_dynamic_filter_boundary_comparison(self):
        f = DynamicFilter("15 <= int(dia) <= 20")
        self.assertTrue(f.evaluate({"dia": "17"}))
        self.assertFalse(f.evaluate({"dia": "12"}))

    def test_03_dynamic_filter_string_containment(self):
        f = DynamicFilter("'iphone' in camera.lower()")
        self.assertTrue(f.evaluate({"camera": "iPhone 13 Pro"}))
        self.assertFalse(f.evaluate({"camera": "Samsung S22"}))

    def test_04_dynamic_filter_syntax_error_fallback(self):
        # Erro de sintaxe (dia == 123 456)
        f = DynamicFilter("dia == 123 456")
        self.assertIsNone(f.code_obj)
        # Deve avaliar para True por padrão
        self.assertTrue(f.evaluate({"dia": "12"}))

    def test_05_dynamic_filter_sandbox_blocks_imports(self):
        f = DynamicFilter("__import__('os').system('echo')")
        # Deve falhar e cair no try-except retornando True
        self.assertTrue(f.evaluate({}))

    def test_06_dynamic_filter_missing_keys(self):
        f = DynamicFilter("camera == 'Canon'")
        # A chave 'camera' não está no dicionário, deve tratar e não travar
        self.assertTrue(f.evaluate({"dia": "10"}))

    def test_07_dynamic_filter_logical_operators(self):
        f = DynamicFilter("int(dia) > 10 and 'eq' in equipe")
        self.assertTrue(f.evaluate({"dia": "15", "equipe": "eq_central"}))
        self.assertFalse(f.evaluate({"dia": "8", "equipe": "eq_central"}))

    # =========================================================================
    # FILE HANDLER TESTS (8-18)
    # =========================================================================

    def test_08_file_handler_normalize_accents(self):
        res = FileHandler.normalize_string("Equipe Célula Água")
        self.assertEqual(res, "equipe celula agua")

    def test_09_file_handler_normalize_tabs_spaces(self):
        res = FileHandler.normalize_string("Equipe\t01   Central\n")
        self.assertEqual(res, "equipe 01 central")

    def test_10_file_handler_scan_empty_keywords(self):
        res = FileHandler.scan_directory(self.temp_dir, [])
        self.assertEqual(len(res), 0)

    def test_11_file_handler_scan_matching_subset(self):
        dummy_file = os.path.join(self.temp_dir, "atividade_foto.jpg")
        Path(dummy_file).touch()
        res = FileHandler.scan_directory(self.temp_dir, ["atividade"])
        self.assertTrue(any(f.name == "atividade_foto.jpg" for f in res))

    def test_12_file_handler_create_folder(self):
        f_name = "pasta_teste_cria"
        res = FileHandler.create_folder(self.temp_dir, f_name)
        self.assertTrue(res)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f_name)))

    def test_13_file_handler_create_folder_with_subfolders(self):
        f_name = "pasta_pai"
        subs = ["sub1", "sub2"]
        res = FileHandler.create_folder(self.temp_dir, f_name, subs)
        self.assertTrue(res)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f_name, "sub1")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f_name, "sub2")))

    def test_14_file_handler_create_folder_subfolder_exclusion(self):
        f_name = "pasta_pai_exclusao"
        subs = ["sub1", "nao"]
        res = FileHandler.create_folder(self.temp_dir, f_name, subs)
        self.assertTrue(res)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, f_name, "sub1")))
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, f_name, "nao")))

    def test_15_file_handler_move_folder_collision(self):
        src_dir = os.path.join(self.temp_dir, "origem")
        os.makedirs(src_dir, exist_ok=True)
        f_src = os.path.join(src_dir, "documento.txt")
        Path(f_src).touch()
        
        dst_dir = os.path.join(self.temp_dir, "destino")
        os.makedirs(dst_dir, exist_ok=True)
        # Cria arquivo colidente
        Path(os.path.join(dst_dir, "documento.txt")).touch()
        
        res = FileHandler.move_folder(f_src, dst_dir)
        self.assertTrue(res.endswith("documento_copia1.txt"))
        self.assertTrue(os.path.exists(res))

    def test_16_file_handler_delete_folder(self):
        del_dir = os.path.join(self.temp_dir, "deletar_mim")
        os.makedirs(del_dir, exist_ok=True)
        res = FileHandler.delete_folder(del_dir)
        self.assertTrue(res)
        self.assertFalse(os.path.exists(del_dir))

    def test_17_file_handler_advanced_rename_sequential(self):
        parent_dir = os.path.join(self.temp_dir, "renomear_lote")
        os.makedirs(parent_dir, exist_ok=True)
        os.makedirs(os.path.join(parent_dir, "subA"), exist_ok=True)
        os.makedirs(os.path.join(parent_dir, "subB"), exist_ok=True)
        
        res = FileHandler.rename_folders_advanced(parent_dir, "subpastas", "Equipe 01")
        self.assertTrue(res)
        self.assertTrue(os.path.exists(os.path.join(parent_dir, "Equipe 01")))
        self.assertTrue(os.path.exists(os.path.join(parent_dir, "Equipe 02")))

    def test_18_file_handler_advanced_rename_rollback(self):
        parent_dir = os.path.join(self.temp_dir, "renomear_lote_erro")
        os.makedirs(parent_dir, exist_ok=True)
        sub_path = os.path.join(parent_dir, "original_folder")
        os.makedirs(sub_path, exist_ok=True)
        
        # Dispara com planilha inexistente para forçar erro e validar rollback
        res = FileHandler.rename_folders_advanced(parent_dir, "subpastas", "excel_abas", excel_path="inexistente.xlsx")
        self.assertFalse(res)
        # Rollback deve manter a pasta original com seu nome original
        self.assertTrue(os.path.exists(sub_path))

    # =========================================================================
    # EXCEL ENGINE TESTS (19-24)
    # =========================================================================

    def test_19_excel_engine_column_validation(self):
        res = ExcelEngine.validate_main_columns(Path(self.test_excel_path), ["Nome"])
        self.assertTrue(res)

    def test_20_excel_engine_formula_injection(self):
        res = ExcelEngine.inject_formula(self.test_excel_path, "Planilha1", "D2", "=SOMA(A1)")
        self.assertTrue(res)

    def test_21_excel_engine_query_data_fuzzy(self):
        res = ExcelEngine.query_data(self.test_excel_path, "artur", "equipe")
        self.assertIn("Equipe 01", res)

    def test_22_excel_engine_query_data_missing_column(self):
        res = ExcelEngine.query_data(self.test_excel_path, "Arthur", "idade")
        self.assertIn("não localizada", res)

    def test_23_excel_engine_query_count_empty(self):
        res = ExcelEngine.query_count_empty(self.test_excel_path, "FOTO01")
        self.assertIn("2 registro", res) # As duas linhas tem FOTO01 vazia

    def test_24_excel_engine_norm(self):
        self.assertEqual(ExcelEngine._norm("  Água  Doce "), "agua doce")

    # =========================================================================
    # INTENT PARSER TESTS (25-30)
    # =========================================================================

    def test_25_intent_parser_normalize_tokenize(self):
        ip = IntentParser()
        tokens = ip._normalize_and_tokenize("Oi! Crie uma pasta, por favor.")
        self.assertTrue("crie" in tokens)
        self.assertTrue("oi" in tokens)

    def test_26_intent_parser_learn_intent(self):
        ip = IntentParser()
        ip.learn_intent("CREATE_FOLDER", "fazer_diretorio")
        ip._load_intents()
        self.assertTrue("fazer_diretorio" in ip._intents_bow["CREATE_FOLDER"])

    def test_27_intent_parser_local_bow_greeting(self):
        ip = IntentParser()
        res = ip.parse_single_intent("Olá, bom dia!")
        self.assertEqual(res["intent"], "GREETING")

    def test_28_intent_parser_local_bow_identity(self):
        ip = IntentParser()
        res = ip.parse_single_intent("Quem é você?")
        self.assertEqual(res["intent"], "IDENTITY")

    def test_29_intent_parser_multiple_split_intents(self):
        ip = IntentParser()
        # Força o bypass da cloud para testar a engine offline local
        ip._cloud_inference = lambda *args: None
        res = ip.parse_multiple_intents("crie uma pasta depois delete a pasta")
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["intent"], "CREATE_FOLDER")
        self.assertEqual(res[1]["intent"], "DELETE_FOLDER")

    def test_30_intent_parser_cache_mechanism(self):
        ip = IntentParser()
        # Mock para retornar um resultado de conversa da nuvem, permitindo testar o cache
        ip._cloud_inference = lambda *args: {"intent": "EXPLAIN_COMMAND", "status": "CONVERSATIONAL", "resposta": "O scan faz uma busca."}
        ip._response_cache.clear()
        res1 = ip.parse_multiple_intents("como funciona o scan")
        # Deve estar em cache agora
        cache_key = list(ip._response_cache.keys())[0]
        self.assertEqual(ip._response_cache[cache_key][0]["intent"], "EXPLAIN_COMMAND")

    # =========================================================================
    # AI ROUTER TESTS (31-34)
    # =========================================================================

    def test_31_ai_router_key_resolution(self):
        # Testa a PRIORIDADE de resolucao de chave (env > config) de forma
        # deterministica, sem depender de uma chave real presente no ambiente.
        ar = AIRouter()
        prov = {"env_key": "SOPHIA_TEST_KEY_31", "api_key": "config_fallback"}
        os.environ.pop("SOPHIA_TEST_KEY_31", None)
        # Sem variavel de ambiente: cai para o api_key legado do config
        self.assertEqual(ar._resolve_api_key(prov), "config_fallback")
        # Com variavel de ambiente definida: ela tem prioridade
        os.environ["SOPHIA_TEST_KEY_31"] = "gsk_env_prioritaria"
        try:
            self.assertEqual(ar._resolve_api_key(prov), "gsk_env_prioritaria")
        finally:
            os.environ.pop("SOPHIA_TEST_KEY_31", None)

    def test_32_ai_router_usage_tracking(self):
        ar = AIRouter()
        ar.usage_today.clear()
        ar._track_usage("TestProv", 1000)
        self.assertEqual(ar.usage_today["TestProv"], 1000)

    def test_33_ai_router_exhaustion_check(self):
        ar = AIRouter()
        prov = {"nome": "TestProv", "limite_diario_tokens": 10000}
        ar.usage_today["TestProv"] = 9500
        self.assertTrue(ar._is_exhausted(prov))

    def test_34_ai_router_temperature_selection(self):
        ar = AIRouter()
        self.assertEqual(TaskType.CODE, "code")
        self.assertEqual(TaskType.REASONING, "reasoning")

    # =========================================================================
    # OCR ENGINE TESTS (35-37)
    # =========================================================================

    def test_35_ocr_engine_availability(self):
        available = OCREngine.is_available()
        self.assertIn(available, [True, False])

    def test_36_ocr_engine_extract_stamp_regex_date(self):
        text = "Relatório executado em 15/05/2026 às 14:30"
        md = re.search(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})', text)
        self.assertIsNotNone(md)
        self.assertEqual(md.group(1), "15")
        self.assertEqual(md.group(2), "05")

    def test_37_ocr_engine_extract_stamp_km(self):
        text = "KM: 123456 \nHODOMETRO: 123456"
        mk = re.search(r'(?:KM|HODOMETRO)[\s:\-]*(\d[\d.,]*)', text, re.IGNORECASE)
        self.assertIsNotNone(mk)
        self.assertEqual(mk.group(1), "123456")

    # =========================================================================
    # METADATA INSPECTOR TESTS (38-39)
    # =========================================================================

    def test_38_metadata_inspector_modtime_fallback(self):
        dummy_file = os.path.join(self.temp_dir, "no_exif.jpg")
        Path(dummy_file).touch()
        info = MetadataInspector.extract_full_metadata(dummy_file)
        self.assertNotEqual(info["data"], "Desconhecida")
        self.assertEqual(info["camera"], "Dispositivo do Sistema Operacional")

    def test_39_metadata_inspector_missing_file(self):
        info = MetadataInspector.extract_full_metadata("missing_file_non_existent.jpg")
        self.assertEqual(info["data"], "Desconhecida")

    # =========================================================================
    # RESPONSE GENERATOR TESTS (40)
    # =========================================================================

    def test_40_response_generator_hash_lookup(self):
        res = ResponseGenerator.generate("EXPLAIN_COMMAND", "Arthur", raw_input="como funciona o scan")
        self.assertIn("varredura nas suas pastas", res)

    # =========================================================================
    # NEW IMPROVEMENTS TESTS (41-42)
    # =========================================================================

    def test_41_ai_router_config_models_override(self):
        # Cria um config temporário simulando a nova chave modelos_ia
        temp_config = os.path.join(self.temp_dir, "temp_config.json")
        import json
        with open(temp_config, "w", encoding="utf-8") as f:
            json.dump({
                "provedores_ia": [
                    {
                        "nome": "ProvedorTeste",
                        "base_url": "https://api.groq.com/openai/v1/chat/completions",
                        "env_key": "GROQ_API_KEY_1",
                        "modelo": "original",
                        "modelo_codigo": "original",
                        "modelo_reasoning": "original",
                        "modelo_intent": "original",
                        "limite_diario_tokens": 500000,
                        "ativo": True,
                        "prioridade": 1
                    }
                ],
                "modelos_ia": {
                    "chat": "modelo-teste-chat",
                    "code": "modelo-teste-code",
                    "reasoning": "modelo-teste-reasoning",
                    "intent": "modelo-teste-intent"
                }
            }, f)
        
        ar = AIRouter(config_path=temp_config)
        # Verifica se o override de modelos_ia foi aplicado em todos os providers carregados
        for p in ar.providers:
            self.assertEqual(p["modelo"], "modelo-teste-chat")
            self.assertEqual(p["modelo_codigo"], "modelo-teste-code")
            self.assertEqual(p["modelo_reasoning"], "modelo-teste-reasoning")
            self.assertEqual(p["modelo_intent"], "modelo-teste-intent")

    def test_42_file_handler_log_error_rotation(self):
        # Testa rotação do log de erros.
        original_log_exists = os.path.exists("erros_conhecidos.txt")
        original_log_content = ""
        if original_log_exists:
            with open("erros_conhecidos.txt", "r", encoding="utf-8") as f:
                original_log_content = f.read()
            os.remove("erros_conhecidos.txt")
        
        try:
            # Cria um log inicial gigante (> 5MB)
            with open("erros_conhecidos.txt", "w", encoding="utf-8") as f:
                f.write("X" * (5 * 1024 * 1024 + 100))
            
            # Executa log_error que deve disparar a rotação
            FileHandler.log_error("Erro de Teste")
            
            # erros_conhecidos.txt atual deve ser novo e pequeno
            self.assertTrue(os.path.exists("erros_conhecidos.txt"))
            self.assertLess(os.path.getsize("erros_conhecidos.txt"), 1000)
            
            # erros_conhecidos.old.txt deve existir com o tamanho original gigante
            self.assertTrue(os.path.exists("erros_conhecidos.old.txt"))
            self.assertGreater(os.path.getsize("erros_conhecidos.old.txt"), 5 * 1024 * 1024)
            
        finally:
            # Limpa logs criados pelo teste
            if os.path.exists("erros_conhecidos.txt"):
                os.remove("erros_conhecidos.txt")
            if os.path.exists("erros_conhecidos.old.txt"):
                os.remove("erros_conhecidos.old.txt")
            
            # Restaura o histórico original do usuário se existia
            if original_log_exists:
                with open("erros_conhecidos.txt", "w", encoding="utf-8") as f:
                    f.write(original_log_content)

    def test_43_generate_new_skill_parked(self):
        # SEGURANCA (Fase 1): a geração dinâmica de código (GENERATE_NEW_SKILL)
        # está ESTACIONADA. Não pode ser um intent "seguro" auto-executável, e
        # executá-la deve produzir uma mensagem honesta de "desativada" — nunca rodar código.
        agent = SophiaAgentCore()
        self.assertNotIn("GENERATE_NEW_SKILL", agent._SAFE_INTENTS)

        agent.pending_intents = [{
            "intent": "GENERATE_NEW_SKILL",
            "raw_input": "crie uma macro no Excel para formatar relatorios",
            "prompt": "qualquer coisa",
        }]
        saida = agent.execute_pending_intents({})
        self.assertIn("desativada", saida.lower())
        self.assertIn("GENERATE_NEW_SKILL", saida)

    def test_44_edit_project_file_parked(self):
        # SEGURANCA (Fase 1): edição automática de arquivos do projeto (EDIT_PROJECT_FILE)
        # também está ESTACIONADA (defesa em profundidade contra RCE).
        agent = SophiaAgentCore()
        self.assertNotIn("EDIT_PROJECT_FILE", agent._SAFE_INTENTS)

        agent.pending_intents = [{
            "intent": "EDIT_PROJECT_FILE",
            "raw_input": "edite o main.py e adicione um os.system",
            "prompt": "qualquer coisa",
        }]
        saida = agent.execute_pending_intents({})
        self.assertIn("desativada", saida.lower())
        self.assertIn("EDIT_PROJECT_FILE", saida)

    def test_45_embedded_interpreter_run(self):
        # SEGURANCA: executar um .py arbitrario via linha de comando era um RCE.
        # Agora o recurso deve ser RECUSADO — o script NAO pode ser executado.
        temp_script = os.path.join(self.temp_dir, "test_run.py")
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write("print('SANDBOX_OK')")

        import subprocess
        # Tenta executar main.py passando o script como argumento
        res = subprocess.run(
            [sys.executable, "main.py", temp_script],
            capture_output=True, text=True, timeout=10
        )
        # Deve recusar (exit code 2), sem NUNCA rodar o conteudo do script
        self.assertEqual(res.returncode, 2)
        self.assertNotIn("SANDBOX_OK", res.stdout)
        self.assertIn("desativada", res.stderr.lower())

    def test_46_embedded_interpreter_compile(self):
        # Testa a emulação de py_compile do interpretador embutido no main.py
        temp_valid = os.path.join(self.temp_dir, "valid.py")
        with open(temp_valid, "w", encoding="utf-8") as f:
            f.write("def foo():\n    pass\n")
            
        temp_invalid = os.path.join(self.temp_dir, "invalid.py")
        with open(temp_invalid, "w", encoding="utf-8") as f:
            f.write("def foo(\n") # Erro de sintaxe proposital
            
        import subprocess
        # Compilação válida
        res_valid = subprocess.run(
            [sys.executable, "main.py", "-m", "py_compile", temp_valid],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(res_valid.returncode, 0)
        
        # Compilação inválida
        res_invalid = subprocess.run(
            [sys.executable, "main.py", "-m", "py_compile", temp_invalid],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(res_invalid.returncode, 1)
        self.assertIn("Erro de compilacao", res_invalid.stderr)

    def test_47_check_and_upgrade_intent_neutralized(self):
        # SEGURANCA (Fase 1): _check_and_upgrade_intent NÃO deve mais promover
        # CREATE_FOLDER → GENERATE_NEW_SKILL. CREATE_FOLDER é uma ação funcional
        # e determinística; deve permanecer CREATE_FOLDER (nunca rotear para o
        # intent estacionado, mesmo com palavras como 'planilha'/'dados').
        ip = IntentParser()
        res = {
            "intent": "CREATE_FOLDER",
            "raw_input": "crie a pasta teeste e coloque a planilha de dados nela",
            "folder_name": "teeste"
        }
        res_out = ip._check_and_upgrade_intent(res)
        self.assertEqual(res_out["intent"], "CREATE_FOLDER")
        self.assertNotEqual(res_out["intent"], "GENERATE_NEW_SKILL")

    def test_48_intent_parser_history_truncation(self):
        # Testa se as mensagens do histórico de conversa do IntentParser são truncadas e limpas corretamente
        ip = IntentParser()
        
        class DummyRouter:
            def call_intent(self, messages, max_tokens):
                return "Certo! [ACTION: GENERATE_NEW_SKILL | PROMPT=" + ("b" * 500) + "]", "MockProvider"
        
        ip._router = DummyRouter()
        
        long_input = "a" * 400
        ip._cloud_inference(long_input)
        
        # Deve ter 2 mensagens no histórico: user e assistant
        self.assertEqual(len(ip.chat_history), 2)
        
        # User message deve estar truncada para 303 caracteres ("..." incluído)
        user_msg = ip.chat_history[0]["content"]
        self.assertTrue(len(user_msg) <= 303)
        self.assertTrue(user_msg.endswith("..."))
        
        # Assistant message deve ter a action limpa e truncada
        assistant_msg = ip.chat_history[1]["content"]
        self.assertTrue(len(assistant_msg) <= 303)
        self.assertIn("[ACTION: GENERATE_NEW_SKILL]", assistant_msg)
        self.assertNotIn("PROMPT=", assistant_msg)

    def test_49_dynamic_coder_continuation(self):
        # Testa se a continuação de código em DynamicCoder funciona corretamente costurando as partes truncadas
        from core.dynamic_coder import DynamicCoder
        coder = DynamicCoder(api_key="dummy_key")
        
        class DummyRouter:
            def __init__(self):
                self.calls = 0
                self.last_was_truncated = False
                
            def call_code(self, messages, max_tokens):
                self.calls += 1
                if self.calls == 1:
                    self.last_was_truncated = True
                    return "```python\nimport os\nclass Foo:\n    def bar(self):\n", "MockProvider"
                else:
                    self.last_was_truncated = False
                    return "        print('done')\n```", "MockProvider"
                    
        coder._router = DummyRouter()
        
        # Gera o script chamando a função mockada
        script = coder._generate_script("crie uma classe foo", {})
        
        # Deve ter chamado a API 2 vezes
        self.assertEqual(coder._router.calls, 2)
        
        # O script final deve estar costurado e limpo
        self.assertEqual(
            script,
            "import os\nclass Foo:\n    def bar(self):\n        print('done')"
        )

    def test_50_atomic_json_write(self):
        # Escrita atômica: grava JSON válido e retorna True; conteúdo íntegro.
        alvo = os.path.join(self.temp_dir, "atomic_out.json")
        dados = {"data": "2026-01-01", "uso": {"Zen": 123}}
        ok = FileHandler.save_json_atomic(alvo, dados, indent=2)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(alvo))
        import json as _json
        with open(alvo, "r", encoding="utf-8") as f:
            lido = _json.load(f)
        self.assertEqual(lido, dados)
        # Não deve deixar arquivos temporários órfãos (.tmp_*) na pasta.
        sobras = [n for n in os.listdir(self.temp_dir) if n.startswith(".tmp_")]
        self.assertEqual(sobras, [])

    def test_51_save_memory_recovers_from_corrupt(self):
        # _save_memory deve se recuperar de um long_term_memory.json corrompido,
        # recriando uma lista válida em vez de estourar. Faz backup/restore do
        # arquivo real do projeto para não afetar o ambiente do usuário.
        import json as _json
        mem_path = os.path.join(PROJECT_ROOT, "long_term_memory.json")
        tinha_backup = os.path.exists(mem_path)
        backup = None
        if tinha_backup:
            with open(mem_path, "r", encoding="utf-8") as f:
                backup = f.read()
        try:
            # Corrompe o arquivo de propósito
            with open(mem_path, "w", encoding="utf-8") as f:
                f.write("{{{ isto não é json válido ]]]")
            ip = IntentParser()
            ip._save_memory("FATO_TESTE_RECUPERACAO_XYZ")
            with open(mem_path, "r", encoding="utf-8") as f:
                conteudo = _json.load(f)  # não deve lançar
            self.assertIsInstance(conteudo, list)
            self.assertIn("FATO_TESTE_RECUPERACAO_XYZ", conteudo)
        finally:
            if tinha_backup:
                with open(mem_path, "w", encoding="utf-8") as f:
                    f.write(backup)
            elif os.path.exists(mem_path):
                os.remove(mem_path)

    def test_52_zen_provider_registered_priority_zero(self):
        # Fase 2: o provedor OpenCode Zen deve estar registrado como prioridade 0
        # (tentado primeiro) e ler a chave de OPENCODE_API_KEY. O modelo ativo é um
        # modelo NÃO-free da Zen (o free-tier retorna 403 fora do CLI do OpenCode).
        zen = AIRouter._DEFAULT_PROVIDERS[0]
        self.assertEqual(zen["prioridade"], 0)
        self.assertEqual(zen["env_key"], "OPENCODE_API_KEY")
        self.assertIn("opencode.ai", zen["base_url"])
        self.assertNotIn("free", zen["modelo"])  # free-tier é bloqueado p/ apps externos
        self.assertTrue(zen["modelo"])           # há um modelo ativo definido

        # Com a chave setada e sem config.json de provedores, o Zen deve ser o 1º ativo.
        old = os.environ.get("OPENCODE_API_KEY")
        os.environ["OPENCODE_API_KEY"] = "oc_sk_dummy_para_teste"
        try:
            cfg_inexistente = os.path.join(self.temp_dir, "no_such_config.json")
            router = AIRouter(config_path=cfg_inexistente)
            self.assertTrue(len(router.providers) >= 1)
            self.assertEqual(router.providers[0]["nome"], "OpenCode-Zen")
        finally:
            if old is None:
                os.environ.pop("OPENCODE_API_KEY", None)
            else:
                os.environ["OPENCODE_API_KEY"] = old

    def test_53_metadata_prioritizes_datetimeoriginal(self):
        # MetadataInspector deve priorizar DateTimeOriginal (sub-IFD 0x8769)
        # sobre DateTime (IFD0). Guarda-se contra variações de libjpeg: se o
        # round-trip do EXIF não preservar o sub-IFD, o teste é pulado.
        from PIL import Image
        img_path = os.path.join(self.temp_dir, "exif_dt.jpg")
        exif = Image.Exif()
        exif[0x0132] = "2026:12:31 23:59:59"          # DateTime (IFD0) — mais recente
        sub = exif.get_ifd(0x8769)
        sub[0x9003] = "2018:06:15 08:30:00"            # DateTimeOriginal — o "verdadeiro"
        exif[0x8769] = sub                             # reatribui p/ Pillow serializar o sub-IFD
        Image.new("RGB", (16, 16), "white").save(img_path, exif=exif)

        # Confirma que o sub-IFD sobreviveu ao round-trip; senão, pula.
        with Image.open(img_path) as check:
            rt = check.getexif().get_ifd(0x8769)
            if rt.get(0x9003) != "2018:06:15 08:30:00":
                self.skipTest("libjpeg local não preservou DateTimeOriginal no round-trip")

        info = MetadataInspector.extract_full_metadata(img_path)
        self.assertEqual(info["data"], "2018/06/15")
        self.assertEqual(info["hora"], "08:30:00")

    def test_54_auditar_efetivo_column_alignment(self):
        # Fix #7: cabeçalho com célula VAZIA antes de "NOME". A leitura deve usar
        # a posição REAL da coluna (col B), não a lista compactada (que apontaria
        # p/ a coluna A vazia e reportaria todo mundo como gap).
        from minhas_habilidades import SophiaExecutor
        import openpyxl

        base = os.path.join(self.temp_dir, "efetivo_align")
        os.makedirs(base, exist_ok=True)
        for nome in ["JOAO SILVA", "MARIA SOUZA"]:
            os.makedirs(os.path.join(base, nome), exist_ok=True)

        xlsx = os.path.join(self.temp_dir, "efetivo_align.xlsx")
        wb = openpyxl.Workbook(); ws = wb.active
        ws["A1"] = None           # coluna de cabeçalho VAZIA antes de NOME
        ws["B1"] = "NOME"
        ws["B2"] = "JOAO SILVA"
        ws["B3"] = "MARIA SOUZA"
        wb.save(xlsx)

        linhas = []
        ex = SophiaExecutor(autonomous_mode=False)
        ex.auditar_efetivo(base, xlsx, lambda m: linhas.append(str(m)))

        saida = " ".join(linhas)
        # Se o alinhamento estiver certo, os nomes casam com as pastas → SEM gaps.
        self.assertIn("Tudo 100% batendo", saida)
        self.assertNotIn("Joao Silva", saida)
        self.assertNotIn("Maria Souza", saida)

if __name__ == "__main__":
    unittest.main()
