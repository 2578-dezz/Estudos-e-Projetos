import os
import zipfile
import shutil

def criar_cbz_de_pastas():
    print("=== Gerador de Arquivos CBZ em Lote ===")
    
    # 1. Pede o caminho da pasta onde estão as pastas dos capítulos
    caminho_raiz = input("Cole o caminho da pasta onde estão os capítulos baixados: ").strip()
    
    # Remove aspas se o usuário copiou como "C:\Caminho"
    caminho_raiz = caminho_raiz.replace('"', '')

    if not os.path.exists(caminho_raiz):
        print("❌ Pasta não encontrada!")
        return

    # Lista tudo que tem na pasta
    itens = os.listdir(caminho_raiz)
    pastas_capitulos = [item for item in itens if os.path.isdir(os.path.join(caminho_raiz, item))]
    
    if not pastas_capitulos:
        print("⚠️ Nenhuma subpasta encontrada para converter.")
        return

    print(f"📂 Encontradas {len(pastas_capitulos)} pastas. Iniciando conversão...\n")

    contador = 0
    
    for nome_pasta in pastas_capitulos:
        caminho_completo_pasta = os.path.join(caminho_raiz, nome_pasta)
        
        # O nome do arquivo CBZ será o mesmo nome da pasta
        nome_arquivo_cbz = os.path.join(caminho_raiz, f"{nome_pasta}.cbz")
        
        print(f"📚 Compactando: {nome_pasta} -> .cbz")
        
        try:
            # Cria o arquivo ZIP (CBZ)
            with zipfile.ZipFile(nome_arquivo_cbz, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Pega todas as imagens dentro da pasta
                for raiz, dirs, arquivos in os.walk(caminho_completo_pasta):
                    for arquivo in arquivos:
                        # Caminho absoluto da imagem
                        caminho_imagem = os.path.join(raiz, arquivo)
                        
                        # Caminho relativo (para não salvar C:/Users/... dentro do zip)
                        # Isso garante que a imagem fique na "raiz" do arquivo CBZ
                        nome_dentro_zip = arquivo 
                        
                        zf.write(caminho_imagem, nome_dentro_zip)
            
            contador += 1
            
        except Exception as e:
            print(f"❌ Erro ao criar CBZ de {nome_pasta}: {e}")

    print("\n" + "="*40)
    print(f"✅ Processo finalizado!")
    print(f"📦 {contador} arquivos .cbz criados em: {caminho_raiz}")
    print("="*40)
    
    # Pergunta opcional para deletar as pastas originais e economizar espaço
    escolha = input("Deseja DELETAR as pastas originais (as de imagens soltas) e manter apenas os CBZ? (s/n): ").lower()
    
    if escolha == 's':
        for nome_pasta in pastas_capitulos:
            caminho_completo = os.path.join(caminho_raiz, nome_pasta)
            try:
                shutil.rmtree(caminho_completo) # Deleta a pasta e tudo dentro
                print(f"🗑️ Deletado: {nome_pasta}")
            except Exception as e:
                print(f"Erro ao deletar {nome_pasta}: {e}")
        print("Limpeza concluída.")
    else:
        print("Pastas originais mantidas.")

if __name__ == "__main__":
    criar_cbz_de_pastas()