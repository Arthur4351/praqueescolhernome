---
name: python-clean-solid
description: Princípios SOLID focados em Single Responsibility e Open/Closed em classes Python.
contract: input: python_classes, output: solid_structure, version: "1.0"
---
# 🧱 @python-clean-solid
- **Diretriz**: Cada classe ou módulo deve ter apenas um motivo para mudar (SRP). Estenda comportamentos usando herança/composição em vez de modificar código existente (OCP).
- **Fluxo**: Mapear responsabilidades da classe → separar lógica de apresentação de lógica de negócio → quebrar classes infladas.
- **Validação**: Verificar acoplamento entre classes. Garantir independência de módulos.
- **Anti-Padrão**: Classes Deus (God Classes) que gerenciam arquivos, fazem OCR, mandam e-mail e tratam a UI juntas.
