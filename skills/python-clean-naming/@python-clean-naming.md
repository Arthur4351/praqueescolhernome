---
name: python-clean-naming
description: Nomenclatura limpa, legível e padronizada em Python (Clean Code PEP 8).
contract: input: variables | functions | classes, output: naming_report, version: "1.0"
---
# 🏷️ @python-clean-naming
- **Diretriz**: Use nomes descritivos e autoexplicativos. Nomes de variáveis/funções em snake_case. Classes em PascalCase. Evite abreviações obscuras.
- **Fluxo**: Analisar código → identificar variáveis curtas (x, y, temp) ou ambíguas → renomear para revelar intenção.
- **Validação**: Garantir que cada nome descreva exatamente o que o objeto é ou faz.
- **Anti-Padrão**: Evite sufixos redundantes como `EquipeDataList` (use `equipes`).
- **Segurança**: Nunca inclua credenciais ou dados sensíveis em nomes de constantes.
