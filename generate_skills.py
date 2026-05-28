import os
import sys
import shutil
import itertools
from pathlib import Path

# Force UTF-8 encoding on Windows terminal output to avoid cp1252 character maps errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def generate_5k_skills():
    # Caminho do Obsidian Vault de Skills do OneDrive
    skills_dir = Path("C:/Users/paulo/OneDrive/Documents/Obsidian Vault/_agent/skills")
    
    # Lista de áreas principais e seus 15 tópicos específicos (150 tópicos únicos)
    topics_by_area = {
        "frontend": [
            "react-hooks", "nextjs-server-actions", "vue-composition", "svelte-routing", "tailwind-v4",
            "state-redux", "state-zustand", "micro-frontends", "css-grid", "a11y-standards",
            "seo-optimization", "lighthouse-performance", "form-handling", "webgl-shaders", "pwa-caching"
        ],
        "backend": [
            "rest-api", "graphql-federation", "trpc-type-safety", "grpc-protobuf", "express-middleware",
            "fastapi-dependency", "rust-axum-routing", "go-concurrency", "node-async", "auth-jwt",
            "oauth2-pkce", "session-caching", "rate-limiting", "error-handling", "logging-telemetry"
        ],
        "mobile": [
            "react-native-bridge", "flutter-riverpod", "swiftui-state", "jetpack-compose-state", "android-services",
            "ios-backgrounding", "mobile-caching", "push-notifications", "app-store-seo", "mobile-deep-linking",
            "flutter-animations", "react-native-reanimated", "mobile-offline-sync", "secure-storage", "biometric-auth"
        ],
        "database": [
            "postgres-indexing", "mysql-clustering", "mongodb-aggregation", "redis-caching", "sqlite-performance",
            "pinecone-vector", "database-sharding", "orm-prisma-optim", "sqlalchemy-queries", "db-migrations",
            "acid-transactions", "read-replicas", "dynamodb-keys", "clickhouse-analytics", "cassandra-tuning"
        ],
        "devops": [
            "docker-multistage", "k8s-pod-scaling", "terraform-modules", "github-actions-ci", "jenkins-pipelines",
            "prometheus-monitoring", "grafana-dashboards", "aws-lambda-serverless", "nginx-reverse-proxy", "cloudflare-cdn",
            "linux-hardening", "ansible-playbooks", "argocd-gitops", "vault-secrets", "docker-compose-local"
        ],
        "systems": [
            "rust-borrow-checker", "cpp-memory-leak", "assembly-registers", "go-garbage-collector", "concurrency-mutex",
            "webassembly-compilation", "linux-syscalls", "network-sockets", "file-descriptors", "memory-paging",
            "compiler-optimization", "cpu-pipelining", "garbage-collection-tuning", "binary-serialization", "multi-threading"
        ],
        "ai": [
            "pytorch-training", "pandas-dataframes", "scikit-learn-regression", "transformers-fine-tuning", "rag-vector-search",
            "llm-prompt-engineering", "tensorflow-graphs", "keras-classification", "feature-engineering", "model-quantization",
            "data-augmentation", "huggingface-pipelines", "langchain-agents", "llm-fine-tuning", "hyperparameter-optimization"
        ],
        "gamedev": [
            "unity-game-loop", "godot-scene-trees", "unreal-blueprints", "physics-colliders", "shader-graphs",
            "audio-spatialization", "pathfinding-astar", "procedural-generation", "ecs-architecture", "gameplay-ability-system",
            "multiplayer-networking", "animation-state-machines", "canvas-rendering", "threejs-scenes", "webgl-buffers"
        ],
        "cybersecurity": [
            "owasp-top-10", "openssl-certificates", "xss-prevention", "csrf-mitigation", "sql-injection-defense",
            "symmetric-cryptography", "asymmetric-encryption", "threat-modeling", "reverse-engineering", "buffer-overflow-defense",
            "jwt-vulnerabilities", "api-security", "network-sniffing", "penetration-testing", "firewall-configuration"
        ],
        "testing": [
            "pytest-fixtures", "jest-mocking", "playwright-e2e", "junit-assertions", "cypress-components",
            "bdd-cucumber", "mutation-testing", "performance-load-testing", "mock-api-servers", "ci-test-reporting",
            "coverage-analysis", "visual-regression", "integration-testing", "snapshot-testing", "contract-testing"
        ]
    }

    levels = ["junior", "intermediate", "senior", "lead", "architect"]
    focuses = ["performance", "security", "architecture", "scalability", "testing", "maintenance", "integration"]

    # Conexões horizontais de focos técnicos para tecer a malha
    focus_connections = {
        "performance": ["scalability", "architecture"],
        "security": ["testing", "maintenance"],
        "architecture": ["integration", "scalability"],
        "scalability": ["performance", "architecture"],
        "testing": ["security", "maintenance"],
        "maintenance": ["testing", "security"],
        "integration": ["architecture", "performance"]
    }

    # Gera a lista de todas as 5.250 combinações possíveis
    combinations = []
    for area, topics in topics_by_area.items():
        for topic in topics:
            for lvl in levels:
                for fcs in focuses:
                    combinations.append((area, topic, lvl, fcs))
                    
    target_skills = combinations[:5000]
    
    print("🔎 Varrendo o Obsidian Vault para identificar as notas nativas preexistentes...")
    native_skills = []
    if skills_dir.exists():
        for p in skills_dir.iterdir():
            if p.is_dir():
                for f_md in p.glob("*.md"):
                    if f_md.name.startswith("@"):
                        native_skills.append(f_md.stem)
    
    native_skills.sort()
    print(f"📊 Encontradas {len(native_skills)} habilidades nativas! Criando ponte de conexões...")

    # Agrupamento lógico das competências nativas
    core_ops = []
    dev_diag = []
    file_sys = []
    ui_ux = []
    data_eng = []
    others = []
    
    for ns in native_skills:
        ns_lower = ns.lower()
        if any(k in ns_lower for k in ["orchestrator", "router", "intent", "context", "logico", "scheduler", "streamer", "guardian"]):
            core_ops.append(ns)
        elif any(k in ns_lower for k in ["debug", "inspect", "generat", "archaeo", "test", "verify", "audit", "regex", "matcher"]):
            dev_diag.append(ns)
        elif any(k in ns_lower for k in ["file", "system", "backup", "clip", "down", "process", "kill", "installer"]):
            file_sys.append(ns)
        elif any(k in ns_lower for k in ["style", "theme", "dialog", "scale", "progress", "splash", "tray", "icon", "widget", "drag", "font"]):
            ui_ux.append(ns)
        elif any(k in ns_lower for k in ["excel", "panda", "json", "xml", "clean", "export", "extract", "anonym", "db", "database", "query"]):
            data_eng.append(ns)
        else:
            others.append(ns)
            
    print(f"🔄 Iniciando a geração procedural da teia de {len(target_skills)} skills no Obsidian...")
    
    # 1. Criação do Central Index (_central-index.md)
    central_index_content = """# 🌌 Central Knowledge Index

Welcome to the central galaxy of the Agentic Obsidian Vault. This index interconnects the 10 core technical domains along with the core operations of the Agent.

## 🛰️ Technical Domains

* [[_frontend-domain|Frontend Domain]] - UI/UX, Frameworks, Graphics and Performance
* [[_backend-domain|Backend Domain]] - APIs, Concurrency, Security and Architecture
* [[_mobile-domain|Mobile Domain]] - Native & Hybrid Mobile Frameworks and Offline Sync
* [[_database-domain|Database Domain]] - Indexing, Clustering, Sharding and Optimizations
* [[_devops-domain|Devops Domain]] - Virtualization, Infrastructure, CI/CD and Security
* [[_systems-domain|Systems Domain]] - Memory Management, Low-level, and Compilers
* [[_ai-domain|AI Domain]] - Deep Learning, LLMs, and Prompt Engineering
* [[_gamedev-domain|Gamedev Domain]] - Game Loops, Physics Engines, Graphics and Networking
* [[_cybersecurity-domain|Cybersecurity Domain]] - Network Audits, Penetration Testing, and Defense
* [[_testing-domain|Testing Domain]] - Fixtures, E2E Automation, and Mutation testing

## 🧠 Core Agent Systems

* [[_agent-core-skills|Core Agent Skills]] - Native LLM Routing, Orchestration, DevTools, and UI Managers
"""
    with open(skills_dir / "_central-index.md", "w", encoding="utf-8") as f:
        f.write(central_index_content)

    # 2. Criação da nota de Core Agent Skills (_agent-core-skills.md)
    def make_list(lst):
        return "\n".join(f"* [[{item}]]" for item in lst) if lst else "* (Nenhuma identificada)"

    agent_core_content = f"""# 🧠 Core Agent Skills

* **Central Hub**: [[_central-index|Galaxy Central Index]]

Welcome to the native core skills index of the Agent. These nodes represent the internal runtime modules, decorators, and engine systems.

---

## 🌌 Core Agent Orchestration
{make_list(core_ops)}

## 🛠️ Diagnostics & Verification
{make_list(dev_diag)}

## 📂 System & Files Management
{make_list(file_sys)}

## 🎨 UI, Styling & Experience
{make_list(ui_ux)}

## 📊 Data Engineering & Databases
{make_list(data_eng)}

## ⚙️ Specialized Automation Integrators
{make_list(others)}
"""
    with open(skills_dir / "_agent-core-skills.md", "w", encoding="utf-8") as f:
        f.write(agent_core_content)

    # 3. Criação dos Domain Hubs (_{area}-domain.md)
    for area, topics in topics_by_area.items():
        topic_links = []
        for topic in topics:
            topic_title = topic.replace('-', ' ').title()
            topic_links.append(f"### 📍 {topic_title}")
            topic_links.append(f"  * [[{topic}-junior-performance|Junior Performance Hub]]")
            topic_links.append(f"  * [[{topic}-senior-architecture|Senior Architecture Hub]]")
            topic_links.append(f"  * [[{topic}-architect-scalability|Architect Scalability Hub]]")
            
        topics_str = "\n".join(topic_links)
        domain_content = f"""# 🪐 {area.upper()} Technical Domain

* **Central Hub**: [[_central-index|Galaxy Central Index]]

---

## 📚 Core Topics in this Domain

{topics_str}
"""
        with open(skills_dir / f"_{area}-domain.md", "w", encoding="utf-8") as f:
            f.write(domain_content)

    # 4. Geração individual de cada Skill conectada
    count = 0
    for area, topic, lvl, fcs in target_skills:
        skill_name = f"{topic}-{lvl}-{fcs}"
        skill_dir = skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = skill_dir / "SKILL.md"
        
        # Conexão de Senioridade Vertical (Anterior e Próximo)
        lvl_idx = levels.index(lvl)
        prog_items = []
        if lvl_idx > 0:
            prev_lvl = levels[lvl_idx - 1]
            prev_skill = f"{topic}-{prev_lvl}-{fcs}"
            prog_items.append(f"  * ⬅️ **Previous seniority**: [[{prev_skill}|{topic.replace('-', ' ').title()} - {prev_lvl.upper()} ({fcs.title()})]]")
        if lvl_idx < len(levels) - 1:
            next_lvl = levels[lvl_idx + 1]
            next_skill = f"{topic}-{next_lvl}-{fcs}"
            prog_items.append(f"  * ➡️ **Next seniority**: [[{next_skill}|{topic.replace('-', ' ').title()} - {next_lvl.upper()} ({fcs.title()})]]")
        progression_links = "\n".join(prog_items) if prog_items else "  * (No higher/lower level available)"

        # Conexão de Foco Horizontal (Tópicos Correlatos)
        fcs_items = []
        for rel_fcs in focus_connections.get(fcs, []):
            rel_skill = f"{topic}-{lvl}-{rel_fcs}"
            fcs_items.append(f"  * 🎯 **Related focus**: [[{rel_skill}|{topic.replace('-', ' ').title()} - {lvl.upper()} ({rel_fcs.title()})]]")
        focus_links = "\n".join(fcs_items) if fcs_items else "  * (No related focus areas mapped)"

        desc = f"Domain guide for {topic.replace('-', ' ').title()} at {lvl.upper()} level focusing on technical {fcs} and Clean Code."
        
        content = f"""---
name: {skill_name}
description: {desc}
allowed-tools: Read, Write, Edit
version: 1.0
priority: normal
---

# {topic.replace('-', ' ').title()} - {lvl.upper()} ({fcs.title()})

> **OBSIDIAN AGENTIC SKILL** - Coexisting knowledge base for robust {area.upper()} automation.

---

## 🌐 Connected Knowledge Web

* 🪐 **Domain Hub**: [[_{area}-domain|{area.title()} Domain Hub]]
* 🌌 **Central Index**: [[_central-index|Galaxy Central Index]]
* 📈 **Seniority Progression**:
{progression_links}
* 🔗 **Related Focus Areas**:
{focus_links}

---

## Technical Standards

| Principle | Objective |
|-----------|-----------|
| **Best Practice** | Implement robust structural clean patterns |
| **Integrity** | Maintain clear scope isolation |
| **Scale** | Fully optimized for {fcs} and efficiency |

---

## Anti-Patterns

| ❌ Avoid | ✅ Use Instead |
|----------|----------------|
| Naive file sequential loops | Fast batch processing |
| Cryptic variable names | Clear descriptive parameters |
| Over-complex systems | Simple composed design patterns |

---

## Operational Guide
1. Ensure the code conforms with general `{area}` guidelines.
2. Run standard verification suites to audit output.
3. Validate `{fcs}` metrics for quality assurance.
"""
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        count += 1
        if count % 1000 == 0:
            print(f"🔹 {count} skills interconectadas gravadas no disco...")

    print(f"✅ Sucesso absoluto! {count} skills e hubs interconectados gerados em {skills_dir}!")

if __name__ == "__main__":
    generate_5k_skills()
