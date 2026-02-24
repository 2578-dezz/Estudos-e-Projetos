#Bibliotecas usadas para o projeto 


#Bibliotecas do drive
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
#Biblioteca para as requisições a API do Tiny
import requests
#Bibliotecas para as pesquisas que envolvem tempo
from datetime import datetime, timedelta
import re
import time

import os

#Biblioteca para enganar o python caso vc perca um dia de trabalho tentando arrumar o script
from freezegun import freeze_time


#Informações essenciais

ID_PASTA_DRIVE = "1aMEO1ZmTO8zukrl3e_Uf10zgA19QS-RH" 

TOKEN_TINY = os.getenv("TOKEN_TINY") #Aqui eu utilizo a biblioteca "os" para importar do meu windows a variavel de ambiente "Token Tiny"


if not TOKEN_TINY:
    print("ERRO CRÍTICO: Token não encontrado nas variáveis de ambiente!")
    exit()

#Aqui tambem utilizo a biblioteca "os"
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CREDENCIAIS = os.path.join(DIRETORIO_ATUAL, "creds.json")

COLUNA_DATA_INDEX = 1  
COLUNA_QTD_INDEX = 3   



#conexão com o Drive
def conectar_google():
    print(" Conectando ao Google")
    
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

#Encontrando as planilhas de acordo com a definição que eu criei que seria por SKU

def encontrar_planilha_por_sku(service_drive, sku):
    
    termo = sku[:4] if len(sku) >= 4 else sku
    
    try:
        
        query = (
            f"'{ID_PASTA_DRIVE}' in parents and "
            f"(mimeType='application/vnd.google-apps.spreadsheet' or "
            f"mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
            f"mimeType='application/vnd.ms-excel.sheet.macroEnabled.12') and "
            f"trashed=false"
        )
        
        results = service_drive.files().list(
            q=query, 
            fields="files(id, name)",
            supportsAllDrives=True, 
            includeItemsFromAllDrives=True
        ).execute()
        
        arquivos = results.get('files', [])
        
        
        candidatos = [f for f in arquivos if termo in f['name']]
        
        return candidatos
    except Exception as e:
        print(f" Erro na busca do Drive: {e}")
        return []


def processar_sku_kit(sku_original, quantidade_vendida):
    sku_limpo = str(sku_original).strip().upper()
    
    if sku_limpo.endswith("K36") or sku_limpo.endswith("K9"):
        return sku_limpo, quantidade_vendida
    

    
    if sku_limpo in ['PI0601', 'PI0602']:
        return sku_limpo, quantidade_vendida * 6
    
    
    match = re.search(r"^(.*)K(\d+)$", sku_limpo)
    
    if match:
        sku_base = match.group(1)       
        multiplicador = int(match.group(2)) 
        return sku_base, quantidade_vendida * multiplicador
    
    return sku_limpo, quantidade_vendida

def buscar_vendas_tiny(data_alvo):
   
    if isinstance(data_alvo, str):
        data_str = data_alvo
    else:
        data_str = data_alvo.strftime("%d/%m/%Y")
    
    print(f"🔄 Consultando Tiny dia {data_str}...")
    
    url_pesquisa = "https://api.tiny.com.br/api2/pedidos.pesquisa.php"
    url_detalhe = "https://api.tiny.com.br/api2/pedido.obter.php"
    
    pagina = 1
    resumo_vendas = {} 
    
    
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
                
              
                status_ignorados = ['Em aberto', 'Dados incompletos', 'Cancelado']
                situacao = p.get('situacao', '')
                
                if situacao in status_ignorados:
                    continue #
                
                id_ped = p['id']
                
            
                try:
                    r_det = requests.post(url_detalhe, data={"token": TOKEN_TINY, "id": id_ped, "formato": "JSON"})
                    if r_det.status_code != 200: continue
                    
                    itens = r_det.json().get('retorno', {}).get('pedido', {}).get('itens', [])
                    
                    for obj in itens:
                        sku = obj['item']['codigo']
                        qtd = float(obj['item']['quantidade'])
                        
                        
                        sku_final, qtd_final = processar_sku_kit(sku, qtd)
                        
                        
                        resumo_vendas[sku_final] = resumo_vendas.get(sku_final, 0) + qtd_final
                except Exception as e_det:
                    print(f"⚠️ Erro ao ler pedido {id_ped}: {e_det}")
                    pass 
            
            pagina += 1
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"❌ Erro conexão Tiny na página {pagina}: {e}")
            break
            
    return resumo_vendas


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
        print("Dia comum: buscar vendas de ontem")
        datas_para_processar.append(hoje - timedelta(days=1))


    client_sheets, service_drive = conectar_google()
    if not client_sheets: return

   
    for data_alvo in datas_para_processar:
        data_str = data_alvo.strftime("%d/%m/%Y")
        print(f"\n--- INICIANDO ATUALIZAÇÃO PARA O DIA: {data_str} ---")

        
        vendas = buscar_vendas_tiny(data_alvo)
        
        if not vendas: 
            print(f" Sem vendas válidas no Tiny para o dia {data_str}.")
            continue 
        
        for sku_venda, qtd in vendas.items():
            print(f"\n SKU '{sku_venda}' (Qtd: {qtd})...")
            
            
            arquivos_candidatos = encontrar_planilha_por_sku(service_drive, sku_venda)
            
            if not arquivos_candidatos:
                print(f"      ❌ Nenhum arquivo encontrado com '{sku_venda[:4]}' no nome.")
                continue

            sku_atualizado = False
            
            for arquivo in arquivos_candidatos:
                try:
                    sh = client_sheets.open_by_key(arquivo['id'])
                    
                    for aba in sh.worksheets():
                       
                        if aba.title.strip().upper().startswith(sku_venda.upper()):
                            print(f"ACHEI! Arquivo: '{arquivo['name']}' | Aba: '{aba.title}'")
                            
                            datas = aba.col_values(COLUNA_DATA_INDEX)
                            linha = -1
                            
                         
                            for i, v in enumerate(datas):
                                if data_str in str(v):
                                    linha = i + 1
                                    break
                            
                            if linha > 0:
                                aba.update_cell(linha, COLUNA_QTD_INDEX, qtd)
                                print(f"        ✅ SUCESSO! Atualizado.")
                            else:
                                print(f"        ⚠️ Data {data_str} não encontrada na aba.")
                            
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
    #with freeze_time("2026-02-09"):  #Se quiser rodar o freeze com uma data especifica basta alterar aqui para a data necessaria e descomentar.
        #print({datetime.now()})#
