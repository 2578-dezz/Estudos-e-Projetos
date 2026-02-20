import streamlit as st
from PIL import Image
import subprocess

icon = Image.open('Colaí.png.png')

st.set_page_config(page_title='Tecnologia Colaí', page_icon=icon)
fundo_do_site ="""<style>
.stApp {
    background-image: url("https://acdn-us.mitiendanube.com/stores/853/995/themes/common/logo-852124537-1693921118-0fc332af4475bdb9e91df6c0a219df6b1693921119-480-0.webp");
    background-size: 400px;
    background-repeat: no-repeat;
    background-position: center;
    background-attachment: fixed;
}
</style>
"""
Nome_de_usuario = 'login'
Utilizadores = {
    
    "Analista 05": "1234", "Analista 01" : "1234", "Rubão": "1234", "Maria": "1234"
                
}


if 'logado' not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario_nome = ""
    
if not st.session_state.logado:
    
    st.subheader("Por favor, realize seu login:")
    st.markdown(fundo_do_site,unsafe_allow_html=True)
    usuario = st.text_input('Usuário')  
    senha = st.text_input('Digite sua senha',type='password')
    if st.button('ENTRAR'):
        if Utilizadores.get(usuario) == senha:
            st.session_state.logado = True
            st.session_state.usuario_nome = usuario
            st.rerun()
        else:
            st.error('Usuario ou senha incorretos. Tente novamente!')
else:
    with st.sidebar:
        st.image('Colaí.png.png')
        st.write(f"Sessão iniciada como: **{st.session_state.usuario_nome}**")
        if st.button ("Sair"):
            st.session_state.logado = False
            st.rerun()
            
        
        
    st.title(f'Olá {st.session_state.usuario_nome}')
    st.write ('Bem vindo a tecnologia :blue[Colaí], como podemos te ajudar hoje?')
    st.markdown('*Essa interface foi desenvolvida para poupar processos manuais dos setores financeiros e de analise de dados! Gostaria de pedir o feedback dos usuarios juntamente com um pouco de paciência pois a mesma ainda está em processo de desenvolvimento!*')
    st.markdown(''' 
                Por aqui você pode:
     
     * Gerar toda a planilha de FULL da Shoppe e MELLI
     * Atualizar a planilha de tacos
     * Atuaizar a planilha de projeção
     * Atualizar a planilha de Fluxo de estoque
     * Atualizar o dolar para a planilha de ICOs e outras funções..          
                
                ''')

    opcao = st.selectbox(
    'Escolha um departamento:',
    ['Integração', 'Financeiro']
    
    )
    if opcao == 'Integração':
        st.write ('Você escolheu Integração')
        if st.button ('Gerar planilhas FULL Shoppe'):
            
        st.button  ('Gerar planilhas FULL MELLI')
        st.button     ('Atualizar planilha de projeção')
        st.button    ( 'Atualizar a planilha de Fluxo de estoque')
        st.button    ( 'Atualizar a planilha de tacos')          
    elif opcao == 'Financeiro':
        st.write('Você escolheu Financeiro')
        st.button (
            'Atualizar valor do dolar na planilha de ICOs'
        )