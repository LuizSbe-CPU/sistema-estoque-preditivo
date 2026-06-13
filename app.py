import streamlit as st
from supabase import create_client, Client

# 1. Configuração das credenciais (Coloque a sua chave aqui!)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
# --- CONFIGURAÇÃO DA TELA ---
st.set_page_config(page_title="Sistema de Estoque", layout="centered")
st.title("🏪 Sistema de Comércio - Painel do Lojista")
st.markdown("Alimente a base de dados e acompanhe as sugestões de compra.")

# Criando as Abas
aba_cadastro, aba_relatorio = st.tabs(["📝 Cadastrar Dados", "📊 Lista de Compras Preditiva"])

# --- ABA 1: CADASTRO ---
with aba_cadastro:
    st.header("Novo Cadastro")
    # Substitua a linha do selectbox por esta:
    opcao = st.selectbox("O que deseja cadastrar?", ["Fornecedor", "Produto"])
    
    # Inicializa o banco apenas dentro do botão para evitar travar a tela
    if opcao == "Fornecedor":
        st.subheader("Cadastrar Novo Fornecedor")
        nome_fornecedor = st.text_input("Nome do Fornecedor (Ex: AMBEV)")
        
        if st.button("Gravar Fornecedor", type="primary"):
            if nome_fornecedor:
                try:
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                    supabase.table("fornecedores").insert({"nome_fornecedor": nome_fornecedor}).execute()
                    st.success(f"✅ Fornecedor '{nome_fornecedor}' gravado na nuvem!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.warning("Digite o nome do fornecedor.")

    elif opcao == "Produto":
        st.subheader("Cadastrar Novo Produto")
        nome_produto = st.text_input("Nome do Produto")
        
        col1, col2 = st.columns(2)
        with col1:
            est_atual = st.number_input("Estoque Atual", min_value=0, value=10, step=1)
            media_venda = st.number_input("Média de Vendas/Dia", min_value=0.0, value=2.0, step=0.5)
        with col2:
            est_minimo = st.number_input("Estoque Mínimo", min_value=0, value=5, step=1)
            custo = st.number_input("Preço de Custo (R$)", min_value=0.0, value=1.5, step=0.1)
            
        id_fornecedor = st.number_input("ID do Fornecedor (Olhar no Supabase)", min_value=1, step=1)
        
        if st.button("Gravar Produto", type="primary"):
            if nome_produto:
                payload = {
                    "nome_produto": nome_produto,
                    "estoque_atual": int(est_atual),
                    "estoque_minimo": int(est_minimo),
                    "media_venda_dia": float(media_venda),
                    "ultimo_custo": float(custo),
                    "id_fornecedor": int(id_fornecedor)
                }
                try:
                    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                    supabase.table("produtos").insert(payload).execute()
                    st.success(f"✅ Produto '{nome_produto}' adicionado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar produto: {e}")
            else:
                st.warning("Digite o nome do produto.")

# --- ABA 2: RELATÓRIO PREDITIVO ---
with aba_relatorio:
    st.header("📋 Sugestão de Compras (Próximos 7 Dias)")
    
    if st.button("🔄 Carregar / Atualizar Relatório"):
        try:
            supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
            response = supabase.table("visualizar_lista_de_compras").select("*").execute()
            dados = response.data
            
            if dados:
                st.dataframe(dados, use_container_width=True)
            else:
                st.info("✅ Todos os produtos estão abastecidos!")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")