import streamlit as st
import pandas as pd
from supabase import create_client
import segno

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="União Comercial", layout="wide")

# Conexão Supabase (Lendo do Secrets)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGIN ---
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login União Comercial")
    u = st.text_input("Usuário:")
    p = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "123":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos!")
    st.stop() # Bloqueia o resto do app se não estiver logado

# --- FUNÇÕES ---
def buscar_dados_pix():
    try:
        data = supabase.table("dados_pix").select("*").eq("id", 1).execute().data
        return data[0] if data else {"chave_pix": "", "nome_titular": "", "cidade_titular": ""}
    except: return {"chave_pix": "", "nome_titular": "", "cidade_titular": ""}

def buscar_produtos():
    try:
        return supabase.table("produtos").select("*").order("nome_produto").execute().data
    except Exception as e:
        st.error(f"Erro ao buscar produtos: {e}")
        return []

# --- MENU ---
st.sidebar.title("🏪 União Comercial")
menu = st.sidebar.radio("Navegar para:", ["🛒 Frente de Caixa (PDV)", "📦 Importação em Lote", "⚙️ Configurações do PIX"])

# --- PDV ---
if menu == "🛒 Frente de Caixa (PDV)":
    st.title("🛒 Frente de Caixa")
    if "carrinho" not in st.session_state: st.session_state.carrinho = []
    
    produtos = buscar_produtos()
    if produtos:
        nomes = [p["nome_produto"] for p in produtos]
        sel = st.selectbox("Selecione o Produto:", nomes)
        prod = next(p for p in produtos if p["nome_produto"] == sel)
        qnt = st.number_input("Quantidade", min_value=1, value=1)
        
        if st.button("Adicionar ao Carrinho"):
            st.session_state.carrinho.append({"id": prod["id"], "nome": prod["nome_produto"], "preco": prod["preco"], "qnt": qnt})
            st.rerun()

    if st.session_state.carrinho:
        df = pd.DataFrame(st.session_state.carrinho)
        st.dataframe(df)
        total = (df["preco"] * df["qnt"]).sum()
        st.subheader(f"Total: R$ {total:.2f}")

# --- IMPORTAÇÃO ---
elif menu == "📦 Importação em Lote":
    st.title("📦 Importação de Produtos")
    file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if file and st.button("Processar Arquivo"):
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
        for _, r in df.iterrows():
            dados = {"nome_produto": r["nome_produto"], "preco": float(r["preco"]), "estoque_atual": int(r["estoque_atual"])}
            existe = supabase.table("produtos").select("id").eq("nome_produto", r["nome_produto"]).execute()
            if existe.data: supabase.table("produtos").update(dados).eq("id", existe.data[0]["id"]).execute()
            else: supabase.table("produtos").insert(dados).execute()
        st.success("Importado com sucesso!")

# --- CONFIG PIX ---
elif menu == "⚙️ Configurações do PIX":
    st.title("⚙️ Configurações PIX")
    d = buscar_dados_pix()
    with st.form("form_pix"):
        c = st.text_input("Chave PIX", value=d["chave_pix"])
        t = st.text_input("Titular", value=d["nome_titular"])
        ci = st.text_input("Cidade", value=d["cidade_titular"])
        if st.form_submit_button("Salvar"):
            supabase.table("dados_pix").update({"chave_pix": c, "nome_titular": t, "cidade_titular": ci}).eq("id", 1).execute()
            st.success("Salvo com sucesso!")