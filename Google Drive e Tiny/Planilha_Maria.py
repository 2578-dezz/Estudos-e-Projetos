#import
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import time
import re

#VALORES
PASTA_ID_FULL = "1FlCl6QmAtwCCjOpzc58gghvW7FXa6Rr_"
ARQUIVOS_CREDENCIAIS = "creds.json"
NOME_MESES = [
    "", "01-jan", "02-fev", "03-mar", "04-abr", "05-mai", "06-jun",
    "07-jul", "08-ago", "09-set", "10-out", "11-nov", "12-dez"
]
#conexão google
def conectar_google_services():
    print("   ...Autenticando...")
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(ARQUIVOS_CREDENCIAIS, scopes=escopos)
    return build('drive', 'v3', credentials=creds), gspread.authorize(creds)
#Pegar os SKUs da aba de consulta integração
def calcular_qtd_real(sku, qtd_inicial):
    sku = (sku).upper().strip()
    qtd = int(float(qtd_inicial))
    match = re.search(r'K(\d+)', sku)
    if not match: return qtd
    numero_k = int(match.group(1))

    if sku.startswith(("PI01", "PI05", "PI02")):
        fator = numero_k // 10
        return qtd * fator
    if sku.startswith(("PA03")):
        fator = numero_k // 8
        return qtd * fator
    if sku.startswith(("PI08")):
        fator = numero_k // 5
        return qtd * fator
    if sku.startswith(("PI06")):
        fator = numero_k // 6
        return qtd * fator
    if sku.startswith(("PI04")):
        return qtd
    
    return qtd * numero_k

def altera_sku_atual(sku):
    sku = (sku).upper()
    if not re.search(r'K\d+', sku): return sku

    if sku.startswith(("PI01", "PI05", "PI02")):
        return re.sub(r'K\d+', 'K10', sku)
    if sku.startswith(("PA03")):
        return re.sub(r'K\d+', 'K8', sku)
    if sku.startswith(("PI06")):
        return re.sub(r'K\d+', 'K6', sku)
    if sku.startswith(("PI08")):
        return re.sub(r'K\d+', 'K5', sku)
    if sku.endswith(("K9", "K36")):
        return sku
    if "COMK" in sku:
        return re.sub(r'COMK\d+', 'com1', sku)
    return re.sub(r'K\d+', '', sku).strip()



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

def atualizar_lista_de_envios(service):    
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

def distribuir_dados(service,client,id_origem_resumo):
  print("\n INICIANDO DISTRIBUIÇÃO...")
    
  sh_origem = client.open_by_key(id_origem_resumo)
  aba_consulta = sh_origem.get_worksheet(1) 
  print(f"   Lendo dados da aba: {aba_consulta.title}")

  dados = aba_consulta.get_all_values()
  lista_cargas = []
  for linha in dados[2:]:
     if len(linha) >= 2 and linha[0]:
            sku = linha[0].strip()
            qtd = linha[1].strip()
            if sku and qtd: lista_cargas.append((sku, qtd))

  


  try:
      aba_destino = sh_origem.worksheet(2)  
  except:
      aba_destino = sh_origem.get_worksheet(2)
  print(f"Distribuindo dados na aba{aba_destino.title}")
  
  valores_para_inserir = []
  for i in range(min(len(lista_cargas),98)):
      sku_atual = lista_cargas[i][0]
      qtd_atual = lista_cargas[i][1]
      sku_final = altera_sku_atual (sku_atual)
      qtd_final = calcular_qtd_real(sku_atual, qtd_atual)   
      valores_para_inserir.append([sku_final , qtd_final]) 
  if valores_para_inserir:
      intervalo = f"A74:B{74 + len(valores_para_inserir)}"
      aba_destino.update(range_name=intervalo, values=valores_para_inserir, value_input_option='USER_ENTERED')
      print("Sucesso!")
  else:
      print("Nenhum dado encontrado para transferencia")      

if __name__ == "__main__":
    
    service_drive, client_sheets = conectar_google_services()
    
    resultado_busca = atualizar_lista_de_envios(service_drive)

    if resultado_busca:
        print(f"✅ Arquivo encontrado: {resultado_busca['name']}")

    distribuir_dados(service_drive, client_sheets, resultado_busca['id'])

else:
    print("Não foi possivel atualizar")


