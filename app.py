import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# 1. Configuração da página (Primeira linha do Streamlit)
st.set_page_config(page_title="Painel União Comercial", layout="wide")

# 2. Conexão direta com o Supabase
url = "https://ltxkhctujyiurotzuios.supabase.co"
key = "sb_publishable_ZuoTHXVKamTALwNZbhPSFw_ccmcC7tI"
supabase: Client = create_client(url, key)

# 3. Gerenciamento do Estado de Login e Carrinho de Compras
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None

if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

# ==========================================
# TELA DE AUTENTICAÇÃO (LOGIN / CADASTRO)
# ==========================================
if st.session_state.usuario_logado is None:
    st.title("🔐 Acesso ao Sistema Comercial")
    
    aba_login, aba_cadastro = st.tabs(["Entrar no Sistema", "Criar Nova Conta"])
    
    with aba_login:
        email_login = st.text_input("E-mail", key="email_log")
        senha_login = st.text_input("Senha", type="password", key="senha_log")
        if st.button("Entrar"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email_login, "password": senha_login})
                st.session_state.usuario_logado = res.user
                st.success("Login realizado com sucesso!")
                st.rerun()
            except Exception as e:
                st.error("Erro ao fazer login. Verifique as credenciais.")
                
    with aba_cadastro:
        email_cad = st.text_input("E-mail para Cadastro", key="email_c")
        senha_cad = st.text_input("Senha (mínimo 6 caracteres)", type="password", key="senha_c")
        if st.button("Cadastrar Comerciante"):
            try:
                res = supabase.auth.sign_up({"email": email_cad, "password": senha_cad})
                st.success("Conta criada com sucesso! Faça o login na aba ao lado.")
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

# ==========================================
# PAINEL DO COMERCIANTE (LOGADO)
# ==========================================
else:
    user = st.session_state.usuario_logado
    
    # --- MENU DA BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        st.header("🏪 Navegação")
        menu = st.radio(
            "Selecione uma tela:",
            ["🛒 PDV", "📈 Relatório de Caixa", "📦 Controle de Estoque", "🤝 Cadastrar Fornecedores"]
        )
        st.markdown("---")
        if st.button("🚪 Sair do Sistema"):
            st.session_state.usuario_logado = None
            st.session_state.carrinho = []
            supabase.auth.sign_out()
            st.rerun()

    # ==========================================
    # TELA 1: PDV (TERMINAL DE VENDAS COMPLETO)
    # ==========================================
    if menu == "🛒 PDV":
        st.title("🛒 Terminal Frente de Caixa (PDV)")
        st.write("Registre os itens dos clientes com segurança e rapidez.")
        st.markdown("---")

        resp_p = supabase.table("produtos").select("*").eq("user_id", user.id).execute()
        lista_produtos = [p["nome_produto"] for p in resp_p.data] if resp_p.data else []

        if not lista_produtos:
            st.warning("⚠️ Você precisa cadastrar produtos na aba 'Controle de Estoque' antes de realizar uma venda.")
        else:
            col_p, col_q, col_v = st.columns([2, 1, 1])
            with col_p:
                prod_selecionado = st.selectbox("1. Selecione o Produto", lista_produtos)
                prod_dados = [p for p in resp_p.data if p["nome_produto"] == prod_selecionado][0]
                preco_sugerido = float(prod_dados["preco"]) if prod_dados["preco"] else 0.0
            with col_q:
                qtd_venda = st.number_input("2. Quantidade", min_value=1, step=1, value=1)
            with col_v:
                preco_final_unitario = st.number_input("3. Preço Unitário R$", min_value=0.0, value=preco_sugerido, step=0.10)
            
            if st.button("➕ Adicionar ao Carrinho", use_container_width=True):
                if prod_dados["estoque_atual"] is None or prod_dados["estoque_atual"] < qtd_venda:
                    st.error(f"❌ Estoque insuficiente! Estoque atual: {prod_dados['estoque_atual']} un.")
                else:
                    item_carrinho = {
                        "id_produto": prod_dados["id_produto"],
                        "produto": prod_selecionado,
                        "quantidade": qtd_venda,
                        "preco_unitario": preco_final_unitario,
                        "total": preco_final_unitario * qtd_venda
                    }
                    st.session_state.carrinho.append(item_carrinho)
                    st.success(f"Adicionado: {qtd_venda}x {prod_selecionado}")
                    st.rerun()

            if st.session_state.carrinho:
                st.markdown("### 📋 Itens Passados no Caixa")
                df_cart = pd.DataFrame(st.session_state.carrinho)
                
                df_cart_exibir = df_cart[['produto', 'quantidade', 'preco_unitario', 'total']].copy()
                df_cart_exibir.columns = ['Produto', 'Quantidade', 'Preço Unitário (R$)', 'Total Item (R$)']
                st.dataframe(df_cart_exibir, use_container_width=True)
                
                valor_total_compra = df_cart['total'].sum()
                
                col_tot, col_limp = st.columns([3, 1])
                col_tot.markdown(f"## 💰 **TOTAL DA COMPRA: R$ {valor_total_compra:.2f}**")
                if col_limp.button("🧹 Limpar Carrinho", type="secondary", use_container_width=True):
                    st.session_state.carrinho = []
                    st.rerun()
                
                st.markdown("---")
                st.markdown("### 🏁 Fechamento e Pagamento")
                
                f_col1, f_col2 = st.columns(2)
                with f_col1:
                    forma_pag = st.selectbox("Escolha a Forma de Pagamento", ["PIX", "Cartão de Crédito", "Cartão de Débito", "Dinheiro"])
                
                num_parcelas = 1
                desc_pagamento = forma_pag
                permitir_venda = True

                with f_col2:
                    if forma_pag == "Cartão de Crédito":
                        parcelas = st.selectbox("Parcelar em até 12x", [f"{i}x" for i in range(1, 13)])
                        num_parcelas = int(parcelas.replace("x", ""))
                        valor_parcela = valor_total_compra / num_parcelas
                        st.markdown(f"### 💳 **{parcelas} de R$ {valor_parcela:.2f}**")
                        desc_pagamento = f"Cartão de Crédito ({parcelas})"
                    elif forma_pag == "Dinheiro":
                        valor_pago = st.number_input("Valor Pago pelo Cliente R$", min_value=0.0, value=valor_total_compra, step=1.0)
                        troco = valor_pago - valor_total_compra
                        if troco > 0:
                            st.markdown(f"### 💵 **Troco para o Cliente: R$ {troco:.2f}**")
                        elif troco < 0:
                            st.markdown(f"⚠️ *Faltam: R$ {abs(troco):.2f}*")
                            permitir_venda = False
                    else:
                        st.write("")

                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("🏁 Finalizar Cupom / Registrar Venda", use_container_width=True, type="primary"):
                    if not permitir_venda:
                        st.error("❌ Não é possível finalizar a venda. O valor pago em dinheiro é menor que o total da compra!")
                    else:
                        try:
                            for item in st.session_state.carrinho:
                                p_atualizado = supabase.table("produtos").select("estoque_atual").eq("id_produto", item["id_produto"]).execute().data[0]
                                novo_estoque = (p_atualizado["estoque_atual"] if p_atualizado["estoque_atual"] is not None else 0) - item["quantidade"]
                                supabase.table("produtos").update({"estoque_atual": novo_estoque}).eq("id_produto", item["id_produto"]).execute()
                                
                                nova_venda = {
                                    "user_id": user.id,
                                    "produto": item["produto"],
                                    "valor": item["total"],
                                    "forma_pagamento": desc_pagamento
                                }
                                supabase.table("vendas").insert(nova_venda).execute()
                            
                            st.success("🎉 Compra finalizada com sucesso!")
                            st.session_state.carrinho = []  
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao processar fechamento: {e}")
            else:
                st.info("O carrinho está vazio. Adicione os itens acima para iniciar a venda.")

    # ==========================================
    # TELA 2: 📈 RELATÓRIO DE CAIXA
    # ==========================================
    elif menu == "📈 Relatório de Caixa":
        st.title("📈 Relatório Gerencial e Fechamento de Caixa")
        st.write(f"Dados financeiros privados de: `{user.email}`")
        st.markdown("---")

        resposta = supabase.table("vendas").select("*").eq("user_id", user.id).execute()
        dados_vendas = resposta.data

        if dados_vendas:
            df = pd.DataFrame(dados_vendas)
            df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert('America/Sao_Paulo').dt.tz_localize(None)
            
            hoje = datetime.now().date()
            mes_atual = datetime.now().month
            ano_atual = datetime.now().year
            
            df_hoje = df[df['created_at'].dt.date == hoje]
            df_mes = df[(df['created_at'].dt.month == mes_atual) & (df['created_at'].dt.year == ano_atual)]
            
            st.markdown("### 💰 Faturamento de Hoje")
            c1, c2, c3, c4 = st.columns(4)
            val_pix = df_hoje[df_hoje['forma_pagamento'].str.contains('PIX', na=False)]['valor'].sum()
            val_cred = df_hoje[df_hoje['forma_pagamento'].str.contains('Crédito', na=False)]['valor'].sum()
            val_deb = df_hoje[df_hoje['forma_pagamento'].str.contains('Débito', na=False)]['valor'].sum()
            val_din = df_hoje[df_hoje['forma_pagamento'].str.contains('Dinheiro', na=False)]['valor'].sum()
            
            c1.metric(label="⚡ Total em PIX", value=f"R$ {val_pix:,.2f}")
            c2.metric(label="💳 Cartão de Crédito", value=f"R$ {val_cred:,.2f}")
            c3.metric(label="🏦 Cartão de Débito", value=f"R$ {val_deb:,.2f}")
            c4.metric(label="💵 Dinheiro Espécie", value=f"R$ {val_din:,.2f}")
            
            st.markdown("### 📅 Balanço Acumulado do Mês")
            total_mes = df_mes['valor'].sum()
            cm1, _ = st.columns(2)
            cm1.metric(label="💰 Faturamento Total do Mês", value=f"R$ {total_mes:,.2f}")
            
            st.markdown("#### 📋 Histórico Detalhado de Movimentações")
            df_exibir = df[['id', 'created_at', 'produto', 'valor', 'forma_pagamento']].copy()
            df_exibir['created_at'] = df_exibir['created_at'].dt.strftime('%d/%m/%Y %H:%M')
            df_exibir.columns = ['ID Venda', 'Data/Hora (BR)', 'Produto', 'Valor Total (R$)', 'Forma de Pagamento']
            st.dataframe(df_exibir.sort_values(by="ID Venda", ascending=False), use_container_width=True)
            
            st.markdown("---")
            st.subheader("❌ Cancelar Registro de Venda / Estorno")
            df['opcao_venda'] = df.apply(lambda r: f"ID: {r['id']} | {r['produto']} | R$ {r['valor']:.2f} ({r['forma_pagamento']})", axis=1)
            venda_selecionada_str = st.selectbox("Selecione a venda para cancelar:", df['opcao_venda'].tolist(), key="select_cancelar_venda")
            venda_dados_cancelar = df[df['opcao_venda'] == venda_selecionada_str].iloc[0]
            
            if st.button("🔥 Confirmar Cancelamento e Apagar Venda", key="btn_cancelar_venda"):
                try:
                    prod_nome = venda_dados_cancelar['produto']
                    resp_prod_estorno = supabase.table("produtos").select("*").eq("user_id", user.id).eq("nome_produto", prod_nome).execute()
                    
                    if resp_prod_estorno.data:
                        prod_banco = resp_prod_estorno.data[0]
                        preco_unitario = float(prod_banco['preco']) if prod_banco['preco'] else 1.0
                        qtd_vendida_calculada = round(float(venda_dados_cancelar['valor']) / preco_unitario)
                        
                        qtd_reposta = (prod_banco['estoque_atual'] if prod_banco['estoque_atual'] is not None else 0) + qtd_vendida_calculada
                        supabase.table("produtos").update({"estoque_atual": qtd_reposta}).eq("id_produto", prod_banco['id_produto']).execute()
                    
                    supabase.table("vendas").delete().eq("id", venda_dados_cancelar['id']).execute()
                    st.success(f"Venda cancelada e estoque reposto!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar cancelamento: {e}")
        else:
            st.info("Nenhuma venda registrada no sistema até o momento.")

    # ==========================================
    # TELA 3: 📦 CONTROLE DE ESTOQUE
    # ==========================================
    elif menu == "📦 Controle de Estoque":
        st.title("📦 Gestão de Estoque Inteligente")
        st.write("Cadastre seus produtos via planilha ou gerencie o inventário atual.")
        st.markdown("---")
        
        # Carrega fornecedores existentes para mapeamento
        resp_fornecedores = supabase.table("fornecedores").select("*").eq("user_id", user.id).execute()
        dict_fornecedores = {f["nome"].strip().lower(): f["id_fornecedor"] for f in resp_fornecedores.data} if resp_fornecedores.data else {}
        dict_fornecedores_original = {f["nome"]: f["id_fornecedor"] for f in resp_fornecedores.data} if resp_fornecedores.data else {}
        lista_nomes_forn = list(dict_fornecedores_original.keys())

        # --- SEÇÃO 1: IMPORTAÇÃO EM MASSA COM CADASTRO AUTOMÁTICO ---
        st.subheader("🚀 Cadastro em Lote (Excel / CSV)")
        expander_lote = st.expander("Clique aqui para enviar uma lista de produtos por Planilha", expanded=False)
        
        with expander_lote:
            # Guia de orientações para o usuário não cometer erros
            st.info("""
            💡 **Orientações para o preenchimento correto (Evite Erros):**
            1. **Fornecedor Automático:** Digite o nome do fornecedor na planilha. Se ele não existir, o sistema criará um cadastro novo para ele automaticamente!
            2. **Atenção à Grafia:** Para não duplicar fornecedores, certifique-se de digitar sempre o mesmo nome (Ex: Use sempre 'Ambev' e evite variações como 'Ambev S/A' ou 'Distribuidora Ambev').
            3. **Preços Sem Vírgula:** Use apenas **ponto (.)** para separar os centavos (Ex: `15.90`). Se usar vírgula, o sistema gerará erro.
            """)
            
            dados_modelo = {
                "nome_produto": ["Arroz Integral 5kg", "Feijão Carioca 1kg", "Óleo de Soja 900ml"],
                "preco_custo": [18.50, 6.20, 5.10],
                "preco_venda": [24.90, 8.50, 6.99],
                "quantidade_estoque": [50, 100, 60],
                "estoque_minimo_alerta": [10, 15, 12],
                "fornecedor": ["Distribuidora Alvorada", "Zé Atacadista", "Ambev"]
            }
            df_modelo = pd.DataFrame(dados_modelo)
            csv_modelo = df_modelo.to_csv(index=False, sep=";").encode('utf-8-sig')
            
            st.download_button(
                label="📥 Baixar Modelo Oficial de Planilha",
                data=csv_modelo,
                file_name="modelo_produtos_uniao_comercial.csv",
                mime="text/csv",
            )
            
            st.markdown("---")
            arquivo_enviado = st.file_uploader("Arraste ou selecione sua planilha preenchida (.csv ou .xlsx)", type=["csv", "xlsx"])
            
            if arquivo_enviado is not None:
                try:
                    if arquivo_enviado.name.endswith('.csv'):
                        df_carregado = pd.read_csv(arquivo_enviado, sep=";")
                    else:
                        df_carregado = pd.read_excel(arquivo_enviado)
                        
                    st.write("👀 Pré-visualização dos dados carregados:")
                    st.dataframe(df_carregado, use_container_width=True)
                    
                    if st.button("🔥 Confirmar e Cadastrar Tudo no Banco"):
                        contador_sucesso = 0
                        contador_novos_forn = 0
                        
                        for _, linha in df_carregado.iterrows():
                            custo = float(linha["preco_custo"])
                            venda = float(linha["preco_venda"])
                            lucro_calc = ((venda - custo) / custo) * 100 if custo > 0 else 0.0
                            
                            nome_f_bruto = str(linha["fornecedor"]).strip() if pd.notna(linha["fornecedor"]) else ""
                            nome_f_chave = nome_f_bruto.lower()
                            
                            id_forn_encontrado = None
                            if nome_f_bruto:
                                # Se já existe, pega o ID
                                if nome_f_chave in dict_fornecedores:
                                    id_forn_encontrado = dict_fornecedores[nome_f_chave]
                                else:
                                    # CADASTRO AUTOMÁTICO DO FORNECEDOR INEXISTENTE
                                    novo_forn_auto = {
                                        "user_id": user.id,
                                        "nome": nome_f_bruto,
                                        "telefone": "Criado via planilha",
                                        "email": "Criado via planilha"
                                    }
                                    res_f = supabase.table("fornecedores").insert(novo_forn_auto).execute()
                                    if res_f.data:
                                        id_forn_encontrado = res_f.data[0]["id_fornecedor"]
                                        # Atualiza os dicionários locais para as próximas linhas da mesma planilha
                                        dict_fornecedores[nome_f_chave] = id_forn_encontrado
                                        contador_novos_forn += 1
                            
                            novo_item_lote = {
                                "user_id": user.id,
                                "nome_produto": str(linha["nome_produto"]),
                                "ultimo_custo": custo,
                                "porcentagem_lucro": lucro_calc,
                                "preco": venda,
                                "estoque_atual": int(linha["quantidade_estoque"]),
                                "estoque_minimo": int(linha["estoque_minimo_alerta"]),
                                "id_fornecedor": id_forn_encontrado
                            }
                            
                            supabase.table("produtos").insert(novo_item_lote).execute()
                            contador_sucesso += 1
                            
                        st.success(f"🎉 Sucesso! {contador_sucesso} produtos processados. {contador_novos_forn} novos fornecedores foram criados automaticamente.")
                        st.rerun()
                except Exception as erro_carga:
                    st.error(f"Erro ao processar planilha. Certifique-se de usar ponto (.) nos centavos. Detalhes: {erro_carga}")
        
        st.markdown("---")

        # --- SEÇÃO 2: SITUAÇÃO ATUAL E EXCLUSÃO EM MASSA DE PRODUTOS ---
        resp_estoque = supabase.table("produtos").select("*").eq("user_id", user.id).execute()
        
        if resp_estoque.data:
            df_est = pd.DataFrame(resp_estoque.data)
            dict_id_para_nome_forn = {v: k for k, v in dict_fornecedores_original.items()}
            df_est['Fornecedor'] = df_est['id_fornecedor'].map(dict_id_para_nome_forn).fillna("Não associado")
            
            st.subheader("📋 Situação Atual do Estoque")
            
            df_visualizacao = df_est[['id_produto', 'nome_produto', 'Fornecedor', 'preco', 'estoque_atual']].copy()
            df_visualizacao.columns = ['ID', 'Produto', 'Fornecedor', 'Preço de Venda (R$)', 'Qtd Atual']
            
            df_visualizacao.insert(0, "Selecionar para Excluir", False)
            
            st.write("💡 Marque a caixinha dos produtos que deseja **remover em lote**:")
            df_editado_usuario = st.data_editor(
                df_visualizacao,
                hide_index=True,
                disabled=['ID', 'Produto', 'Fornecedor', 'Preço de Venda (R$)', 'Qtd Atual'],
                use_container_width=True
            )
            
            ids_para_deletar = df_editado_usuario[df_editado_usuario["Selecionar para Excluir"] == True]["ID"].tolist()
            
            if ids_para_deletar:
                st.warning(f"⚠️ Você selecionou {len(ids_para_deletar)} produto(s) para remoção definitiva.")
                if st.button("🗑️ Confirmar e Excluir Selecionados", type="primary"):
                    try:
                        for id_del in ids_para_deletar:
                            supabase.table("produtos").delete().eq("id_produto", id_del).execute()
                        st.success("💥 Os produtos selecionados foram removidos com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao deletar itens: {e}")
            
            st.markdown("---")
            
            # --- SEÇÃO 3: EDITAR OU CADASTRO MANUAL ---
            aba_manual, aba_editar = st.tabs(["🆕 Adicionar Item Manual", "✏️ Editar Item Existente"])
            
            with aba_manual:
                with st.form("form_cadastro_manual", clear_on_submit=True):
                    row1_col1, row1_col2, row1_col3 = st.columns(3)
                    with row1_col1:
                        nome_p = st.text_input("Nome do Produto")
                    with row1_col2:
                        qtd_inicial = st.number_input("Quantidade Inicial", min_value=0, step=1)
                    with row1_col3:
                        forn_sel = st.selectbox("Selecione o Fornecedor", ["Não associado"] + lista_nomes_forn)
                        
                    row2_col1, row2_col2, row2_col3 = st.columns(3)
                    with row2_col1:
                        custo_p = st.number_input("Preço de Custo (R$)", min_value=0.0, step=0.50)
                    with row2_col2:
                        venda_p = st.number_input("Preço de Venda (R$)", min_value=0.0, step=0.50)
                    with row2_col3:
                        estoque_min = st.number_input("Estoque Mínimo", min_value=1, value=5, step=1)
                        
                    if st.form_submit_button("Salvar Produto"):
                        if nome_p:
                            lucro_p_calculado = ((venda_p - custo_p) / custo_p) * 100 if custo_p > 0 else 0.0
                            id_do_fornecedor = dict_fornecedores_original.get(forn_sel, None) if forn_sel != "Não associado" else None
                            
                            novo_item = {
                                "user_id": user.id,
                                "nome_produto": nome_p,
                                "ultimo_custo": custo_p,
                                "porcentagem_lucro": lucro_p_calculado,
                                "preco": venda_p,
                                "estoque_atual": qtd_inicial,
                                "estoque_minimo": estoque_min,
                                "id_fornecedor": id_do_fornecedor
                            }
                            supabase.table("produtos").insert(novo_item).execute()
                            st.success(f"Produto '{nome_p}' cadastrado!")
                            st.rerun()
                            
            with aba_editar:
                lista_para_editar = df_est['nome_produto'].tolist()
                prod_para_editar = st.selectbox("Escolha o produto que deseja alterar:", lista_para_editar, key="select_edit")
                dados_item_edit = df_est[df_est['nome_produto'] == prod_para_editar].iloc[0]
                
                with st.form("form_edicao_produto", clear_on_submit=False):
                    edit_col1, edit_col2, edit_col3 = st.columns(3)
                    with edit_col1:
                        novo_nome = st.text_input("Nome do Produto", value=str(dados_item_edit['nome_produto']))
                    with edit_col2:
                        nova_qtd = st.number_input("Quantidade em Estoque", min_value=0, value=int(dados_item_edit['estoque_atual'] if dados_item_edit['estoque_atual'] is not None else 0), step=1)
                    with edit_col3:
                        nome_forn_atual = dict_id_para_nome_forn.get(dados_item_edit['id_fornecedor'], "Não associado")
                        opcoes_forn_edicao = ["Não associado"] + lista_nomes_forn
                        idx_forn = opcoes_forn_edicao.index(nome_forn_atual) if nome_forn_atual in opcoes_forn_edicao else 0
                        novo_forn_sel = st.selectbox("Alterar Fornecedor", opcoes_forn_edicao, index=idx_forn)

                    edit_col4, edit_col5, edit_col6 = st.columns(3)
                    with edit_col4:
                        val_custo_atual = float(dados_item_edit['ultimo_custo']) if dados_item_edit['ultimo_custo'] is not None else 0.0
                        novo_custo = st.number_input("Novo Preço de Custo (R$)", min_value=0.0, value=val_custo_atual, step=0.50)
                    with edit_col5:
                        val_venda_atual = float(dados_item_edit['preco']) if dados_item_edit['preco'] is not None else 0.0
                        novo_venda = st.number_input("Novo Preço de Venda (R$)", min_value=0.0, value=val_venda_atual, step=0.50)
                    with edit_col6:
                        val_min_atual = int(dados_item_edit['estoque_minimo']) if dados_item_edit['estoque_minimo'] is not None else 5
                        novo_min = st.number_input("Novo Estoque Mínimo", min_value=1, value=val_min_atual, step=1)
                    
                    if st.form_submit_button("💾 Salvar Alterações"):
                        novo_lucro_calculado = ((novo_venda - novo_custo) / novo_custo) * 100 if novo_custo > 0 else 0.0
                        id_do_novo_fornecedor = dict_fornecedores_original.get(novo_forn_sel, None) if novo_forn_sel != "Não associado" else None
                        
                        dados_atualizados = {
                            "nome_produto": novo_nome,
                            "ultimo_custo": novo_custo,
                            "porcentagem_lucro": novo_lucro_calculado,
                            "preco": novo_venda,
                            "estoque_atual": nova_qtd,
                            "estoque_minimo": novo_min,
                            "id_fornecedor": id_do_novo_fornecedor
                        }
                        supabase.table("produtos").update(dados_atualizados).eq("id_produto", dados_item_edit['id_produto']).execute()
                        st.success(f"🔄 Produto '{novo_nome}' atualizado!")
                        st.rerun()
        else:
            st.info("Nenhum produto cadastrado no estoque ainda.")

    # ==========================================
    # TELA 4: CADASTRAR/GERENCIAR FORNECEDORES
    # ==========================================
    elif menu == "🤝 Cadastrar Fornecedores":
        st.title("🤝 Gestão de Fornecedores de Alta Performance")
        st.write("Gerencie, edite e remova os parceiros comerciais vinculados ao estoque.")
        st.markdown("---")
        
        resp_f = supabase.table("fornecedores").select("*").eq("user_id", user.id).execute()
        lista_forn_banco = resp_f.data if resp_f.data else []
        
        # --- SUB-SEÇÃO A: SITUAÇÃO ATUAL E EXCLUSÃO EM MASSA DE FORNECEDORES ---
        if lista_forn_banco:
            df_f = pd.DataFrame(lista_forn_banco)
            st.subheader("📋 Fornecedores Cadastrados Atualmente")
            
            df_vis_f = df_f[['id_fornecedor', 'nome', 'telefone', 'email']].copy()
            df_vis_f.columns = ['ID Fornecedor', 'Nome / Empresa', 'Telefone de Contato', 'E-mail']
            df_vis_f.insert(0, "Selecionar para Excluir", False)
            
            st.write("💡 Marque os fornecedores que deseja **remover em lote** (Atenção: isso deixará os produtos deles sem vínculo):")
            df_editado_forn = st.data_editor(
                df_vis_f,
                hide_index=True,
                disabled=['ID Fornecedor', 'Nome / Empresa', 'Telefone de Contato', 'E-mail'],
                use_container_width=True
            )
            
            ids_forn_deletar = df_editado_forn[df_editado_forn["Selecionar para Excluir"] == True]["ID Fornecedor"].tolist()
            
            if ids_forn_deletar:
                st.warning(f"⚠️ Você selecionou {len(ids_forn_deletar)} fornecedor(es) para exclusão definitiva.")
                if st.button("🗑️ Confirmar e Excluir Fornecedores", type="primary", key="btn_del_forn_lote"):
                    try:
                        for id_f_del in ids_forn_deletar:
                            # Primeiro remove a referência nos produtos para não quebrar a chave estrangeira
                            supabase.table("produtos").update({"id_fornecedor": None}).eq("id_fornecedor", id_f_del).execute()
                            # Depois apaga o fornecedor
                            supabase.table("fornecedores").delete().eq("id_fornecedor", id_f_del).execute()
                        st.success("💥 Os parceiros comerciais selecionados foram removidos com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao remover fornecedores: {e}")
        else:
            st.info("Nenhum fornecedor cadastrado ainda.")
            
        st.markdown("---")
        
        # --- SUB-SEÇÃO B: TABS DE ADIÇÃO MANUAL OU EDIÇÃO ---
        aba_f_manual, aba_f_editar = st.tabs(["🆕 Registrar Fornecedor Manual", "✏️ Editar Fornecedor Existente"])
        
        with aba_f_manual:
            with st.form("form_fornecedor_manual", clear_on_submit=True):
                st.write("Insira os dados do novo distribuidor:")
                nome_f = st.text_input("Nome da Empresa / Fornecedor")
                telefone_f = st.text_input("Telefone de Contato")
                email_f = st.text_input("E-mail de Contato")
                
                if st.form_submit_button("Salvar Fornecedor"):
                    if nome_f:
                        novo_forn = {
                            "user_id": user.id,
                            "nome": nome_f,
                            "telefone": telefone_f if telefone_f else "Não informado",
                            "email": email_f if email_f else "Não informado"
                        }
                        supabase.table("fornecedores").insert(novo_forn).execute()
                        st.success(f"Fornecedor '{nome_f}' cadastrado com sucesso!")
                        st.rerun()
                        
        with aba_f_editar:
            if lista_forn_banco:
                lista_nomes_edicao_f = [f["nome"] for f in lista_forn_banco]
                forn_escolhido_edit = st.selectbox("Escolha qual fornecedor deseja alterar:", lista_nomes_edicao_f)
                dados_f_especificos = [f for f in lista_forn_banco if f["nome"] == forn_escolhido_edit][0]
                
                with st.form("form_edicao_fornecedor_manual"):
                    novo_nome_f = st.text_input("Alterar Nome", value=str(dados_f_especificos["nome"]))
                    novo_tel_f = st.text_input("Alterar Telefone", value=str(dados_f_especificos["telefone"]))
                    novo_email_f = st.text_input("Alterar E-mail", value=str(dados_f_especificos["email"]))
                    
                    if st.form_submit_button("💾 Salvar Alterações no Fornecedor"):
                        dados_f_atualizados = {
                            "nome": novo_nome_f,
                            "telefone": novo_tel_f,
                            "email": novo_email_f
                        }
                        supabase.table("fornecedores").update(dados_f_atualizados).eq("id_fornecedor", dados_f_especificos["id_fornecedor"]).execute()
                        st.success(f"🔄 Cadastro do fornecedor '{novo_nome_f}' atualizado!")
                        st.rerun()
            else:
                st.write("Sem fornecedores disponíveis para edição.")