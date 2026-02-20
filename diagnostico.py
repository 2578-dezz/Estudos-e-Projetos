import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import os
import time

# ==============================================================================
# CONFIGURAÇÕES DE DIAGNÓSTICO
# ==============================================================================

# ⚠️ COLA AQUI O ID DA PASTA ONDE ESTÃO AS PLANILHAS
ID_PASTA_ALVO = "15t19SkCGxTKv7InSXkepOBI_ALZc-Vx8" 

# Configuração automática do arquivo de senha
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_CREDENCIAIS = os.path.join(DIRETORIO_ATUAL, "creds.json")

def conectar_google():
    print("☁️ A conectar ao Google...")
    
    if not os.path.exists(ARQUIVO_CREDENCIAIS):
        print("❌ ERRO: Ficheiro 'creds.json' não encontrado na pasta.")
        return None, None

    escopos = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds = Credentials.from_service_account_file(ARQUIVO_CREDENCIAIS, scopes=escopos)
        client = gspread.authorize(creds)
        service = build('drive', 'v3', credentials=creds)
        return client, service
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return None, None

def listar_arquivos(service, folder_id):
    print(f"📂 A listar ficheiros na pasta {folder_id}...")
    try:
        # Filtro para ver Excel (.xlsx), Excel com Macro (.xlsm) e Google Sheets
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
            print("⚠️ AVISO: A pasta está vazia para o robô.")
        else:
            print(f"✅ Encontrei {len(arquivos)} ficheiros compatíveis.")
            
        return arquivos
    except Exception as e:
        print(f"❌ Erro ao listar: {e}")
        return []

def rodar_diagnostico():
    client, service = conectar_google()
    if not client: return

    arquivos = listar_arquivos(service, ID_PASTA_ALVO)
    
    print("\n" + "="*60)
    print("🕵️  RELATÓRIO DE ABAS ENCONTRADAS")
    print("="*60)

    for arquivo in arquivos:
        nome_arquivo = arquivo['name']
        id_arquivo = arquivo['id']
        
        print(f"\n📄 FICHEIRO: {nome_arquivo}")
        
        try:
            # Tenta abrir a planilha
            sh = client.open_by_key(id_arquivo)
            
            # Pega a lista de todas as abas
            lista_abas = [ws.title for ws in sh.worksheets()]
            
            print(f"   🔢 Total de abas: {len(lista_abas)}")
            print(f"   📑 NOMES DAS ABAS:")
            print(f"      {lista_abas}")
            
            # Dica visual se a lista for grande
            if len(lista_abas) > 10:
                print("      (Muitas abas! Verifique se o nome do SKU está exatamente igual a um destes)")
                
        except Exception as e:
            print(f"   ❌ Erro ao ler este ficheiro: {e}")

    print("\n" + "="*60)
    print("FIM DO DIAGNÓSTICO")

if __name__ == "__main__":
    rodar_diagnostico()