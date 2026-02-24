#importações usadas para este projeto:


import streamlit as st
from PIL import Image
import base64

#Apartir daqui são importações dos scripts que existem na mesma pasta do arquivo streamlit(scripts que dão vida aos botões)

import Planilhas_de_separação
import Planilha_Maria
import Planilhas_Mel_e_Integração
import Fluxo_estoque
import Planilha_Paulo
import Separação_Melli
import Liste_de_envios_Shoppe

#python -m streamlit run Projeto_Streamlit.py (função usada no CMD para rodar o arquivo streamlit)


icon = Image.open("Colaí.png.png")#Aqui voce coloca o titulo do arquivo da imagem que vc quer colocar como icone do site(essa imagem vai ficar na barra da URL)
st.set_page_config(page_title='Nome que vc preferir', page_icon=icon, layout="centered")#Coloca o titulo do seu site





#Aqui voce define o fundo do site, que no meu caso esta sendo utilizada somente na parte de login

fundo_do_site = """
<style>
.stApp {
    background-image: url("https://acdn-us.mitiendanube.com/stores/853/995/themes/common/logo-852124537-1693921118-0fc332af4475bdb9e91df6c0a219df6b1693921119-480-0.webp");
    background-size: 400px;
    background-repeat: no-repeat;
    background-position: center 80%;
    background-attachment: fixed;
}
</style>
"""


utilizadores = {
    "Nome de usuario" : "senha" #se quiser acrescentar mais usuarios só ir colocando um nome e senha no dicionario
}

#Parte de conexão com usuario que antecede a entrada do site
if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario_nome = ""


if not st.session_state.logado:
    st.markdown(fundo_do_site, unsafe_allow_html=True)
    

    _, col_login, _ = st.columns([1, 2, 1])
    
    with col_login:
        st.write("") # 
        st.subheader("Por favor, faça seu login:")
        

        with st.form("form_login"):
            usuario = st.text_input('Usuário:')  
            senha = st.text_input('Senha:', type='password')
            submit = st.form_submit_button('ENTRAR', use_container_width=True)
            
            if submit:
                if utilizadores.get(usuario) == senha:
                    st.session_state.logado = True
                    st.session_state.usuario_nome = usuario
                    st.rerun()
                else:
                    st.error('Usuário ou senha incorretos. Tente novamente!')
#borda lateral com opção de escolha de setor junto com o nome do usario, imagem representando a empresa e opção de sair

else:

    with st.sidebar:
        st.image("GrupoM.A.png", width=300)
   
        with st.container(border=True):
             st.write(f"👤 Usuário: **{st.session_state.usuario_nome}**")
        st.markdown("---")
        
        st.markdown("### Setor:")
        opcao_menu = st.selectbox(
            'Escolha o Setor:',
            ['Integração', 'Financeiro'],
            label_visibility="collapsed"
        )

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.logado = False
            st.rerun()
    
    
    #Parte frontal do site com uma breve apresentação ao usuario junto com uma apresentação do que é feito            
    
    st.title(f'Olá, {st.session_state.usuario_nome}! 👋')
    st.markdown("### Bem-vindo ao **Painel de Automações** ")
    st.write('Selecione um setor no menu lateral a esquerda para começar.')
    st.markdown("---") 

    #Aqui entram as opções de botões que são integradas com scripts em python que existem em outras pastas do VS code(Qualquer outro sistema para programar em python)
  
    if opcao_menu == 'Integração':
        st.subheader("🌐 Central de Integrações")
        st.write("Gerencie envios e atualize bases de dados operacionais.")
        st.write("") 

        col1, col2 = st.columns(2)
        
      
        with col1:
     
            with st.container(border=True):
                st.subheader("⚡ Envios FULL")
                st.write("Rotinas de expedição e etiquetas.")
                
                escolha_o_full = st.selectbox(
                  'Selecione o Marketplace:',
                  ['Selecione...', 'FULL Shoppe', 'FULL MELLI'],
                  label_visibility="collapsed"
                )
                
                if escolha_o_full == 'FULL Shoppe':
                    st.divider()
                    st.markdown("**🏪 Rotinas Shopee:**")

                    from datetime import datetime

                    meses_opcoes = {
                       1: "01-jan", 2: "02-fev", 3: "03-mar", 4: "04-abr", 
                       5: "05-mai", 6: "06-jun", 7: "07-jul", 8: "08-ago", 
                       9: "09-set", 10: "10-out", 11: "11-nov", 12: "12-dez"
                    }

                    mes_selecionado = st.selectbox(
                       "Selecione o mês do envio FULL:",
                       options=list(meses_opcoes.keys()),
                       format_func=lambda x: meses_opcoes[x],
                       index=None,
                       placeholder="Escolha um mês na lista..."

                    )

                    if mes_selecionado is not None:
                        st.info(f"Mês selecionado: **{meses_opcoes[mes_selecionado]}**")#



                    if st.button(" Gerar Planilhas Consulta Mel e Integração",key="btn_sep_mel_e_integração_shopee" , use_container_width=True):
                         with st.spinner('📝 Atualizando planilhas Mel e Integração... Aguarde!'):
                            try:
                                resultado = Planilhas_Mel_e_Integração.planilhas_mel_e_integração(mes_selecionado)
                                
                                st.success(resultado)
                            
                            except Exception as e:
                                st.error(f"❌ Ocorreu um erro no atualização: {e}")
                    if st.button(" Gerar Planilhas de Separação",key="btn_sep_shopee" ,use_container_width=True):
                        with st.spinner('📝 Atualizando planilhas... Aguarde!'):
                            try:
                                resultado = Planilhas_de_separação.planilhas_de_separação(mes_selecionado)
                                
                                st.success(resultado)
                            
                            except Exception as e:
                                st.error(f"❌ Ocorreu um erro no atualização: {e}")
                    if st.button(" Gerar Planilha Maria",key="btn_sep_maria_shopee" , use_container_width=True):
                         with st.spinner('📝 Atualizando planilha... Aguarde!'):
                            try:
                                resultado = Planilha_Maria.planilha_maria(mes_selecionado)
                                
                                st.success(resultado)
                            
                            except Exception as e:
                                st.error(f"❌ Ocorreu um erro no atualização: {e}")
                    if st.button(" Gerar Planilha Paulo",key="btn_sep_Paulo_shopee" ,use_container_width=True):
                           with st.spinner('📝 Atualizando planilha... Aguarde!'):
                            try:
                                resultado = Planilha_Paulo.planilha_paulo(mes_selecionado)
                                
                                st.success(resultado)
                            
                            except Exception as e:
                                st.error(f"❌ Ocorreu um erro no atualização: {e}")
                    if st.button(" Gerar Lista de envios",key="btn_sep_envios_shopee" ,use_container_width=True):
                           with st.spinner('📝 Atualizando planilha... Aguarde!'):
                            try:
                                resultado = Liste_de_envios_Shoppe.planilha_de_envios(mes_selecionado)
                                
                                st.success(resultado)
                            
                            except Exception as e:
                                st.error(f"❌ Ocorreu um erro no atualização: {e}")

                    st.button(" Atualizar Estoque Tiny", use_container_width=True)
               

                elif escolha_o_full == 'FULL MELLI':
                    st.divider()
                    st.markdown("**📦  Rotinas Mercado Livre:**")

                    from datetime import datetime

                    meses_opcoes = {
                        1: "01-jan", 2: "02-fev", 3: "03-mar", 4: "04-abr", 
                        5: "05-mai", 6: "06-jun", 7: "07-jul", 8: "08-ago", 
                        9: "09-set", 10: "10-out", 11: "11-nov", 12: "12-dez"
                    }

                    mes_selecionado = st.selectbox(
                        "Selecione o mês do envio FULL:",
                        options=list(meses_opcoes.keys()),
                        format_func=lambda x: meses_opcoes[x],
                        index=None,
                        placeholder="Escolha um mês na lista..."

                    )

                    if mes_selecionado is not None:
                        st.info(f"Mês selecionado: **{meses_opcoes[mes_selecionado]}**")


                    if st.button(" Gerar Planilhas de Separação",key="btn_sep_melli",use_container_width=True):
                        with st.spinner('📝 Atualizando planilha... Aguarde!'):
                            try:
                                resultado = Separação_Melli.separação_melli(mes_selecionado)
                                
                                st.success(resultado)
                            
                            except Exception as e:
                                st.error(f"❌ Ocorreu um erro no atualização: {e}")
               
               
      


        with col2:
            with st.container(border=True):
                st.subheader("📊 Bases de Dados")
                st.write("Manutenção de planilhas estratégicas.")
                
                escolha_a_planilha = st.selectbox(
                 'Selecione a rotina:',
                  ['Selecione...', 'Tacos 📉', 'Projeção 📈','Fluxo de Estoque 🏪'],
                  label_visibility="collapsed"
                )

            

                if escolha_a_planilha == 'Tacos 📉':
                    st.button("📉 Executar: Atualizar Tacos", use_container_width=True)
                
                elif escolha_a_planilha == 'Projeção 📈':
                     st.button("📈 Executar: Atualizar Projeção", use_container_width=True)

                elif escolha_a_planilha == 'Fluxo de Estoque 🏪':
                    if st.button("📈 Executar: Atualizar Fluxo de Estoque",key="btn_sep_fluxo_dados",use_container_width=True):
                        with st.spinner('📝 Atualizando planilha Fluxo de Estoque... Aguarde!'):
                            try:
                                resultado = Fluxo_estoque.fluxo_estoque()
                                
                                st.success(resultado)
                            
                            except Exception as e:
                                st.error(f"❌ Ocorreu um erro no atualização: {e}")
        
        
        
    elif opcao_menu == 'Financeiro':
            st.subheader("💰 Central de Financeiros")
            st.write("Gerencie as atualizações dos dados financeiros")
            st.write("") 

            col1, col2 = st.columns(2)

            with col1:
     
             with st.container(border=True):
                st.subheader("💸 Planilhas do Financeiro")
                st.write("Realiza automações nas planilhas do Financeiro.")
                
                escolha_a_automação = st.selectbox(
                  'Selecione a automação:',
                  ['Selecione...', 'Planilha de ICOs'],
                  label_visibility="collapsed"
                )

                if escolha_a_automação == 'Planilha de ICOs':
                    st.button("Atualizar o valor do Dólar atual na planilha de ICOs💵")

#Para os botoes funcionarem e atualizar nos locais desejados, só é possivel se criar uma pasta com o todos esses arquivos juntos, uma pro seu arquivo streamlit e as demais seram os scripts que vão ser utilizados nas funções.
