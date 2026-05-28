---
name: excel-clean-design
description: Diretrizes de design profissional, formatação e estrutura limpa para planilhas Excel.
contract: input: spreadsheet_request, output: professional_excel_script, version: "1.0"
---
# 📊 @excel-clean-design

- **Diretriz**: Crie planilhas de nível corporativo PREMIUM, esteticamente deslumbrantes e ricas em detalhes. Fuja do básico.
- **Design Visual (Aesthetics) e Formatação Premium**:
  * Aplique cores de fundo ricas e profissionais para cabeçalhos (ex: Azul Marinho, Ciano, com fonte Branca/Clara e Negrito).
  * OBRIGATÓRIO: Implemente "Zebra Striping" (linhas alternadas em cores claras, ex: '#F2F9F9' e branco) para facilitar a leitura.
  * Formate números apropriadamente: valores monetários devem ter formato de moeda (ex: `R$ #,##0.00`), quantidades com separadores de milhares.
  * OBRIGATÓRIO: Adicione formatação condicional (ex: vermelho para alto consumo, verde para normal) usando `CellIsRule`.
  * Adicione bordas suaves em todas as células de dados.
- **Estrutura e Organização Avançada**:
  * O título da planilha (célula mesclada no topo) deve ser imponente (fonte grande, negrito, centralizado).
  * NUNCA mescle células que contêm nomes de colunas diferentes.
  * Crie múltiplas seções, como: uma "Tabela de Resumo" e uma "Tabela de Detalhes".
  * Inclua legendas explicando os status e cores.
- **Visualização de Dados**:
  * OBRIGATÓRIO: Sempre inclua um Gráfico (ex: BarChart 2D ou 3D) posicionado de forma inteligente na planilha para visualizar os principais dados.
- **Fórmulas e Funções**:
  * Use fórmulas dinâmicas do Excel em inglês (como `=SUM(...)`, `=AVERAGE(...)`, `=IF(...)`) para calcular totais, médias e resultados. Não calcule estaticamente no Python.
- **Ajuste de Largura**:
  * Sempre ajuste automaticamente a largura das colunas baseando-se no maior tamanho do texto de cada coluna, mas se houver células mescladas, ignore-as no cálculo de largura para evitar o erro "MergedCell object has no attribute 'column'". (Use `from openpyxl.utils import get_column_letter`, e `col_letter = get_column_letter(col[0].column)` se `col[0]` não for mesclada).
- **Segurança e Proteção**:
  * Proteja as planilhas (`ws.protection.sheet = True`) desbloqueando apenas as células de inserção de dados para que fórmulas e cabeçalhos fiquem protegidos contra edição acidental.
  * Garanta tratamento de exceções (try/except) e fechamento seguro de conexões de arquivos.
