---
name: python-clean-functions
description: Funções pequenas, puras e focadas em responsabilidade única em Python.
contract: input: python_functions, output: modular_functions, version: "1.0"
---
# 🧪 @python-clean-functions
- **Diretriz**: Funções devem fazer apenas uma coisa e fazê-la bem. Mantenha funções pequenas (idealmente abaixo de 20 linhas). Reduza o número de argumentos a no máximo 3.
- **Fluxo**: Analisar tamanho da função → extrair blocos aninhados para subfunções → retornar valores limpos.
- **Validação**: Garantir efeitos colaterais mínimos (funções puras).
- **Anti-Padrão**: Passar flags booleanas que mudam drasticamente o comportamento interno da função (ex: `processar(atualizar_tudo=True)`).
