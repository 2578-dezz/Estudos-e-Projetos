import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import requests
from datetime import datetime, timedelta
import re
import time
import os

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================

# ID DA PASTA FINAL (Onde estão as planilhas)
ID_PASTA_DRIVE = "15t19SkCGxTKv7InSXkepOBI_ALZc-Vx8" 

# TOKEN DO TINY
TOKEN_TINY = ""

# Caminho das credenciais
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CREDENCIAIS = os.path.join(DIRETORIO_ATUAL, "creds.json")

# Configuração das Colunas 
COLUNA_DATA_INDEX = 1  # Coluna A (Onde procura a data)
COLUNA_QTD_INDEX = 3   # Coluna C (Onde escreve a quantidade)

# ==============================================================================
# 2. CONEXÃO GOOGLE
# ==============================================================================
def conectar_google():
    print("☁️ Conectando ao Google...")
    
    if not os.path.exists(ARQUIVO_CREDENCIAIS):
        print("❌ ERRO CRÍTICO: Arquivo 'creds.json' não encontrado na pasta.")
        return None, None

    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_file(ARQUIVO_CREDENCIAIS, scopes=escopos)
        client = gspread.authorize(creds)
        service_drive = build('drive', 'v3', credentials=creds)
        return client, service_drive
    except Exception as e:
        print(f"❌ Erro conexão Google: {e}")
        return None, None

def encontrar_planilha_por_sku(service_drive, sku):
    
    termo = sku[:4] if len(sku) >= 4 else sku
    
    try:
        # Filtro para ver Excel (.xlsx), Macro (.xlsm) e Google Sheets
        query = (
            f"'{folder_id}' in parents and "
            f"(mimeType='application/vnd.google-apps.spreadsheet' or "
            f"mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
            f"mimeType='application/vnd.ms-excel.sheet.macroEnabled.12') and "
            f"trashed=false"
        )
        results = service_drive.files().list(q=query, fields="files(id, name)",supportsAllDrives=True, 
        includeItemsFromAllDrives=True).execute()
        arquivos = results.get('files', [])
        
        arquivos = results.get('files', [])
        
        # Filtro extra Python: Garante que o termo está mesmo no nome
        candidatos = [f for f in arquivos if termo in f['name']]
        
        return candidatos
    except:
        return []
        
       

# ==============================================================================
# 3. LÓGICA DE NEGÓCIO (TINY + KITS)
# ==============================================================================
def processar_sku_kit(sku_original, quantidade_vendida):
    sku_limpo = str(sku_original).strip().upper()
    
    if sku_limpo.endswith("K36") or sku_limpo.endswith("K9"):
        return sku_limpo, quantidade_vendida
    
    # Procura padrão K + Número (ex: PI0101K10)
    match = re.search(r"^(.*)K(\d+)$", sku_limpo)
    
    if match:
        sku_base = match.group(1)       
        multiplicador = int(match.group(2)) 
        return sku_base, quantidade_vendida * multiplicador
    
    return sku_limpo, quantidade_vendida

def buscar_vendas_tiny(data_alvo):
    data_str = data_alvo.strftime("%d/%m/%Y")
    # data_str = "18/01/2026" #forçar uma data de teste
    
    print(f"🔄 Consultando Tiny dia {data_str}...")
    
    url_pesquisa = "https://api.tiny.com.br/api2/pedidos.pesquisa.php"
    url_detalhe = "https://api.tiny.com.br/api2/pedido.obter.php"
    
    pagina = 1
    resumo_vendas = {} 
    
    # --- LOOP DE PAGINAÇÃO (Para alto volume) ---
    while True:
        payload = {
            "token": TOKEN_TINY,
            "dataInicial": data_str,
            "dataFinal": data_str,
            "formato": "JSON",
            "pagina": pagina
        }
        
        try:
            resp = requests.post(url_pesquisa, data=payload)
            dados = resp.json()
            
           
            if dados.get('retorno', {}).get('status') == 'Erro':
                break 
            
            pedidos = dados['retorno'].get('pedidos', [])
            if not pedidos: break 
            
            print(f"   📄 Página {pagina}: Processando {len(pedidos)} pedidos...")

            for item in pedidos:
                p = item['pedido']
                # Filtro de Status
                status_ignorados: list[str] = ['Em aberto', 'Dados incompletos', 'Cancelado']
                
            
             

                id_ped = p['id']
                
                # Chama detalhes para ver itens
                try:
                    r_det = requests.post(url_detalhe, data={"token": TOKEN_TINY, "id": id_ped, "formato": "JSON"})
                    if r_det.status_code != 200: continue
                    
                    itens = r_det.json().get('retorno', {}).get('pedido', {}).get('itens', [])
                    
                    for obj in itens:
                        sku = obj['item']['codigo']
                        qtd = float(obj['item']['quantidade'])
                        
                        # Processa Kit
                        sku_final, qtd_final = processar_sku_kit(sku, qtd)
                        
                        # Soma no resumo total
                        resumo_vendas[sku_final] = resumo_vendas.get(sku_final, 0) + qtd_final
                except:
                    pass # Se falhar um pedido, continua
            
            pagina += 1
            time.sleep(0.5) # Respira para não travar
            
        except Exception as e:
            print(f"❌ Erro conexão Tiny: {e}")
            break
            
    return resumo_vendas

# ==============================================================================
# 4. EXECUTOR PRINCIPAL
# ==============================================================================
def rodar_atualizacao():
    hoje = datetime.now()
    dia_da_semana = hoje.weekday()
    
    datas_para_processar = []
    
    if dia_da_semana == 0:
        print("Hoje é segunda! Processar vendas do fim de semana (Sexta, Sábado e Domingo).")
        
        for i in [3, 2, 1]:
            data_alvo = hoje - timedelta(days=i)
            datas_para_processar.append(data_alvo)
    else:
        print("Dia comum buscar vendas de ontem")
        datas_para_processar.append(hoje-timedelta(days=1))

     # 2. Conecta Google
    client_sheets, service_drive = conectar_google()
    if not client_sheets: return

    # 3. Lista Planilhas
    encontrar_planilha_por_sku = service_drive,(service_drive, ID_PASTA_DRIVE)
    if not  encontrar_planilha_por_sku: return

    # 4. Processa cada SKU vendido
    for data_alvo in datas_para_processar:
        data_str = data_alvo.strftime("%d/%m/%Y")
        print(f"\n--- 🚀 INICIANDO ATUALIZAÇÃO PARA O DIA: {data_str} ---")

        # Pega vendas do Tiny para ESTA data específica
        vendas = buscar_vendas_tiny(data_str)
        if not vendas: 
                print(f"⚠️ Sem vendas no Tiny para o dia {data_str}.")
                continue # Pula para a próxima data da lista
        
        for sku_venda, qtd in vendas.items():
            print(f"\n📦 SKU '{sku_venda}' (Qtd: {qtd})...")
            
            # --- CORREÇÃO: USANDO A BUSCA POR NOME ---
            # Em vez de listar tudo, procuramos só arquivos que tenham a ver com o SKU
            arquivos_candidatos = encontrar_planilha_por_sku(service_drive, sku_venda)
            
            if not arquivos_candidatos:
                print(f"      ❌ Nenhum arquivo encontrado com '{sku_venda[:4]}' no nome.")
                continue

            sku_atualizado = False
            
            for arquivo in arquivos_candidatos:
                try:
                    sh = client_sheets.open_by_key(arquivo['id'])
                    
                    for aba in sh.worksheets():
                        if aba.title.strip().startswith(sku_venda):
                            print(f"      📍 ACHEI! Arquivo: '{arquivo['name']}' | Aba: '{aba.title}'")
                            
                            datas = aba.col_values(COLUNA_DATA_INDEX)
                            linha = -1
                            for i, v in enumerate(datas):
                                if data_str in str(v):
                                    linha = i + 1
                                    break
                            
                            if linha > 0:
                                aba.update_cell(linha, COLUNA_QTD_INDEX, qtd)
                                print(f"         ✅ SUCESSO! Atualizado.")
                            else:
                                print(f"         ⚠️ Data não encontrada.")
                            
                            sku_atualizado = True
                            break 
                    if sku_atualizado: break
                except Exception as e:
                    print(f"      ⚠️ Erro ao abrir '{arquivo['name']}': {e}")
            
            if not sku_atualizado:
                print(f"      ❌ Aba não encontrada nos arquivos candidatos.")
                
            time.sleep(1)

    print("\n✅ FIM DO PROCESSO.")

if __name__ == "__main__":
    rodar_atualizacao()
