import os
import sys
import yaml
from pathlib import Path

# Force UTF-8 encoding on Windows terminal output to avoid cp1252 character maps errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def validate_5k_skills():
    skills_dir = Path("C:/Users/paulo/OneDrive/Documents/Obsidian Vault/_agent/skills")
    
    if not skills_dir.exists():
        print("❌ Diretório de skills não encontrado!")
        return False
        
    print("🧪 Iniciando validação e auditoria estrutural do Obsidian Vault...")
    
    folders = [f for f in skills_dir.iterdir() if f.is_dir()]
    total_folders = len(folders)
    
    print(f"📊 Total de pastas encontradas em .agent/skills/: {total_folders}")
    
    valid_count = 0
    errors = []
    names_seen = set()
    
    for folder in folders:
        skill_file = folder / "SKILL.md"
        if not skill_file.exists():
            # Alguns folders originais como lint-and-validate podem ter outros arquivos ou estruturas, tudo bem!
            continue
            
        try:
            with open(skill_file, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Verifica frontmatter
            if not content.startswith("---"):
                errors.append(f"❌ {folder.name}: Falta delimitador de frontmatter inicial")
                continue
                
            parts = content.split("---")
            if len(parts) < 3:
                errors.append(f"❌ {folder.name}: Frontmatter mal formado")
                continue
                
            yaml_content = parts[1]
            metadata = yaml.safe_load(yaml_content)
            
            name = metadata.get("name")
            desc = metadata.get("description")
            
            if not name:
                errors.append(f"❌ {folder.name}: Atributo 'name' ausente no frontmatter")
                continue
            if not desc:
                errors.append(f"❌ {folder.name}: Atributo 'description' ausente")
                continue
                
            if name in names_seen:
                errors.append(f"❌ Duplicata de nome detectada: {name}")
            names_seen.add(name)
            
            valid_count += 1
            
        except Exception as e:
            errors.append(f"❌ {folder.name}: Erro ao analisar SKILL.md: {e}")
            
    print(f"✅ Total de skills válidas auditadas: {valid_count}")
    
    if errors:
        print(f"⚠️ Foram encontrados {len(errors)} erros/alertas:")
        for err in errors[:20]:  # Mostra os 20 primeiros
            print(err)
        if len(errors) > 20:
            print(f"... e mais {len(errors) - 20} erros ocultados.")
        return False
    else:
        print("🎉 SUCESSO ABSOLUTO! 100% das notas geradas estão saudáveis, estruturadas e sem colisões!")
        return True

if __name__ == "__main__":
    validate_5k_skills()
