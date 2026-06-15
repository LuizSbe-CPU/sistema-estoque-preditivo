import streamlit as st
import pandas as pd
from supabase import create_client, Client
import segno

st.set_page_config(page_title="Painel União Comercial", layout="wide")

# Conexão Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- LOGIN ---
if "logado" not in st.session_state: st.session_state.logado = False
if not st.session_state.logado:
    st.title("🔐 Login União Comercial")
    u, p = st.text_input("Usuário:"), st.text_input("Senha:", type="password")
    if st.button("Entrar") and u == "admin" and p == "123":
        st.session_state.logado = True
        st.rerun()
    st.stop()

# --- FUNÇÕES ---
def buscar_dados_pix():
    try: return supabase.table("dados_pix").select("*").eq("id", 1).execute().data[0]
    except: return {"chave_pix": "", "nome_titular": "", "cidade_titular": ""}

def atualizar_dados_pix(chave, titular, city):
    supabase.table("dados_pix").update({"chave_pix": chave, "nome_titular": titular, "cidade_titular": city}).eq("id", 1).execute()

def gerar_payload_pix(chave, titular, city, valor):
    t, c = titular.strip().upper(), city.strip().upper()
    return f"00020101021126360014br.gov.bcb.pix0114{chave.strip()}5204000053039865405{valor:.2f}5802BR59{len(t):02d}{t}60{len(c):02d}{c}62070503***6304"

def buscar_produtos():
    return supabase.table("produtos").select("*").order("nome_produto").execute().data

# --- MENU ---
st.sidebar.title("🏪 União Comercial")
menu = st.sidebar.radio("Navegar:", ["🛒 Frente de Caixa (PDV)", "📦 Importação em Lote", "⚙️ Configurações do PIX"])

if menu == "⚙️ Configurações do PIX":
    st.title("⚙️ Configurações PIX")
    d = buscar_dados_pix()
    with st.form("p"):
        c, t, ci = st.text_input("Chave", d["chave_pix"]), st.text_input("Titular", d["nome_titular"]), st.text_input("Cidade", d["cidade_titular"])
        if st.form_submit_button("Salvar"):
            atualizar_dados_pix(c, t, ci)
            st.success("Salvo!")

elif menu == "🛒 Frente de Caixa (PDV)":
    st.title("🛒 Frente de Caixa")
    if "carrinho" not in st.session_state: st.session_state.carrinho = []
    prods = buscar_produtos()
    sel = st.selectbox("Produto", [p["nome_produto"] for p in prods])
    p_sel = next(p for p in prods if p["nome_produto"] == sel)
    qnt = st.number_input("Quantidade", 1, p_sel["estoque_atual"])
    if st.button("Adicionar"):
        st.session_state.carrinho.append({"id": p_sel["id"], "nome": p_sel["nome_produto"], "preco": p_sel["preco"], "qnt": qnt})
    
    if st.session_state.carrinho:
        df = pd.DataFrame(st.session_state.carrinho)
        st.dataframe(df)
        total = (df["preco"] * df["qnt"]).sum()
        if st.button("Finalizar Venda"):
            for item in st.session_state.carrinho:
                supabase.table("produtos").update({"estoque_atual": (next(p for p in prods if p["id"] == item["id"])["estoque_atual"] - item["qnt"])}).eq("id", item["id"]).execute()
            st.session_state.carrinho = []
            st.success("Venda Finalizada!")

elif menu == "📦 Importação em Lote":
    st.title("📦 Importação de Produtos")
    file = st.file_uploader("Upload CSV/Excel", type=["csv", "xlsx"])
    if file:
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
        if st.button("Processar"):
            for _, r in df.iterrows():
                dados = {"nome_produto": r["nome_produto"], "preco": float(r["preco"]), "estoque_atual": int(r["estoque_atual"])}
                existe = supabase.table("produtos").select("id").eq("nome_produto", r["nome_produto"]).execute()
                if existe.data: supabase.table("produtos").update(dados).eq("id", existe.data[0]["id"]).execute()
                else: supabase.table("produtos").insert(dados).execute()
            st.success("Importado com sucesso!")