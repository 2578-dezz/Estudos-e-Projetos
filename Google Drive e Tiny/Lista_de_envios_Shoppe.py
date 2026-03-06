import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import time

PASTA_ID_FULL = "1FlCl6QmAtwCCjOpzc58gghvW7FXa6Rr_"
ARQUIVOS_CREDENCIAIS = "creds.json"
NOME_MESES = [
    "", "01-jan", "02-fev", "03-mar", "04-abr", "05-mai", "06-jun",
    "07-jul", "08-ago", "09-set", "10-out", "11-nov", "12-dez"
]



def conectar_google_services():
    print("   ...Autenticando...")
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(ARQUIVOS_CREDENCIAIS, scopes=escopos)
    return build('drive', 'v3', credentials=creds), gspread.authorize(creds)

#ENTRAR NA PASTA ID FULL, PROCURAR O MES QUE ESTAMOS E DEBNTRO DO MES QUE ESTAMOS ACHAR A PASTA QUE TEM AT NO FIM DO NOME
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





#APOS ENTRAR NA PASTA COM AT NO FIM DO NOME ELE VAI ENCONTRAR O ARQUIVO "FULL PRONTO"
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


#DENTRO DO ARQUIVO FULL PRONTO NA ABA DE "CONSULTA INTEGRAÇÃO" PEGAR OS VALORES DAS CELULAS A3:A100;B3:B100 E PASSAR PARA OUTRA PLANILHA
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

  file_meta = service.files().get(fileId=id_origem_resumo, fields="parents", supportsAllDrives=True).execute()
  id_pasta_dia = file_meta['parents'][0]
  print("Buscando arquivo Lista de envios")
  arq_lista_de_envios = buscar_id_pasta_ou_arquivo(service, id_pasta_dia, "LISTA DE ENVIOS", "application/vnd.google-apps.spreadsheet")

  if not arq_lista_de_envios:
      print("Arquivo de lista de envios não encontrado na mesma pasta")
      return 
  sh_destino = client.open_by_key(arq_lista_de_envios['id'])

  #aba_destino = sh_destino.getworksheet(0)
  try:
      aba_destino = sh_destino.worksheet(0)  
  except:
      aba_destino = sh_destino.get_worksheet(0)
  print(f"Distribuindo dados na aba{aba_destino.title}")
  
  valores_para_inserir = []
  for i in range(min(len(lista_cargas),98)):
      sku = lista_cargas[i][0]
      qtd = lista_cargas[i][1]
      qtd_numerica = int(float(qtd))
      valores_para_inserir.append([sku , qtd_numerica]) 
  if valores_para_inserir:
      intervalo = f"M2:N{2 + len(valores_para_inserir)}"
      aba_destino.update(range_name=intervalo, values=valores_para_inserir, value_input_option='USER_ENTERED')
      print("Sucesso!")
  else:
      print("Nenhum dado encontrado para transferencia")      

#APÓS PEGAR OS DADOS, DENTRO DA MESMA PASTA PROCURAR O ARQUIVO "LISTA DE ENVIOS" E PASSAR OS DADOS DA "CONSULTA INTEGRAÇÃO" PARA AS CELULAS M3:M100;N3:N100
if __name__ == "__main__":
    service, client_sheets = conectar_google_services()
    arquivo_pronto = atualizar_lista_de_envios(service)
    
    if arquivo_pronto:
        distribuir_dados(service, client_sheets, arquivo_pronto['id'])
    else:
        print("  Não foi possível encontrar o fluxo de pastas até o 'FULL PRONTO'.")
