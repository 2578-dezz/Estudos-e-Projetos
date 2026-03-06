import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import re
import time


PLANILHA_ENVIOS_FULL = ""
PASTA_ID_FULL = ""
ARQUIVOS_CREDENCIAIS = "creds.json" 

NOME_MESES = [
    "", "01-jan", "02-fev", "03-mar", "04-abr", "05-mai", "06-jun",
    "07-jul", "08-ago", "09-set", "10-out", "11-nov", "12-dez"
]

def conectar_google_services():
    print("   ...Autenticando credenciais...")
    escopos = [     
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(ARQUIVOS_CREDENCIAIS, scopes=escopos)
    service_drive = build('drive', 'v3', credentials=creds)
    client_sheets = gspread.authorize(creds)
    return service_drive, client_sheets

def atualizar_full_atual(service_drive):    
    hoje = datetime.now()
    mes_atual = hoje.month
    texto_data = hoje.strftime("%d/%m")
    
    id_pai = PASTA_ID_FULL
    nome_busca = NOME_MESES[mes_atual]

    
    print(f" 1. Procurando pasta do mês: '{nome_busca}' em '{id_pai}'...")
    query_mes = f"'{id_pai}' in parents and name contains '{nome_busca}' and trashed = false"
    
    
    results_mes = service_drive.files().list(
        q=query_mes, 
        fields="files(id, name)",
        supportsAllDrives=True,        
        includeItemsFromAllDrives=True 
    ).execute()
    
    items_mes = results_mes.get('files',[])

    if not items_mes:
        print(f"❌ ERRO: Pasta do mês '{nome_busca}' não encontrada.")
        print("DICA: Verifique se você compartilhou a PASTA '1FlCl...' com o email do robô!")
        return None

    id_mes_encontrado = items_mes[0]['id']
    print(f"   ✅ Mês encontrado: {items_mes[0]['name']}")

    
    print(f"🔎 2. Procurando pasta do dia '{texto_data}' com 'AT'...")
    query_dia = f"'{id_mes_encontrado}' in parents and name contains 'AT' and trashed = false"
    
    results_dia = service_drive.files().list(
        q=query_dia, 
        fields="files(id, name)",
        supportsAllDrives=True,        
        includeItemsFromAllDrives=True 
    ).execute()
    
    items_dia = results_dia.get('files',[])
    
    if not items_dia:
        print(f"❌ Pasta do dia {texto_data} AT não encontrada.")
        return None
    
    id_pasta_dia = items_dia[0]['id']
    print(f"   ✅ Dia encontrado: {items_dia[0]['name']}")

    
    nome_arquivo = "FULL PRONTO" 
    print(f" 3. Procurando arquivo '{nome_arquivo}'...")
    
    query_arq = f"'{id_pasta_dia}' in parents and name contains '{nome_arquivo}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    
    results_arq = service_drive.files().list(
        q=query_arq, 
        fields="files(id, name)",
        supportsAllDrives=True,        
        includeItemsFromAllDrives=True 
    ).execute()
    
    items_arq = results_arq.get('files', [])

    if not items_arq:
        print(f"❌ Arquivo '{nome_arquivo}' não encontrado na pasta do dia.")
        return None
    
    planilha_alvo = items_arq[0]
    print(f"✅ SUCESSO! Planilha Encontrada: {planilha_alvo['name']}")
    
    return planilha_alvo['id']



def transferencia_de_dados(client, id_origem, id_destino):
    print(f" Abrindo planilhas")
    aba_origem = client.open_by_key(id_origem).get_worksheet(1)
    aba_destino = client.open_by_key(id_destino).get_worksheet(0)
    


    dados_origem = aba_origem.get_all_values()

    INDICE_ARM = 1
    INDICE_SKU = 4
    INDICE_QNT = 13

    lista_coluna_B = []
    lista_coluna_C = []
    lista_coluna_D = [] 
    
    dados_temporarios = []   

    print("Processando SKU e Quantidades") 

    for linha in dados_origem[1:]:

        if len(linha) <= INDICE_QNT:
            continue
    
        sku_sujo = linha[INDICE_SKU]
        sku_limpo = sku_sujo.split('-')[0].split('P16')[0].strip()
       

        id_armazen = linha[INDICE_ARM]

        qtd_texto = linha[INDICE_QNT]
        if qtd_texto.isdigit():
            qtd_num = int(qtd_texto)
        else:
            qtd_num = 0
        
        if qtd_num % 2 != 0:
            qtd_final = qtd_num + 1
        else:
            qtd_final = qtd_num
        
        if qtd_final>0:
            dados_temporarios.append((sku_limpo, id_armazen, qtd_final))
    
    dados_temporarios.sort(key=lambda x: x[0])
    
    lista_coluna_B = []
    lista_coluna_C = []
    lista_coluna_D = []

    prefixo_anterior = None

    print("formatando agrupação")

    for sku, id_arm, qtd in dados_temporarios:
        prefixo_atual  = sku[:4]

        if prefixo_anterior is not None and prefixo_atual != prefixo_anterior:
            lista_coluna_B.append([""]) 
            lista_coluna_C.append([""]) 
            lista_coluna_D.append([""])
        lista_coluna_B.append([id_arm]) 
        lista_coluna_C.append([sku]) 
        lista_coluna_D.append([qtd])

        prefixo_anterior = prefixo_atual

    if lista_coluna_B:
        total_linhas = len(lista_coluna_B)
        print(f" Escrevendo {total_linhas} linhas no topo da planilha...")

        range_B = f"B2:B{total_linhas + 1}"
        range_C = f"C2:C{total_linhas + 1}"
        range_D = f"D2:D{total_linhas + 1}"

        aba_destino.update(range_name=range_B, values=lista_coluna_B)
        aba_destino.update(range_name=range_C, values=lista_coluna_C)
        aba_destino.update(range_name=range_D, values=lista_coluna_D)
    else:
        print("Nenhum dado enviado (lista vazia).")


def transferencia_de_resumo(client, id_origem , id_destino):
    print(f" Abrindo segunda planilha")
    aba_origem = client.open_by_key(id_origem).get_worksheet(1)
    aba_destino_resumo = client.open_by_key(id_destino).get_worksheet(1)
    dados_origem = aba_origem.get_all_values()
    
    INDICE_SKU = 4
    INDICE_QNT = 13

    agrupado = {}
    
    for linha in dados_origem[1:]:

        if len(linha) <= INDICE_QNT:
            continue
    
        sku_sujo = linha[INDICE_SKU]
        sku_limpo = sku_sujo.split('-')[0].split('P16')[0].strip()

        qtd_texto = linha[INDICE_QNT]
        if qtd_texto.isdigit():
            qtd_num = int(qtd_texto)
        else:
            qtd_num = 0
        
        if qtd_num % 2 != 0:
            qtd_final = qtd_num + 1
        else:
            qtd_final = qtd_num
        
        if qtd_final>0:
            if sku_limpo in agrupado:
                agrupado[sku_limpo] += qtd_final
            else:
                agrupado[sku_limpo] = qtd_final

    dados_finais = []

    for sku, total in agrupado.items():
        dados_finais.append((sku,total))

    dados_finais.sort(key=lambda x: x[0])
   
    lista_coluna_A = []
    lista_coluna_B = []

    prefixo_anterior = None

    for sku, qtd in dados_finais:
        prefixo_atual = sku[:4]
        if prefixo_anterior and prefixo_atual != prefixo_anterior:
            lista_coluna_A.append([""])
            lista_coluna_B.append([""])
        lista_coluna_A.append([sku])
        lista_coluna_B.append([qtd])

        prefixo_anterior = prefixo_atual


    if lista_coluna_B:
        total_linhas = len(lista_coluna_B)
        print(f"🚀 Escrevendo {total_linhas} linhas...")
        
        range_A = f"A3:A{total_linhas + 2}"
        range_B = f"B3:B{total_linhas + 2}"

      
        aba_destino_resumo.update(range_name=range_A, values=lista_coluna_A)
        aba_destino_resumo.update(range_name=range_B, values=lista_coluna_B)
        print("RESUMO ATUALIZADO")
    else:
        print("nenhum dado para")

def consulta_integração(client, id_origem , id_destino):
    print(f" Abrindo segunda planilha")
    aba_origem = client.open_by_key(id_origem).get_worksheet(1)
    aba_destino_resumo = client.open_by_key(id_destino).get_worksheet(1)
    dados_origem = aba_origem.get_all_values()
    
    INDICE_SKU = 4
    INDICE_QNT = 13

    agrupado = {}
    
    for linha in dados_origem[1:]:

        if len(linha) <= INDICE_QNT:
            continue
    
        sku_sujo = linha[INDICE_SKU]
        sku_limpo = sku_sujo.split('-')[0].split('P16')[0].strip()

        if "quadratto" in sku_limpo.lower():
            sku_limpo = "cadre"

        qtd_texto = linha[INDICE_QNT]
        if qtd_texto.isdigit():
            qtd_num = int(qtd_texto)
        else:
            qtd_num = 0
        
        if qtd_num % 2 != 0:
            qtd_final = qtd_num + 1
        else:
            qtd_final = qtd_num
        
        if qtd_final>0:
            if sku_limpo in agrupado:
                agrupado[sku_limpo] += qtd_final
            else:
                agrupado[sku_limpo] = qtd_final

    dados_finais = []

    for sku, total in agrupado.items():
        dados_finais.append((sku,total))

    dados_finais.sort(key=lambda x: x[0])
   
    lista_coluna_A = []
    lista_coluna_B = []

    prefixo_anterior = None

    for sku, qtd in dados_finais:
        prefixo_atual = sku[:4]
        if prefixo_anterior and prefixo_atual != prefixo_anterior:
            lista_coluna_A.append([""])
            lista_coluna_B.append([""])
        lista_coluna_A.append([sku])
        lista_coluna_B.append([qtd])

        prefixo_anterior = prefixo_atual


    if lista_coluna_B:
        total_linhas = len(lista_coluna_B)
        print(f"🚀 Escrevendo {total_linhas} linhas...")
        
        range_A = f"A3:A{total_linhas + 2}"
        range_B = f"B3:B{total_linhas + 2}"

      
        aba_destino_resumo.update(range_name=range_A, values=lista_coluna_A)
        aba_destino_resumo.update(range_name=range_B, values=lista_coluna_B)
        print("RESUMO ATUALIZADO")
    else:
        print("nenhum dado para atualizar")


if __name__ == "__main__": 
    try:
        print("Iniciando conexão...")
        service, client = conectar_google_services()

        
        
        id_encontrado = atualizar_full_atual(service)

        if id_encontrado:
            print("-" * 30)
            print(f"ID FINAL: {id_encontrado}")
            print("Iniciando transferência e cálculos...")

            transferencia_de_dados(client, PLANILHA_ENVIOS_FULL, id_encontrado)
            consulta_integração(client, PLANILHA_ENVIOS_FULL, id_encontrado)
            print("-" * 30) 
            print("Processo concluído com sucesso!")
        else:
            print("A busca falhou em alguma etapa.")
            
    except Exception as e:

        print(f"ERRO TÉCNICO: {e}")
