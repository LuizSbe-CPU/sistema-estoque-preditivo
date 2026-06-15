import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="União Comercial", layout="wide")

# Conexão Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGIN SIMPLIFICADO ---
if "logado" not in st.session_state: st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login União Comercial")
    u = st.text_input("Usuário (digite admin):")
    p = st.text_input("Senha (digite 123):", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "123":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos!")
    st.stop()

# --- SE ESTIVER LOGADO, MOSTRA O SISTEMA ---
st.sidebar.title("🏪 União Comercial")
menu = st.sidebar.radio("Navegar:", ["🛒 Frente de Caixa (PDV)", "⚙️ Configurações do PIX"])

# --- FUNÇÃO CORRIGIDA ---
def buscar_produtos():
    try:
        # AQUI ESTÁ A CORREÇÃO: Usando 'nome_produto' conforme sua tabela
        return supabase.table("produtos").select("*").order("nome_produto").execute().data
    except Exception as e:
        st.error(f"Erro ao buscar produtos: {e}")
        return []

if menu == "🛒 Frente de Caixa (PDV)":
    st.title("🛒 Frente de Caixa")
    produtos = buscar_produtos()
    if produtos:
        # AQUI TAMBÉM CORRIGIMOS PARA 'nome_produto'
        sel = st.selectbox("Produto:", [p["nome_produto"] for p in produtos])
        st.write(f"Você selecionou: {sel}")
    else:
        st.warning("Nenhum produto encontrado na tabela 'produtos'.")

elif menu == "⚙️ Configurações do PIX":
    st.title("⚙️ Configurações PIX")
    # ... (seu código de PIX aqui)