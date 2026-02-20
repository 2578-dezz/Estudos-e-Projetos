import os
import time
import requests
import re
from bs4 import BeautifulSoup

# --- CONFIGURAÇÕES ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://google.com'
}

def limpar_nome_arquivo(nome):
    return re.sub(r'[<>:"/\\|?*]', '', str(nome)).strip()

# ==============================================================================
# CLASSE BASE (TEMPLATE)
# ==============================================================================
class SiteBase:
    def pesquisar(self, termo):
        """Recebe o nome, retorna lista de resultados [{'titulo': 'X', 'url': 'Y'}]"""
        return []

    def obter_capitulos(self, url):
        """Recebe URL do mangá, retorna lista de capítulos"""
        return []
    
    def baixar_imagens(self, url_capitulo, pasta_destino):
        """Baixa as imagens"""
        pass

# ==============================================================================
# SITE 1: MANGADEX (API)
# ==============================================================================
class SiteMangaDex(SiteBase):
    def pesquisar(self, termo):
        print(f"🔍 Pesquisando '{termo}' no MangaDex...")
        url = "https://api.mangadex.org/manga"
        params = {"title": termo, "limit": 10, "contentRating[]": ["safe", "suggestive", "erotica"]}
        
        try:
            r = requests.get(url, params=params)
            data = r.json()['data']
            resultados = []
            for item in data:
                titulo = item['attributes']['title'].get('en') or list(item['attributes']['title'].values())[0]
                # Montamos a URL fake para usar internamente depois
                url_manga = f"https://mangadex.org/title/{item['id']}"
                resultados.append({'titulo': titulo, 'url': url_manga})
            return resultados
        except Exception as e:
            print(f"Erro na pesquisa: {e}")
            return []

    def obter_capitulos(self, url):
        # Extrai ID da URL fake
        manga_id = url.split('/title/')[1]
        
        print("📥 Buscando capítulos (API)...")
        api_url = f"https://api.mangadex.org/manga/{manga_id}/feed"
        # Prioriza PT-BR, depois Inglês
        params = {"translatedLanguage[]": ["pt-br", "en"], "limit": 500, "order[chapter]": "asc"}
        
        r = requests.get(api_url, params=params)
        if r.status_code != 200: return []
        
        lista = []
        for item in r.json()['data']:
            attr = item['attributes']
            num = attr['chapter']
            if num: # Ignora se não tiver número
                lista.append({
                    'numero': num,
                    'url': item['id'], # ID do capitulo
                    'titulo': attr['title'] or "",
                    'tipo': 'api'
                })
        return lista

    def baixar_imagens(self, cap_id, pasta_destino):
        # A URL aqui é apenas o ID do capítulo
        r = requests.get(f"https://api.mangadex.org/at-home/server/{cap_id}")
        if r.status_code != 200: return
        
        data = r.json()
        base_url = data['baseUrl']
        hash_cap = data['chapter']['hash']
        
        for i, img in enumerate(data['chapter']['data']):
            img_url = f"{base_url}/data/{hash_cap}/{img}"
            ext = img.split('.')[-1]
            path = os.path.join(pasta_destino, f"{i+1:03}.{ext}")
            
            with open(path, 'wb') as f:
                f.write(requests.get(img_url).content)
            time.sleep(0.1)

# ==============================================================================
# SITE 2: MANGANATO (HTML)
# ==============================================================================
class SiteManganato(SiteBase):
    def pesquisar(self, termo):
        print(f"🔍 Pesquisando '{termo}' no Manganato...")
        # Manganato usa underscores e remove caracteres especiais
        termo_limpo = re.sub(r'[^a-zA-Z0-9 ]', '', termo).replace(' ', '_')
        url_search = f"https://manganato.com/search/story/{termo_limpo}"
        
        r = requests.get(url_search, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        resultados = []
        # A lista de busca do Manganato
        itens = soup.select('div.search-story-item a.item-title')
        
        for item in itens[:10]: # Pega só os 10 primeiros
            resultados.append({
                'titulo': item.text.strip(),
                'url': item['href']
            })
        return resultados

    def obter_capitulos(self, url):
        print("📄 Lendo lista de capítulos...")
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        lista = []
        # Seletor de capítulos do Manganato
        links = soup.select('ul.row-content-chapter li a.chapter-name')
        
        for link in links:
            url_cap = link['href']
            txt = link.text
            # Extrai número com Regex
            match = re.search(r'Chapter (\d+\.?\d*)', txt)
            num = match.group(1) if match else "0"
            
            lista.append({'numero': num, 'url': url_cap, 'titulo': txt, 'tipo': 'html'})
            
        return lista[::-1] # Inverte para ficar Crescente

    def baixar_imagens(self, url, pasta):
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        div = soup.find('div', class_='container-chapter-reader')
        if not div: return
        
        imgs = div.find_all('img')
        header_img = HEADERS.copy()
        header_img['Referer'] = 'https://manganato.com/' # Anti-Hotlink
        
        for i, img in enumerate(imgs):
            src = img.get('src')
            try:
                res = requests.get(src, headers=header_img)
                with open(os.path.join(pasta, f"{i+1:03}.jpg"), 'wb') as f:
                    f.write(res.content)
                time.sleep(0.2)
            except: pass

# ==============================================================================
# SITE 3: MEDIOCRE SCAN (Atualizado / Mais Robusto)
# ==============================================================================
class SiteMediocre(SiteBase):
    def pesquisar(self, termo):
        print(f"🔍 Pesquisando '{termo}' no MediocreScan...")
        # Tenta a busca padrão do WordPress
        params = {"s": termo, "post_type": "wp-manga"}
        url_search = "https://mediocrescan.site/"
        
        try:
            # verify=False ajuda se o certificado SSL do site for "ruim"
            r = requests.get(url_search, params=params, headers=HEADERS, verify=False)
            
            if r.status_code != 200:
                print(f"⚠️ Erro ao acessar o site: Código {r.status_code}")
                return []

            soup = BeautifulSoup(r.text, 'html.parser')
            
            resultados = []
            # TENTA O SELETOR 1 (Padrão lista)
            itens = soup.select('div.c-tabs-item__content h3 a')
            
            # SELETOR 2 (Caso o layout seja grade)
            if not itens:
                itens = soup.select('div.post-title h3 a')
            
            # SELETOR 3 (Genérico para links de título)
            if not itens:
                itens = soup.select('h3.h4 a')

            for item in itens[:10]:
                resultados.append({
                    'titulo': item.text.strip(),
                    'url': item['href']
                })
            return resultados
        except Exception as e:
            print(f"Erro ao pesquisar: {e}")
            return []

    def obter_capitulos(self, url):
        print("📄 Lendo lista de capítulos...")
        try:
            r = requests.get(url, headers=HEADERS, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            lista = []
            # Seletor padrão de capítulos
            links = soup.select('li.wp-manga-chapter > a')
            
            if not links:
                print("⚠️ Não achei a lista de capítulos. O site pode ter mudado o layout.")
                # Tenta imprimir um pedaço do site para ver se não fomos bloqueados
                if "Just a moment" in soup.text:
                    print("❌ ERRO CRÍTICO: O site tem proteção Cloudflare ativa. O script simples não vai passar.")
                return []

            for link in links:
                url_cap = link['href']
                txt = link.text.strip()
                
                # Tenta extrair número. Se falhar, usa o texto todo.
                match = re.search(r'(\d+)', txt) 
                num = match.group(1) if match else txt
                
                lista.append({'numero': num, 'url': url_cap, 'titulo': txt, 'tipo': 'html'})
            
            return lista[::-1]
        except Exception as e:
            print(f"Erro ao ler capítulos: {e}")
            return []

    def baixar_imagens(self, url, pasta):
        try:
            r = requests.get(url, headers=HEADERS, verify=False)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Tenta achar imagens (Vários lugares possíveis)
            imgs = soup.select('div.reading-content img')
            
            # Se não achar, tenta outro lugar comum
            if not imgs: 
                imgs = soup.select('.page-break img')
            
            if not imgs:
                print("⚠️ Nenhuma imagem encontrada neste capítulo.")
                return

            contador = 0
            for i, img in enumerate(imgs):
                # Pega o link real (muitos sites escondem no data-src)
                src = img.get('data-src') or img.get('src')
                
                if not src: continue
                
                src = src.strip()
                
                try:
                    res = requests.get(src, headers=HEADERS, verify=False, timeout=10)
                    if res.status_code == 200:
                        with open(os.path.join(pasta, f"{i+1:03}.jpg"), 'wb') as f:
                            f.write(res.content)
                        contador += 1
                        time.sleep(0.5) 
                    else:
                        print(f"   - Erro ao baixar imagem {i}: Status {res.status_code}")
                except: 
                    pass
            
            if contador > 0:
                print(f"   ✅ Baixadas {contador} imagens.")
            else:
                print("   ❌ Falha: As imagens foram detectadas mas não baixaram.")
                
        except Exception as e:
            print(f"Erro no download: {e}")

# ==============================================================================
# MENU PRINCIPAL (Lógica de Interação)
# ==============================================================================
def main():
    print("=== ULTRA MANGA DOWNLOADER 2.0 (Busca Automática) ===")
    print("1. MangaDex")
    print("2. Manganato")
    print("3. MediocreScan")
    
    escolha = input("\nEscolha o site: ").strip()
    
    bot = None
    if escolha == '1': bot = SiteMangaDex()
    elif escolha == '2': bot = SiteManganato()
    elif escolha == '3': bot = SiteMediocre()
    else: return

    # --- PASSO 1: PESQUISA ---
    nome_pesquisa = input("Nome do Mangá: ").strip()
    resultados = bot.pesquisar(nome_pesquisa)
    
    if not resultados:
        print("❌ Nenhum mangá encontrado com esse nome.")
        return

    print("\n🔎 Resultados Encontrados:")
    for i, item in enumerate(resultados):
        print(f"[{i+1}] {item['titulo']}")
    
    try:
        idx = int(input("\nQual o número correto? ")) - 1
        manga_escolhido = resultados[idx]
    except:
        print("Opção inválida.")
        return

    print(f"\n📚 Selecionado: {manga_escolhido['titulo']}")
    url_manga = manga_escolhido['url']
    
    # --- PASSO 2: LISTAR CAPÍTULOS ---
    capitulos = bot.obter_capitulos(url_manga)
    if not capitulos:
        print("❌ Nenhum capítulo encontrado ou erro ao carregar página.")
        return

    print(f"✅ Total: {len(capitulos)} capítulos encontrados.")
    print(f"Primeiro: {capitulos[0]['numero']} | Último: {capitulos[-1]['numero']}")
    
    # --- PASSO 3: INTERVALO E DOWNLOAD ---
    try:
        inicio = float(input("Baixar do Cap: "))
        fim = float(input("Até o Cap: "))
    except: return

    nome_pasta_raiz = f"Downloads_{limpar_nome_arquivo(manga_escolhido['titulo'])}"
    if not os.path.exists(nome_pasta_raiz):
        os.makedirs(nome_pasta_raiz)

    print(f"\n🚀 Iniciando downloads em: {nome_pasta_raiz}")
    
    for cap in capitulos:
        try:
            num = float(cap['numero'])
            if num >= inicio and num <= fim:
                nome_pasta = f"Cap_{cap['numero']}"
                caminho_final = os.path.join(nome_pasta_raiz, nome_pasta)
                
                if not os.path.exists(caminho_final):
                    os.makedirs(caminho_final)
                    print(f"📥 Baixando Cap {cap['numero']}...")
                    bot.baixar_imagens(cap['url'], caminho_final)
                else:
                    print(f"⏩ Cap {cap['numero']} já existe.")
        except ValueError:
            pass 

    print("\n✨ Processo Finalizado!")

if __name__ == "__main__":
    main()