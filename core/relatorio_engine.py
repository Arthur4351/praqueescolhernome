import datetime

def gerar_relatorio_faltas(dados_relatorio: dict) -> tuple:
    """
    Gera um relatório de fotos faltantes estilizado em Markdown a partir do dicionário pre-construído
    cruzado com os dias reais do Excel.
    Retorna (texto_resumo, dados_json).
    """
    if not dados_relatorio:
        return "ℹ️ Nenhuma equipe foi processada ou a planilha estava vazia.", {}
        
    now = datetime.datetime.now()
    
    # Gerar texto premium
    resumo_texto = f"📊 *Relatório de Auditoria Sophia* - {now.strftime('%d/%m/%Y')}\n"
    resumo_texto += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    total_faltas = 0
    equipes_completas = 0
    
    # Ordenar equipes alfabeticamente
    for eq in sorted(dados_relatorio.keys()):
        dias = dados_relatorio[eq]
        if dias:
            resumo_texto += f"🚨 *{eq}*\n"
            for dia in sorted(list(dias.keys()), key=lambda x: int(x)):
                faltas = dias[dia]
                resumo_texto += f"  └ 📅 Dia {int(dia):02d}: ❌ Faltando {', '.join(faltas)}\n"
                total_faltas += len(faltas)
            resumo_texto += "\n"
        else:
            equipes_completas += 1
            
    if total_faltas == 0:
        resumo_texto += "✨ *EXCELENTE!* ✨\nNenhuma foto está faltando nas planilhas hoje.\n"
    else:
        resumo_texto += "━━━━━━━━━━━━━━━━━━━━━━\n"
        resumo_texto += f"📉 *Resumo:* Faltam {total_faltas} fotos no total.\n"
        
    if equipes_completas > 0:
        resumo_texto += f"✅ {equipes_completas} equipe(s) com documentação 100% em dia.\n"
            
    return resumo_texto, dados_relatorio
