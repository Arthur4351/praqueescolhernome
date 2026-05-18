import os
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta

def criar_imagem(texto, caminho_arquivo, cor_fundo):
    img = Image.new('RGB', (800, 600), color=cor_fundo)
    d = ImageDraw.Draw(img)
    
    # Tenta usar uma fonte padrão
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
        
    # Calcula a posição centralizada usando textbbox
    bbox = d.textbbox((0, 0), texto, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (800 - text_width) / 2
    y = (600 - text_height) / 2
    
    d.text((x, y), texto, fill=(255, 255, 255), font=font)
    img.save(caminho_arquivo)

def gerar_teste():
    pasta_teste = os.path.join(os.path.dirname(__file__), "fotos_teste_sophia")
    if not os.path.exists(pasta_teste):
        os.makedirs(pasta_teste)
        
    equipes = ["Equipe Alpha", "Equipe Bravo", "Equipe Charlie"]
    tipos = [
        ("1-entrada", (50, 150, 50)),   # Verde
        ("2-antes", (150, 50, 50)),     # Vermelho
        ("3-depois", (50, 50, 150)),    # Azul
        ("4-saida", (100, 100, 100))    # Cinza
    ]
    
    data_inicio = datetime(2026, 5, 1)
    
    total = 0
    for dia in range(10):
        data_atual = data_inicio + timedelta(days=dia)
        data_str = data_atual.strftime("%Y-%m-%d")
        
        for equipe in equipes:
            for tipo_nome, cor in tipos:
                # Nome do arquivo amigável para extração (Equipe_Data_Tipo)
                nome_arquivo = f"{equipe}_{data_str}_{tipo_nome}.jpg"
                caminho = os.path.join(pasta_teste, nome_arquivo)
                
                texto = f"{equipe}\nData: {data_str}\nFase: {tipo_nome}"
                criar_imagem(texto, caminho, cor)
                total += 1
                
    print(f"✅ Geradas {total} fotos de teste na pasta: {pasta_teste}")

if __name__ == "__main__":
    print("Iniciando geração de fotos de teste...")
    gerar_teste()
