"""Interface Streamlit para consulta individual e previsão de CSVs."""

import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from churn.dashboard_client import (
    DashboardError, EXAMPLE_CUSTOMER, MAX_CSV_ROWS, check_health,
    customers_from_frame, predict_customers,
)

YES_NO = {"Yes": "Sim", "No": "Não"}


def choice(label, options, key, default=None):
    values = list(options)
    default = default if default is not None else EXAMPLE_CUSTOMER.get(key, values[0])
    return st.selectbox(label, values, index=values.index(default), format_func=options.get, key=key)


def show_results(result, threshold):
    st.subheader("Resultado da análise")
    st.caption(f"Limiar aplicado: {threshold:.0%}. A classe indica churn quando a probabilidade é maior ou igual ao limiar.")
    total, at_risk, average = st.columns(3)
    total.metric("Clientes analisados", len(result))
    at_risk.metric("Com indicação de churn", int(result.churn_prediction.sum()))
    average.metric("Probabilidade média", f"{result.churn_probability.mean():.1%}")
    if len(result) == 1:
        row = result.iloc[0]
        st.progress(float(row.churn_probability), text=f"Probabilidade de churn: {row.churn_probability:.1%}")
        if row.churn_prediction:
            st.warning("Cliente com indicação de churn. Avalie uma ação de retenção.")
        else:
            st.success("Cliente abaixo do limiar de churn definido para esta análise.")
    display = result.rename(columns={
        "customerID": "Cliente", "churn_probability": "Probabilidade de churn",
        "churn_prediction": "Indicação de churn (0/1)",
    })
    st.dataframe(display, hide_index=True, width="stretch", column_config={
        "Probabilidade de churn": st.column_config.NumberColumn(format="%.4f"),
    })
    st.download_button("Baixar previsões em CSV", result.to_csv(index=False).encode("utf-8-sig"),
                       file_name="previsoes_churn.csv", mime="text/csv")


def individual(threshold):
    st.subheader("Conheça o risco de cada cliente")
    st.write("Preencha o perfil e os serviços contratados para estimar a probabilidade de cancelamento.")
    with st.form("customer_form"):
        left, right = st.columns(2)
        customer = {}
        with left:
            st.markdown("#### Perfil do cliente")
            customer_id = st.text_input("Identificador do cliente (opcional)", key="customer_id")
            customer["gender"] = choice("Gênero", {"Female": "Feminino", "Male": "Masculino"}, "gender")
            customer["SeniorCitizen"] = choice("Pessoa idosa", {0: "Não", 1: "Sim"}, "SeniorCitizen")
            customer["Partner"] = choice("Possui parceiro(a)", YES_NO, "Partner")
            customer["Dependents"] = choice("Possui dependentes", YES_NO, "Dependents")
            customer["tenure"] = st.number_input("Tempo como cliente (meses)", min_value=0, value=12, step=1, key="tenure")
            customer["Contract"] = choice("Contrato", {
                "Month-to-month": "Mensal", "One year": "Um ano", "Two year": "Dois anos",
            }, "Contract")
            customer["PaperlessBilling"] = choice("Fatura digital", YES_NO, "PaperlessBilling")
            customer["PaymentMethod"] = choice("Forma de pagamento", {
                "Electronic check": "Cheque eletrônico", "Mailed check": "Cheque pelo correio",
                "Bank transfer (automatic)": "Transferência automática",
                "Credit card (automatic)": "Cartão de crédito automático",
            }, "PaymentMethod")
            customer["MonthlyCharges"] = st.number_input("Cobrança mensal (unidade monetária da base)", min_value=0.0, value=89.9, step=1.0, key="MonthlyCharges")
            customer["TotalCharges"] = st.number_input("Total cobrado (unidade monetária da base)", min_value=0.0, value=1078.8, step=1.0, key="TotalCharges")
        with right:
            st.markdown("#### Serviços contratados")
            customer["PhoneService"] = choice("Telefonia", YES_NO, "PhoneService")
            customer["MultipleLines"] = choice("Múltiplas linhas", {**YES_NO, "No phone service": "Sem telefonia"}, "MultipleLines")
            customer["InternetService"] = choice("Internet", {"DSL": "DSL", "Fiber optic": "Fibra óptica", "No": "Sem internet"}, "InternetService")
            for key, label in [
                ("OnlineSecurity", "Segurança online"), ("OnlineBackup", "Backup online"),
                ("DeviceProtection", "Proteção de dispositivo"), ("TechSupport", "Suporte técnico"),
                ("StreamingTV", "Streaming de TV"), ("StreamingMovies", "Streaming de filmes"),
            ]:
                customer[key] = choice(label, {**YES_NO, "No internet service": "Sem internet"}, key)
            st.info("O modelo estima uma probabilidade; a decisão de retenção deve considerar o contexto do cliente.")
        submitted = st.form_submit_button("Analisar cliente", type="primary", width="stretch")
    if submitted:
        st.session_state.pop("individual_result", None)
        if customer_id.strip():
            customer["customerID"] = customer_id.strip()
        # Harmoniza os serviços quando não existe telefonia ou internet.
        if customer["PhoneService"] == "No":
            customer["MultipleLines"] = "No phone service"
        if customer["InternetService"] == "No":
            for key in ("OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"):
                customer[key] = "No internet service"
        try:
            with st.spinner("Consultando o modelo pela API..."):
                result = predict_customers([customer], threshold)
            st.session_state["individual_result"] = (result, threshold)
        except DashboardError as exc:
            st.error(str(exc))
    if "individual_result" in st.session_state:
        result, used_threshold = st.session_state["individual_result"]
        show_results(result, used_threshold)


def batch(threshold):
    st.subheader("Analise sua carteira de clientes")
    st.write(f"Envie um CSV com até {MAX_CSV_ROWS:,} clientes. As consultas são divididas em lotes de até 1.000 linhas.")
    st.download_button("Baixar modelo de CSV", pd.DataFrame([{"customerID": "cliente-001", **EXAMPLE_CUSTOMER}]).to_csv(index=False).encode("utf-8-sig"),
                       file_name="modelo_clientes.csv", mime="text/csv")
    st.caption("Use UTF-8, vírgula ou ponto e vírgula como separador e ponto decimal. Colunas numéricas vazias são aceitas. A coluna Churn é ignorada.")
    upload = st.file_uploader("Arquivo de clientes", type=["csv"])
    if upload is None:
        st.session_state.pop("batch_result", None)
        return
    import hashlib

    upload_key = hashlib.sha256(upload.getvalue()).hexdigest()
    if st.session_state.get("batch_upload") != upload_key:
        st.session_state.pop("batch_result", None)
        st.session_state["batch_upload"] = upload_key
    try:
        frame = pd.read_csv(upload, sep=None, engine="python", dtype=str, keep_default_na=False, encoding="utf-8-sig", nrows=MAX_CSV_ROWS + 1)
        customers = customers_from_frame(frame)
    except (ValueError, UnicodeError, pd.errors.ParserError, DashboardError) as exc:
        st.error(str(exc) if isinstance(exc, DashboardError) else "Não foi possível ler o CSV. Confira a codificação, o separador e os cabeçalhos.")
        return
    st.caption(f"{len(customers):,} clientes prontos para análise.")
    st.dataframe(frame.head(10), hide_index=True, width="stretch")
    if st.button("Analisar CSV", type="primary"):
        st.session_state.pop("batch_result", None)
        try:
            with st.spinner("Consultando os lotes na API..."):
                result = predict_customers(customers, threshold)
            st.session_state["batch_result"] = (result, threshold)
        except DashboardError as exc:
            st.error(str(exc))
    if "batch_result" in st.session_state:
        result, used_threshold = st.session_state["batch_result"]
        show_results(result, used_threshold)


def main():
    st.set_page_config(page_title="Churn | Análise de clientes", page_icon="📊", layout="wide")
    st.markdown("""<style>
        .stApp {background: #f5f7fb; color: #17243b;}
        h1, h2, h3 {letter-spacing: -0.025em;}
        [data-testid="stMetric"] {background: white; border: 1px solid #dce4ef; padding: 1rem; border-radius: 12px;}
        [data-testid="stForm"] {background: white; border-radius: 16px;}
        </style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("## Churn Analytics")
        st.caption("Inteligência para retenção de clientes")
        st.divider()
        threshold = st.slider("Limiar de classificação", min_value=0.0, max_value=1.0, value=0.5, step=0.05)
        st.caption("Um limiar menor sinaliza mais clientes para avaliação. Alterá-lo exige uma nova análise.")
        st.divider()
        if check_health():
            st.success("API conectada")
        else:
            st.warning("API iniciando ou indisponível. Aguarde e clique em Verificar conexão.")
        st.button("Verificar conexão")
        docs_url = os.environ.get("CHURN_API_PUBLIC_URL")
        if docs_url:
            st.link_button("Documentação da API", docs_url.rstrip("/") + "/docs")
        st.caption("Streamlit · FastAPI · MLflow")
    st.title("Antecipe o churn. Cuide de quem fica.")
    st.write("Transforme o perfil dos seus clientes em sinais para apoiar ações de retenção.")
    single_tab, csv_tab = st.tabs(["Análise individual", "Análise por CSV"])
    with single_tab:
        individual(threshold)
    with csv_tab:
        batch(threshold)
    st.caption("As previsões são estimativas do modelo treinado. O limiar padrão de 50% não foi otimizado por custo de negócio.")


def cli():
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()),
        "--server.address", "127.0.0.1", *sys.argv[1:],
    ]))


if __name__ == "__main__":
    main()
