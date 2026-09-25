---
name: python-clean-dry
description: Princípio DRY (Don't Repeat Yourself) aplicado à modularização de código Python.
contract: input: code_blocks, output: refactored_functions, version: "1.0"
---
# 🔄 @python-clean-dry
- **Diretriz**: Nunca duplique lógica. Se um bloco de código aparece mais de duas vezes, extraia para uma função ou utilitário parametrizado.
- **Fluxo**: Identificar duplicidade → parametrizar variáveis → criar helper comum → substituir código duplicado.
- **Validação**: Verificar se a refatoração preserva a semântica e os testes existentes.
- **Anti-Padrão**: Copiar e colar funções entre módulos (ex: funções auxiliares de string ou listas).
- **Segurança**: Centralize rotinas críticas de validação de dados para evitar bypasses locais.
