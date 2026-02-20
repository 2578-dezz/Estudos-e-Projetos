import os
import time
import requests
import re

# --- Configurações ---
# Mude para "en" se o mangá estiver em inglês, ou "pt-br" para português
IDIOMA = "pt-br" 
PAUSE_ENTRE_REQ = 0.8  # Aumentei um pouco a pausa para garantir segurança com muitos capítulos

def limpar_nome(nome):
    """Remove caracteres proibidos no Windows/Linux"""
    if not nome:
        return ""
    # Remove caracteres inválidos
    nome_limpo = re.sub(r'[<>:"/\\|?*]', '', nome)
    # Remove espaços extras
    return nome_limpo.strip()

def obter_id_manga(url):
    try:
        partes = url.split('/')
        if 'title' in partes:
            index_title = partes.index('title')
            return partes[index_title + 1]
        return partes[-2] if url.endswith('/') else partes[-1]
    except:
        return None

def obter_capitulos(manga_id):
    url_api = f"https://api.mangadex.org/manga/{manga_id}/feed"
    
    # Pegamos até 500 capítulos ordenados por número
    params = {
        "translatedLanguage[]": [IDIOMA],
        "order[chapter]": "asc",
        "limit": 500
    }

    print(f"🔄 Buscando lista de capítulos no MangaDex ({IDIOMA})...")
    r = requests.get(url_api, params=params)
    
    if r.status_code == 200:
        return r.json()['data']
    else:
        print(f"❌ Erro na API: {r.status_code}")
        return []

def baixar_capitulo(capitulo_data, pasta_raiz):
    # Extrai dados básicos
    attrs = capitulo_data['attributes']
    cap_num = attrs.get('chapter', 'Oneshot')
    cap_title = attrs.get('title', '') # Pega o título ex: "Sociedade Sangrenta (1)"
    cap_id = capitulo_data['id']
    
    # --- Lógica de Nome da Pasta ---
    # Se tiver título, adiciona no nome da pasta. Se não, usa o ID para evitar duplicata.
    nome_limpo_titulo = limpar_nome(cap_title)
    
    if nome_limpo_titulo:
        nome_pasta_final = f"Capitulo_{cap_num} - {nome_limpo_titulo}"
    else:
        # Se não tiver título, adicionamos o ID curto para diferenciar partes sem nome
        nome_pasta_final = f"Capitulo_{cap_num} [{cap_id[:4]}]"

    caminho_pasta_cap = os.path.join(pasta_raiz, nome_pasta_final)

    # Verifica se já existe
    if os.path.exists(caminho_pasta_cap):
        # Verifica se a pasta tem arquivos dentro
        if len(os.listdir(caminho_pasta_cap)) > 0:
            print(f"⚠️  {nome_pasta_final} já existe. Pulando.")
            return

    os.makedirs(caminho_pasta_cap, exist_ok=True)
    print(f"📥 Baixando: {nome_pasta_final} ...")

    # Obtém link das imagens (At-Home Server)
    r = requests.get(f"https://api.mangadex.org/at-home/server/{cap_id}")
    if r.status_code != 200:
        print("Erro ao comunicar com servidor de imagens.")
        return

    data = r.json()
    base_url = data['baseUrl']
    chapter_hash = data['chapter']['hash']
    imagens = data['chapter']['data']

    # Baixa as imagens
    for i, nome_img in enumerate(imagens):
        url_imagem = f"{base_url}/data/{chapter_hash}/{nome_img}"
        extensao = nome_img.split('.')[-1]
        
        # Nome do arquivo: pag_001.jpg
        caminho_arquivo = os.path.join(caminho_pasta_cap, f"pag_{i+1:03}.{extensao}")

        try:
            img_resp = requests.get(url_imagem, timeout=10)
            with open(caminho_arquivo, 'wb') as f:
                f.write(img_resp.content)
        except Exception as e:
            print(f"   Erro na imagem {i+1}: {e}")
        
        time.sleep(0.1) # Pequena pausa entre imagens

    print(f"✅ Sucesso!")

def main():
    print("=== MangaDex Downloader (Versão Partes Corrigida) ===")
    url_manga = input("URL do Manga: ").strip()
    manga_id = obter_id_manga(url_manga)
    
    if not manga_id:
        print("URL inválida.")
        return

    lista_capitulos = obter_capitulos(manga_id)
    if not lista_capitulos:
        print("Nenhum capítulo encontrado. Tente mudar o IDIOMA no código para 'en' ou 'pt-br'.")
        return

    try:
        inicio = float(input("Do capítulo (número): "))
        fim = float(input("Até o capítulo (número): "))
    except:
        print("Use apenas números (ex: 111).")
        return

    nome_pasta_raiz = f"Downloads_Manga_{manga_id}"
    if not os.path.exists(nome_pasta_raiz):
        os.makedirs(nome_pasta_raiz)

    print(f"\n📂 Salvando tudo em: {nome_pasta_raiz}")
    print("------------------------------------------------")

    count = 0
    for cap in lista_capitulos:
        try:
            # Tenta converter o número do capítulo para float para comparar
            num_str = cap['attributes']['chapter']
            if num_str is None: continue # Pula se for nulo
            
            num_atual = float(num_str)
            
            # Checa se está no intervalo
            if num_atual >= inicio and num_atual <= fim:
                baixar_capitulo(cap, nome_pasta_raiz)
                count += 1
                time.sleep(PAUSE_ENTRE_REQ)
                
        except ValueError:
            # Ignora capítulos que não são números (ex: "Artbook")
            pass

    print(f"\n🎉 Finalizado! {count} pastas criadas.")

if __name__ == "__main__":
    main()