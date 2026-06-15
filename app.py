import streamlit as st
import pandas as pd
from supabase import create_client, Client
import segno

# Configuração da página do Streamlit
st.set_page_config(page_title="Painel União Comercial", layout="wide")

# 🔒 FORMA PROFISSIONAL: Buscando as credenciais em segredo do Secrets do Streamlit
# (Você não precisa colar seus links aqui, o Streamlit lê direto da caixinha preta do site)
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- FUNÇÕES DE BUSCA E ATUALIZAÇÃO DO PIX ---
def buscar_dados_pix():
    try:
        response = supabase.table("dados_pix").select("*").eq("id", 1).execute()
        if response.data:
            return response.data[0]
    except Exception as e:
        return None
    return {"chave_pix": "", "nome_titular": "", "cidade_titular": ""}

def atualizar_dados_pix(chave, titular, city):
    try:
        supabase.table("dados_pix").update({
            "chave_pix": chave,
            "nome_titular": titular,
            "cidade_titular": city
        }).eq("id", 1).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no banco: {e}")
        return False

def gerar_payload_pix(chave, titular, city, valor):
    chave = str(chave).strip()
    titular = str(titular).strip().upper()
    city = str(city).strip().upper()
    
    payload = "00020101021126360014br.gov.bcb.pix"
    payload += f"0114{chave}"
    payload += "520400005303986"
    payload += f"5405{valor:.2f}"
    payload += "5802BR"
    payload += f"59{len(titular):02d}{titular}"
    payload += f"60{len(city):02d}{city}"
    payload += "62070503***6304"
    return payload

# --- FUNÇÕES DE PRODUTOS E ESTOQUE ---
def buscar_produtos():
    try:
        response = supabase.table("produtos").select("*").order("nome").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao buscar produtos: {e}")
        return []

# --- INICIALIZAÇÃO DO CARRINHO ---
if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

# --- MENU LATERAL NAVEGAÇÃO ---
st.sidebar.title("🏪 União Comercial")
menu = st.sidebar.radio("Navegar para:", ["🛒 Frente de Caixa (PDV)", "📦 Importação em Lote", "⚙️ Configurações do PIX"])

# -------------------------------------------------------------
# PAGINA: CONFIGURAÇÕES DO PIX
# -------------------------------------------------------------
if menu == "⚙️ Configurações do PIX":
    st.title("⚙️ Configurações de Recebimento via PIX")
    st.write("Insira os dados da conta bancária da empresa para gerar os QR Codes no caixa.")
    
    dados_atuais = buscar_dados_pix()
    
    with st.form("form_pix"):
        chave_input = st.text_input("Chave PIX (CNPJ, E-mail, Celular ou Chave Aleatória)", value=dados_atuais.get("chave_pix", ""))
        titular_input = st.text_input("Nome do Titular da Conta (Sem acentos, ex: LOJA DA UNIAO LTDA)", value=dados_atuais.get("nome_titular", ""))
        cidade_input = st.text_input("Cidade da Agência Bancária (Sem acentos, ex: RIBEIRAO DAS NEVES)", value=dados_atuais.get("cidade_titular", ""))
        
        botao_salvar = st.form_submit_button("Salvar Configurações do PIX")
        
        if botao_salvar:
            if chave_input and titular_input and cidade_input:
                if atualizar_dados_pix(chave_input, titular_input, cidade_input):
                    st.success("✅ Configurações salvas e integradas com sucesso!")
            else:
                st.error("⚠️ Por favor, preencha todos os campos.")

# -------------------------------------------------------------
# PAGINA: FRENTE DE CAIXA (PDV)
# -------------------------------------------------------------
elif menu == "🛒 Frente de Caixa (PDV)":
    st.title("🛒 Frente de Caixa (PDV)")
    
    produtos = buscar_produtos()
    
    if not produtos:
        st.warning("Nenhum produto cadastrado no estoque ainda. Vá na aba 'Importação em Lote'.")
    else:
        lista_nomes = [p["nome"] for p in produtos]
        produto_selecionado = st.selectbox("Selecione o Produto:", lista_nomes)
        
        prod_dados = next(p for p in produtos if p["nome"] == produto_selecionado)
        
        col_dados1, col_dados2 = st.columns(2)
        with col_dados1:
            st.info(f"**Preço Unitário:** R$ {prod_dados['preco']:.2f}")
        with col_dados2:
            st.info(f"**Estoque Atual:** {prod_dados['estoque_atual']} un")
            
        quantidade = st.number_input("Quantidade:", min_value=1, value=1, step=1)
        
        if st.button("➕ Adicionar ao Carrinho"):
            if quantidade > prod_dados["estoque_atual"]:
                st.error("⚠️ Quantidade superior ao estoque disponível!")
            else:
                st.session_state.carrinho.append({
                    "id": prod_dados["id"],
                    "nome": prod_dados["nome"],
                    "preco": prod_dados["preco"],
                    "quantidade": quantidade,
                    "total_item": prod_dados["preco"] * quantidade
                })
                st.toast("Item adicionado!")

    if st.session_state.carrinho:
        st.subheader("📋 Itens no Carrinho")
        df_carrinho = pd.DataFrame(st.session_state.carrinho)
        st.dataframe(df_carrinho[["nome", "preco", "quantidade", "total_item"]], use_container_width=True)
        
        valor_total = df_carrinho["total_item"].sum()
        st.markdown(f"### 💰 **Total da Venda: R$ {valor_total:.2f}**")
        
        if st.button("🗑️ Limpar Carrinho"):
            st.session_state.carrinho = []
            st.rerun()
            
        st.write("---")
        st.subheader("💳 Finalização da Venda")
        forma_pagamento = st.selectbox("Forma de Pagamento:", ["Dinheiro", "Cartão", "PIX"])
        
        if forma_pagamento == "PIX":
            dados_config = buscar_dados_pix()
            if not dados_config or dados_config.get("chave_pix") == "Insira sua chave":
                st.warning("⚠️ PIX não configurado. Acesse a aba 'Configurações do PIX'.")
            else:
                if st.button("🔄 Gerar QR Code do PIX"):
                    payload = gerar_payload_pix(
                        dados_config["chave_pix"], dados_config["nome_titular"], dados_config["cidade_titular"], valor_total
                    )
                    qr = segno.make(payload)
                    qr.save("pix_atual.png", scale=8)
                    
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.image("pix_atual.png", caption="Abra o app do banco")
                    with c2:
                        st.success(f"**Favorecido:** {dados_config['nome_titular']}")
                        st.code(payload, caption="Código Copia e Cola")
                        
        if st.button("✅ Confirmar e Finalizar Venda"):
            try:
                for item in st.session_state.carrinho:
                    p_atual = supabase.table("produtos").select("estoque_atual").eq("id", item["id"]).execute().data[0]
                    novo_estoque = p_atual["estoque_atual"] - item["quantidade"]
                    
                    supabase.table("produtos").update({"estoque_atual": novo_estoque}).eq("id", item["id"]).execute()
                
                st.balloons()
                st.success("🎉 Venda concluída e estoque atualizado com sucesso!")
                st.session_state.carrinho = []
            except Exception as e:
                st.error(f"Erro ao processar baixa de estoque: {e}")

# -------------------------------------------------------------
# PAGINA: IMPORTAÇÃO EM LOTE
# -------------------------------------------------------------
elif menu == "📦 Importação em Lote":
    st.title("📦 Importação de Produtos em Lote")
    st.write("Suba sua planilha para atualizar ou cadastrar o estoque em massa.")
    
    arquivo_enviado = st.file_uploader("Selecione um arquivo CSV ou Excel:", type=["csv", "xlsx"])
    
    if arquivo_enviado is not None:
        try:
            if arquivo_enviado.name.endswith(".csv"):
                df = pd.read_csv(arquivo_enviado, sep=None, engine="python")
            else:
                df = pd.read_excel(arquivo_enviado)
                
            st.subheader("Pré-visualização dos Dados:")
            st.dataframe(df.head())
            
            df.columns = df.columns.str.strip().str.lower()
            
            if st.button("🚀 Enviar Dados para o Banco (Supabase)"):
                progresso = st.progress(0)
                total_linhas = len(df)
                
                for index, row in df.iterrows():
                    preco_limpo = float(str(row["preco"]).replace(",", "."))
                    estoque_limpo = int(row["estoque_atual"])
                    estoque_min_limpo = int(row["estoque_minimo"]) if "estoque_minimo" in df.columns else 5
                    
                    dados_produto = {
                        "nome": str(row["nome"]).strip(),
                        "preco": preco_limpo,
                        "estoque_atual": estoque_limpo,
                        "estoque_minimo": estoque_min_limpo
                    }
                    
                    existe = supabase.table("produtos").select("id").eq("nome", dados_produto["nome"]).execute()
                    
                    if existe.data:
                        supabase.table("produtos").update(dados_produto).eq("id", existe.data[0]["id"]).execute()
                    else:
                        supabase.table("produtos").insert(dados_produto).execute()
                        
                    progresso.progress((index + 1) / total_linhas)
                    
                st.success("✅ Todos os produtos foram importados/atualizados com sucesso!")
        except Exception as e:
            st.error(f"Erro ao processar o arquivo: {e}. Verifique as colunas (nome, preco, estoque_atual).")