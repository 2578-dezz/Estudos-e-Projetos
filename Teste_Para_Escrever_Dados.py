import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os
import time

# ==============================================================================
# CONFIGURAÇÕES DE TESTE
# ==============================================================================

# O ID DA PASTA(O teu pessoal)
ID_PASTA_DRIVE = "15t19SkCGxTKv7InSXkepOBI_ALZc-Vx8" 

# DADOS FALSOS PARA TESTE (Simulando o Tiny)
SKU_TESTE = "PI0901 - FITA DOURADA"  # Nome da aba que vamos procurar
QTD_TESTE = 999           # Valor que vamos escrever
DATA_TESTE = "25/12/2025" # Uma data que JÁ EXISTA na Coluna A da planilha

# CONFIGURAÇÕES FIXAS
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CREDENCIAIS = os.path.join(DIRETORIO_ATUAL, "creds.json")
COLUNA_DATA_INDEX = 1
COLUNA_QTD_INDEX = 3

def conectar_google():
    print(" Conectando ao Google.")
    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_file(ARQUIVO_CREDENCIAIS, scopes=escopos)
        client = gspread.authorize(creds)
        service = build('drive', 'v3', credentials=creds)
        return client, service
    except Exception as e:
        print(f"❌ Erro conexão: {e}")
        return None, None

def listar_planilhas(service, folder_id):
    print(f" Listando arquivos na pasta {folder_id}...")
    try:
        # Filtro completo (Google Sheets + Excel + XLSM)
        query = (
            f"'{folder_id}' in parents and "
            f"(mimeType='application/vnd.google-apps.spreadsheet' or "
            f"mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or "
            f"mimeType='application/vnd.ms-excel.sheet.macroEnabled.12') and "
            f"trashed=false"
        )
        results = service.files().list(q=query, fields="files(id, name)").execute()
        arquivos = results.get('files', [])
        
        if not arquivos:
            print("❌ Pasta vazia!")
        else:
            print(f"✅ Encontrei {len(arquivos)} arquivos.")
            
        return arquivos
    except Exception as e:
        print(f"❌ Erro ao listar: {e}")
        return []

def rodar_teste_escrita():
    client, service = conectar_google()
    if not client: return

    arquivos = listar_planilhas(service, ID_PASTA_DRIVE)
    if not arquivos: return

    print(f"\n INICIANDO TESTE DE ESCRITA")
    print(f"   Vou procurar a aba '{SKU_TESTE}' e a data '{DATA_TESTE}'...")

    for arquivo in arquivos:
        print(f" Abrindo: {arquivo['name']}")
        try:
            # FIX: Usando open_by_key que é o comando padrão compatível
            sh = client.open_by_key(arquivo['id'])
            
            try:
                ws = sh.worksheet(SKU_TESTE)
                print(f"ABA ENCONTRADA")
                
                # Procura a data na Coluna A
                datas = ws.col_values(COLUNA_DATA_INDEX)
                linha = -1
                
                # Varredura simples
                for i, val in enumerate(datas):
                    if DATA_TESTE in str(val):
                        linha = i + 1
                        break
                
                if linha > 0:
                    print(f"   Data encontrada na linha {linha}. Escrevendo {QTD_TESTE}...")
                    
                    # Tenta escrever
                    ws.update_cell(linha, COLUNA_QTD_INDEX, QTD_TESTE)
                    
                    print(f"      ✅ SUCESSO! Célula B{linha} atualizada com 999.")
                    print("      (Vá no Google Drive e confira se apareceu!)")
                    return # Para o teste se deu certo
                else:
                    print(f"      ⚠️ Data {DATA_TESTE} não encontrada na coluna A.")
                    
            except gspread.WorksheetNotFound:
                # print("      Aba não existe aqui.")
                pass
            except Exception as e:
                print(f"      ❌ Erro ao escrever: {e}")
                
        except Exception as e:
            print(f"      ❌ Erro ao abrir arquivo: {e}")

if __name__ == "__main__":
    rodar_teste_escrita()
    
