import pandas as pd
import requests
import os
import re
from datetime import datetime, timedelta

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================

# ⚠️ COLA AQUI O TOKEN DA TUA CONTA FAKE
TOKEN_TINY = "085827cb0ceeb1c6358ae8fcd6cb54cea0ee32813bf8ca782831662000ce7417"

# DATA DO TESTE (Dinâmica: Sempre pega o dia de ONTEM)
# Se hoje é 19/01, ele vai buscar 18/01.
DATA_TESTE = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")

# Se quiser forçar manualmente o dia 18, descomente a linha abaixo:
# DATA_TESTE = "18/01/2026"

print(f"--- 🕵️ A INICIAR EXTRAÇÃO DE VENDAS FAKE: {DATA_TESTE} ---")

# ==============================================================================
# 2. LÓGICA DE KITS (A MATEMÁTICA)
# ==============================================================================
def processar_sku_kit(sku_original, quantidade_vendida):
    # Limpa espaços e coloca em maiúsculas
    sku_limpo = str(sku_original).strip().upper()
    
    # Procura padrão: Qualquer coisa + K + Números no final
    # Exemplo: PI0901K10 -> Grupo 1: PI0901, Grupo 2: 10
    match = re.search(r"^(.*)K(\d+)$", sku_limpo)
    
    if match:
        sku_base = match.group(1)       # Ex: PI0901
        multiplicador = int(match.group(2)) # Ex: 10
        qtd_total = quantidade_vendida * multiplicador
        return sku_base, qtd_total, True
    
    # Se não for kit, devolve o original
    return sku_limpo, quantidade_vendida, False

# ==============================================================================
# 3. ROBÔ DE EXTRAÇÃO
# ==============================================================================
def extrair_relatorio_vendas():
    url_pesquisa = "https://api.tiny.com.br/api2/pedidos.pesquisa.php"
    
    # --- URL DE DETALHE CORRIGIDA (Definida antes do uso) ---
    url_detalhe = "https://api.tiny.com.br/api2/pedido.obter.php"
    
    payload = {
        "token": TOKEN_TINY,
        "dataInicial": DATA_TESTE,
        "dataFinal": DATA_TESTE,
        "formato": "JSON"
    }
    
    try:
        print("📡 A conectar ao Tiny Fake...")
        response = requests.post(url_pesquisa, data=payload)
        dados = response.json()
        
        status = dados.get('retorno', {}).get('status')
        
        # --- TRATAMENTO ESPECÍFICO PARA LISTA VAZIA ---
        if status == 'Erro':
            erro_msg = dados['retorno'].get('erros', [{'erro': 'Desconhecido'}])[0]['erro']
            
            # Se o erro for apenas "Não tem vendas", tratamos como aviso
            if "A consulta não retornou registros" in erro_msg:
                print(f"⚠️ AVISO: Nenhuma venda encontrada no dia {DATA_TESTE}.")
                print("   (Confira se a data do pedido no Tiny é realmente de ONTEM)")
                return
            
            print(f"❌ Erro do Tiny: {erro_msg}")
            return

        pedidos = dados['retorno'].get('pedidos', [])
        print(f"📦 Encontrei {len(pedidos)} pedidos. A processar...")
        
        lista_final = []
        
        cont_processados = 0
        cont_ignorados = 0

        for i, item in enumerate(pedidos):
            p = item['pedido']
            situacao = p['situacao']
            
            # --- FILTRO DE STATUS REMOVIDO ---
            # Agora processamos TUDO, não importa se está cancelado ou em aberto.
            # status_ignorados = ['Em aberto', 'Dados incompletos', 'Cancelado']
            # if situacao in status_ignorados: ...

            cont_processados += 1
            id_ped = p['id']
            
            # Pede os detalhes do pedido (Usando url_detalhe corretamente)
            r_det = requests.post(url_detalhe, data={"token": TOKEN_TINY, "id": id_ped, "formato": "JSON"})
            
            if r_det.status_code == 200:
                d_det = r_det.json()
                itens = d_det.get('retorno', {}).get('pedido', {}).get('itens', [])
                
                for obj in itens:
                    prod = obj['item']
                    sku_nota = prod['codigo']
                    qtd_nota = float(prod['quantidade'])
                    
                    # Aplica a lógica do Kit
                    sku_final, qtd_final, era_kit = processar_sku_kit(sku_nota, qtd_nota)
                    
                    lista_final.append({
                        "Pedido": p['numero'],
                        "Status": situacao,
                        "SKU Original": sku_nota,
                        "Qtd Nota": qtd_nota,
                        "É Kit?": "SIM" if era_kit else "Não",
                        "SKU Final (Estoque)": sku_final,
                        "Qtd Final (Estoque)": qtd_final
                    })
            
            if i % 5 == 0: print(f"   ⏳ Lendo {i+1}...")

        print("-" * 50)
        print(f"📊 RESUMO: {cont_processados} processados | {cont_ignorados} ignorados")
        
        # --- SALVAR EM EXCEL ---
        if lista_final:
            df = pd.DataFrame(lista_final)
            
            # Salva na Área de Trabalho para ser fácil de achar
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
            nome_arquivo = f"Teste_Tiny_Fake_{DATA_TESTE.replace('/', '-')}.xlsx"
            caminho_final = os.path.join(desktop, nome_arquivo)
            
            df.to_excel(caminho_final, index=False)
            
            print(f"\n✅ SUCESSO! Arquivo gerado na Área de Trabalho.")
            print(f"📂 Nome: {nome_arquivo}")
        else:
            print("\n⚠️ Nenhum pedido válido encontrado após os filtros.")

    except Exception as e:
        print(f"❌ Erro Crítico: {e}")

if __name__ == "__main__":
    extrair_relatorio_vendas()