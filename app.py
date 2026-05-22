import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import io

# Configuração da página web
st.set_page_config(page_title="Simulador Geofísico", layout="wide")

# =============================================================================
# 0. GERENCIAMENTO DE MEMÓRIA
# =============================================================================
if 'simulacao_concluida' not in st.session_state:
    st.session_state.simulacao_concluida = False
    st.session_state.resultados = []
    st.session_state.excel_buffer = None


# =============================================================================
# 1. FUNÇÕES MATEMÁTICAS VETORIZADAS
# =============================================================================
def calcular_razao_precisa(h_a, K, max_n=5000):
    h_a_arr = np.atleast_1d(h_a)[:, np.newaxis]
    n = np.arange(1, max_n + 1)[np.newaxis, :]
    K_n = K ** n
    termo1 = K_n / np.sqrt(1 + (2 * n * h_a_arr) ** 2)
    termo2 = K_n / np.sqrt(4 + (2 * n * h_a_arr) ** 2)
    soma = np.sum(termo1 - termo2, axis=1)
    resultado = 1.0 + 4 * soma
    return resultado[0] if np.isscalar(h_a) else resultado


x_vals = np.linspace(0.005, 2.0, 400)

# =============================================================================
# 2. INTERFACE DO USUÁRIO (WEB)
# =============================================================================
st.title("🌍 Simulador Geofísico: Cálculo do Fator K")
st.markdown("Insira os dados coletados em campo na tabela abaixo. Use **vírgula (,)** para separar as casas decimais.")

dados_iniciais = pd.DataFrame([
    {'Espaçamento a (m)': '4,0', 'Razão y': '0,593', 'Tipo K': 'Negativo'},
    {'Espaçamento a (m)': '6,0', 'Razão y': '0,710', 'Tipo K': 'Negativo'},
    {'Espaçamento a (m)': '8,0', 'Razão y': '0,850', 'Tipo K': 'Positivo'},
    {'Espaçamento a (m)': '10,0', 'Razão y': '0,920', 'Tipo K': 'Positivo'}
])

df_input = st.data_editor(
    dados_iniciais,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Tipo K": st.column_config.SelectboxColumn(
            "Tipo K",
            options=["Negativo", "Positivo"],
            required=True
        )
    }
)

# =============================================================================
# 3. MOTOR DE SIMULAÇÃO (Grava na Memória)
# =============================================================================
if st.button("🚀 Executar Simulação", type="primary"):
    st.session_state.resultados = []
    buffer_excel = io.BytesIO()

    with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Tabelas_de_Campo')

        formato_titulo_neg = workbook.add_format(
            {'bold': True, 'font_color': '#ffffff', 'bg_color': '#C00000', 'align': 'center', 'valign': 'vcenter',
             'border': 1})
        formato_titulo_pos = workbook.add_format(
            {'bold': True, 'font_color': '#ffffff', 'bg_color': '#203764', 'align': 'center', 'valign': 'vcenter',
             'border': 1})
        formato_cabecalho = workbook.add_format(
            {'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        formato_celula = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

        worksheet.set_column('A:A', 12)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 20)
        linha_atual = 0

        for index, row in df_input.iterrows():
            a_val = float(str(row['Espaçamento a (m)']).replace(',', '.'))
            y_constante = float(str(row['Razão y']).replace(',', '.'))
            tipo_k = str(row['Tipo K']).strip().lower()

            if tipo_k == 'positivo':
                valores_K = np.arange(0.1, 1.1, 0.1)
                y_curves = {K: 1.0 / calcular_razao_precisa(x_vals, K) for K in valores_K}
                label_y = r'$\frac{\rho_1}{\rho(a)}$'
                titulo_k = 'K Positivo'
            else:
                valores_K = np.arange(-0.1, -1.1, -0.1)
                y_curves = {K: calcular_razao_precisa(x_vals, K) for K in valores_K}
                label_y = r'$\frac{\rho(a)}{\rho_1}$'
                titulo_k = 'K Negativo'

            fig, ax = plt.subplots(figsize=(10, 6))
            dados_tabela = []
            ax.set_ylim(0, 1.05)
            ax.set_xlim(0, 2)

            for K in valores_K:
                y_vals = y_curves[K]
                ax.plot(x_vals, y_vals, color='black', alpha=0.7, linewidth=1.2)

                diferenca = y_vals - y_constante
                mudancas_sinal = np.where(np.diff(np.sign(diferenca)))[0]

                if len(mudancas_sinal) > 0:
                    idx = mudancas_sinal[0]
                    x1, x2 = x_vals[idx], x_vals[idx + 1]
                    y1_diff, y2_diff = diferenca[idx], diferenca[idx + 1]

                    h_a_exato = x1 - y1_diff * (x2 - x1) / (y2_diff - y1_diff)
                    h_calculado = h_a_exato * a_val

                    dados_tabela.append({
                        'K': f"{K:.1f}".replace('.', ','),
                        'h/a': f"{h_a_exato:.3f}".replace('.', ','),
                        f'h [m] (a={a_val})': f"{h_calculado:.3f}".replace('.', ',')
                    })

                    # Plotando os pontos e linhas de intersecção
                    ax.plot(h_a_exato, y_constante, 'ro', markersize=5)
                    ax.vlines(x=h_a_exato, ymin=0, ymax=y_constante, color='red', linestyle=':', alpha=0.6)

                    # Rótulo do eixo X em vermelho e inclinado
                    ax.text(h_a_exato, -0.08, f'{h_a_exato:.3f}', color='red', fontsize=10,
                            ha='right', va='top', rotation=45, transform=ax.get_xaxis_transform())
                else:
                    dados_tabela.append({'K': f"{K:.1f}".replace('.', ','), 'h/a': '-', f'h [m] (a={a_val})': '-'})

                # Rótulo do valor de K ao longo de cada curva
                idx_label = 55
                ax.text(x_vals[idx_label], y_vals[idx_label] + 0.015,
                        f'{K:.1f}'.replace('.', ','), fontsize=9, ha='center', va='bottom')

            # Estética completa do Gráfico (Reta, Eixos e Legendas matemáticas)
            ax.axhline(y=y_constante, color='red', linestyle='--', label=f'y = {y_constante:.3f}')

            ax.set_xticks(np.arange(0, 2.2, 0.2))
            ax.set_yticks(np.arange(0, 1.1, 0.1))

            ax.text(1.02, -0.02, r'$\frac{h}{a}$', fontsize=16, transform=ax.transAxes, ha='left', va='top')
            ax.text(-0.06, 1.05, label_y, fontsize=16, transform=ax.transAxes)

            ax.set_title(f'{titulo_k} | a = {a_val}m', fontsize=14)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), frameon=True)

            # Ajusta o layout para evitar cortes na imagem final
            fig.tight_layout()

            buf_img = io.BytesIO()
            fig.savefig(buf_img, format="png", dpi=600, bbox_inches="tight")
            buf_img.seek(0)
            plt.close(fig)

            df_resultados = pd.DataFrame(dados_tabela)

            st.session_state.resultados.append({
                'a_val': a_val,
                'imagem_bytes': buf_img.getvalue(),
                'tabela': df_resultados
            })

            # --- Gravar Tabela no Excel ---
            estilo_titulo = formato_titulo_pos if tipo_k == 'positivo' else formato_titulo_neg
            texto_titulo = f"a = {a_val}m  |  y = {y_constante:.3f}  |  K {tipo_k.capitalize()}"

            worksheet.merge_range(linha_atual, 0, linha_atual, 2, texto_titulo, estilo_titulo)
            linha_atual += 1
            for col_num, nome_coluna in enumerate(df_resultados.columns):
                worksheet.write(linha_atual, col_num, nome_coluna, formato_cabecalho)
            linha_atual += 1
            for _, row_df in df_resultados.iterrows():
                worksheet.write(linha_atual, 0, row_df.iloc[0], formato_celula)
                worksheet.write(linha_atual, 1, row_df.iloc[1], formato_celula)
                worksheet.write(linha_atual, 2, row_df.iloc[2], formato_celula)
                linha_atual += 1
            linha_atual += 2

    st.session_state.excel_buffer = buffer_excel.getvalue()
    st.session_state.simulacao_concluida = True

# =============================================================================
# 4. EXIBIÇÃO DOS RESULTADOS
# =============================================================================
if st.session_state.simulacao_concluida:
    st.divider()

    col_titulo, col_botao = st.columns([0.8, 0.2])
    with col_titulo:
        st.subheader("📊 Resultados da Simulação")
    with col_botao:
        if st.button("🔄 Nova Simulação"):
            st.session_state.simulacao_concluida = False
            st.rerun()

    colunas_web = st.columns(2)

    for idx, resultado in enumerate(st.session_state.resultados):
        with colunas_web[idx % 2]:
            st.image(resultado['imagem_bytes'], use_container_width=True)

            st.download_button(
                label=f"🖼️ Baixar Gráfico (a={resultado['a_val']}m)",
                data=resultado['imagem_bytes'],
                file_name=f"Grafico_a_{resultado['a_val']}m.png",
                mime="image/png",
                key=f"dl_img_{idx}"
            )

            st.dataframe(resultado['tabela'], use_container_width=True, hide_index=True)

    st.success("Tudo pronto!")
    st.download_button(
        label="📥 Baixar Relatório Excel Formatado",
        data=st.session_state.excel_buffer,
        file_name="Relatorio_Geofisico.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_excel_final"
    )