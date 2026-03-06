#imports
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import time
import re
from gspread.cell import Cell

PASTA_ID_FULL = "1FlCl6QmAtwCCjOpzc58gghvW7FXa6Rr_"
ARQUIVOS_CREDENCIAIS = "creds.json"
NOME_MESES = [
    "", "01-jan", "02-fev", "03-mar", "04-abr", "05-mai", "06-jun",
    "07-jul", "08-ago", "09-set", "10-out", "11-nov", "12-dez"
]





#Conexao Google service

def conectar_google_services():
    print("   ...Autenticando...")
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(ARQUIVOS_CREDENCIAIS, scopes=escopos)
    return build('drive', 'v3', credentials=creds), gspread.authorize(creds)

#Entrar na pasta do dia com final AT

def buscar_id_pasta_ou_arquivo(service, parent_id, nome_contem, mime_type=None):
     q = f"'{parent_id}' in parents and name contains '{nome_contem}' and trashed = false"
     if mime_type:
        if mime_type == "excel_ou_sheet":
            q += " and (mimeType = 'application/vnd.google-apps.spreadsheet' or mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')"
        else:
            q += f" and mimeType = '{mime_type}'"
     res = service.files().list(q=q, fields="files(id, name, mimeType)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
     items = res.get('files', [])
     return items[0] if items else None






#Encontrar planilha de FULL Pronto
def planilha_FULL_Pronto(service):    
     hoje = datetime.now()
     meses = ["", "01-jan", "02-fev", "03-mar", "04-abr", "05-mai", "06-jun", "07-jul", "08-ago", "09-set", "10-out", "11-nov", "12-dez"]
     nome_mes = meses[hoje.month]
    
     print(f" 1. Buscando pasta do mês: {nome_mes}...")
     pasta_mes = buscar_id_pasta_ou_arquivo(service, PASTA_ID_FULL, nome_mes, "application/vnd.google-apps.folder")
     if not pasta_mes: return None
    
     print("2. Buscando pasta 'AT'...")
     pasta_at = buscar_id_pasta_ou_arquivo(service, pasta_mes['id'], "AT", "application/vnd.google-apps.folder")
     if not pasta_at: return None
    
     print(" 3. Buscando arquivo 'FULL PRONTO'...")
     arq_pronto = buscar_id_pasta_ou_arquivo(service, pasta_at['id'], "FULL PRONTO", "application/vnd.google-apps.spreadsheet")
     return arq_pronto



#se o SKU começar com PI01, PI05 ignorar
#se o SKU contiver medidas "50x50" "100x50" ignorar

def sku_validos(sku):   
    sku = (sku).upper()


    if sku.startswith(("PI01","PI05",)):
        return False
    
    for medida in ["50X50", "25X25"]:
        if medida in sku:
            return False

    match_medida = re.search(r'(\d+[xX]\d+)', sku, re.IGNORECASE)
    if match_medida:
        return False
    
    return True








#Encontrar aba Consulta maria
#Pegar os skus iguais e somar
def somar_skus(service,client,id_origem_resumo):
  print("Iniciando distribuição!")
  sh_origem = client.open_by_key(id_origem_resumo)
  aba_consulta = sh_origem.get_worksheet(2) 
  print(f"   Lendo dados da aba: {aba_consulta.title}")

  dados = aba_consulta.get_all_values()
   

  soma_dos_skus = {}

  lista_cargas = []
  for linha in dados[73:]:
     if len(linha) >= 2 and linha[0]:
            sku = linha[0].strip()
        

            try:
                qtd = int(linha[1].strip())

            except ValueError:
                continue

            if sku_validos(sku):
             
                if sku in soma_dos_skus:
                    soma_dos_skus[sku] += qtd
              
                else:
                    soma_dos_skus[sku] = qtd
#Após somar, ele vai entrar na 3 aba e procurar o nome dos skus que ele somou e escrever na mesma linha porem na coluna da frente

  aba_destino = sh_origem.get_worksheet(3)
  print(f"   Escrevendo na aba: {aba_destino.title}")
        
       
  dados_destino = aba_destino.get_all_values()  
  batch_updates = []
  for indice, item in enumerate(dados_destino):
         if len(item) > 0:
             sku_da_planilha  = item[0].strip().upper()
             linha_alvo = indice + 1
      
             if sku_da_planilha in soma_dos_skus:
                quantidade_final = soma_dos_skus[sku_da_planilha]
                

                batch_updates.append({'range': f'B{linha_alvo}', 'values': [[quantidade_final]]})


             if len(item) > 5:
                sku_da_planilha  = item[5].strip().upper()
                if sku_da_planilha in soma_dos_skus:
                   quantidade_final = soma_dos_skus[sku_da_planilha]  
                   batch_updates.append({'range': f'G{linha_alvo}', 'values': [[quantidade_final]]})
  if batch_updates:
            aba_destino.batch_update(batch_updates, value_input_option='USER_ENTERED')
            print(f"Sucesso! {len(batch_updates)} células atualizadas!.")




if __name__ == "__main__":
    service_drive, client_sheets = conectar_google_services()
    

    info_planilha = planilha_FULL_Pronto(service_drive)
    
    if info_planilha:
        id_real = info_planilha['id']
        print(f"✅ Iniciando processamento da planilha: {info_planilha['name']}")
        
  
        somar_skus(service_drive, client_sheets, id_real)
    else:
        print("❌ Falha: Não consegui localizar a planilha 'FULL PRONTO' automaticamente.") 