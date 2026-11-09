"""Churn Radar: consulta por customerID com a base e o modelo existentes."""

import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from churn.dashboard_client import (
    DashboardError, check_health, customer_from_id, customers_from_frame,
    load_customer_base, predict_customers,
)

THRESHOLD = 0.5
CLASSIFICATION = {
    0: "SIM — tende a continuar pagando",
    1: "NÃO — tende a cancelar o serviço",
}

RADAR_STYLE = """<style>
    :root {--radar-ink:#111c36; --radar-muted:#69738c; --radar-purple:#5143e9;}
    .stApp {
        background: radial-gradient(ellipse at 15% 5%, #eaeaff 0%, transparent 48%),
                    linear-gradient(135deg, #f3f3fd 0%, #f8f9fe 65%, #f0f2fb 100%);
        color:var(--radar-ink);
    }
    [data-testid="stHeader"] {background:transparent;}
    [data-testid="stMainBlockContainer"] {max-width:1040px; padding:3rem 2.2rem 2rem;}
    h1 {text-align:center; font-size:clamp(2rem,4.2vw,2.8rem)!important;
        line-height:1.17!important; font-weight:780!important; letter-spacing:-.045em!important;
        color:var(--radar-ink)!important; padding:0!important; margin:0 auto 1rem!important; max-width:820px;}
    .radar-brand {display:flex; justify-content:center; align-items:center; gap:12px;
        margin:0 auto 2.2rem; color:var(--radar-purple); font-size:11px; font-weight:800; letter-spacing:.21em;}
    .radar-mark {width:36px;height:36px;display:grid;place-items:center;background:var(--radar-purple);
        color:white;border-radius:12px;box-shadow:0 6px 15px #5143e928;}
    .radar-subtitle {text-align:center;max-width:610px;margin:.25rem auto 1.2rem;color:var(--radar-muted);
        font-size:15px;line-height:1.8;}
    .radar-subtitle code {background:#eeecff;color:#5143e9;padding:3px 6px;border-radius:6px;font-size:13px;}
    .radar-meta {display:flex;justify-content:center;align-items:center;gap:14px;flex-wrap:wrap;
        font-size:11px;color:#79829a;margin-bottom:1.8rem;}
    .radar-meta strong {font-weight:650;color:#59647c;}
    .status-dot {display:inline-block;width:6px;height:6px;border-radius:50%;background:#26a886;margin-right:6px;}
    .status-dot.waiting {background:#c58b29;}
    .st-key-lookup_card {background:#fff;border:1px solid #e0e4f4!important;border-radius:26px!important;
        padding:30px 34px!important;box-shadow:0 22px 50px -30px #23305155;margin-bottom:.5rem;}
    .card-eyebrow {color:#8b91a8;font-weight:750;font-size:10px;letter-spacing:.15em;margin:0 0 18px;}
    .st-key-customer_id label p {font-size:12px;font-weight:600;color:#495776;}
    .st-key-customer_id [data-baseweb="input"] {height:54px;border:1px solid #dfe3f4;border-radius:14px;
        background:#fff;box-shadow:none;}
    .st-key-customer_id input {font-size:14px;padding-left:16px;color:#17223c;}
    .st-key-customer_id [data-baseweb="input"]:focus-within {border-color:#7062f0;box-shadow:0 0 0 3px #5143e911;}
    .st-key-lookup_card [data-testid="stFormSubmitButton"] button {
        height:54px;border:none;border-radius:14px;background:#5143e9;color:white;
        font-size:13px;font-weight:650;box-shadow:0 8px 18px -8px #5143e9a0;transition:background .18s,transform .18s;}
    .st-key-lookup_card [data-testid="stFormSubmitButton"] button:hover {background:#4034cd;transform:translateY(-1px);}
    .st-key-lookup_card [data-testid="stFormSubmitButton"] button:focus-visible {outline:3px solid #b8b0ff;outline-offset:3px;}
    .examples-label {font-size:11px;color:#77819b;margin:6px 0 3px;}
    .st-key-examples [data-testid="stButton"] button {
        background:#fff;color:#6253e9;border:1px solid #e1dffa;border-radius:999px;
        min-height:32px;padding:3px 12px;font-weight:500;font-size:11px;box-shadow:none;}
    .st-key-examples [data-testid="stButton"] button:hover {background:#f2efff;border-color:#b8adff;}
    .st-key-prediction_card {background:white;border:1px solid #e0e4f4!important;border-radius:24px!important;
        padding:28px 34px!important;box-shadow:0 18px 40px -30px #23305155;margin-top:10px;}
    .result-heading {display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:16px;}
    .result-eyebrow {font-size:10px;letter-spacing:.12em;font-weight:750;color:#8b91a8;margin:0 0 5px;}
    .result-id {font-size:19px;font-weight:750;color:#192641;margin:0;}
    .class-badge {font-size:11px;font-weight:650;border-radius:999px;padding:7px 12px;white-space:nowrap;}
    .class-badge.stay {background:#edf9f4;color:#187d5e;}
    .class-badge.leave {background:#fff3e7;color:#a45a14;}
    .verdict {font-size:22px;font-weight:750;letter-spacing:-.02em;line-height:1.35;margin:0 0 6px;color:#17223c;}
    .verdict-description {font-size:12px;line-height:1.7;color:#79829a;margin:0 0 20px;}
    .st-key-prediction_card [data-testid="stMetric"] {background:#f6f5ff;border:1px solid #eeebff;border-radius:16px;padding:16px 20px;}
    .st-key-prediction_card [data-testid="stMetricLabel"] p {color:#747496;font-size:12px;}
    .st-key-prediction_card [data-testid="stMetricValue"] {color:#5143e9;font-weight:750;font-size:36px;}
    .st-key-prediction_card [data-testid="stProgress"] > div > div {background:#ebe8ff;}
    .st-key-prediction_card [data-testid="stProgress"] > div > div > div {background:#6959f0;}
    .radar-footer {max-width:700px;margin:18px auto 0;text-align:center;color:#838ca3;font-size:11px;line-height:1.9;}
    .radar-footer strong {color:#6a7390;font-weight:550;}
    [data-testid="stExpander"] {border-color:#e5e7f2;border-radius:12px;background:transparent;}
    [data-testid="stExpander"] summary p {font-size:12px;color:#78819a;}
    @media(max-width:640px) {
        [data-testid="stMainBlockContainer"] {padding:2rem 1rem 1.5rem;}
        .radar-brand {margin-bottom:1.7rem;}
        .st-key-lookup_card,.st-key-prediction_card {padding:22px 18px!important;border-radius:20px!important;}
        .radar-subtitle {font-size:13px;}
        .radar-meta {gap:10px;font-size:10px;}
        .verdict {font-size:19px;}
        .st-key-prediction_card [data-testid="stMetric"] {padding:12px;}
        .st-key-prediction_card [data-testid="stMetricValue"] {font-size:28px;}
    }
</style>"""


def select_example(customer_id):
    st.session_state["customer_id"] = customer_id
    st.session_state["pending_customer"] = customer_id


def show_prediction(result, customer):
    row = result.iloc[0]
    prediction = int(row.churn_prediction)
    probability = float(row.churn_probability)
    customer_id = escape(str(customer["customerID"]))
    badge = "Classe 1 · cancelamento" if prediction else "Classe 0 · permanência"
    description = (
        "O perfil deste cliente tem indicação de cancelamento. Vale avaliar uma ação de retenção."
        if prediction else
        "O perfil deste cliente tem indicação de permanência no serviço."
    )
    with st.container(border=True, key="prediction_card"):
        st.markdown(f'''<div class="result-heading"><div><p class="result-eyebrow">RESULTADO DA CONSULTA</p>
            <p class="result-id">Cliente {customer_id}</p></div>
            <span class="class-badge {'leave' if prediction else 'stay'}">{badge}</span></div>
            <p class="verdict">{CLASSIFICATION[prediction]}</p>
            <p class="verdict-description">{description}</p>''', unsafe_allow_html=True)
        cancel, stay = st.columns(2)
        cancel.metric("Chance de cancelar", f"{probability:.1%}")
        stay.metric("Chance de permanecer", f"{1 - probability:.1%}")
        st.progress(probability, text="Probabilidade de cancelamento estimada pelo modelo")
        st.caption("Classificação recebida do modelo treinado · limiar de decisão: 50%.")
        with st.expander("Ver dados utilizados na análise"):
            st.dataframe(pd.DataFrame([customer]), hide_index=True, width="stretch")
        with st.expander("Ver resposta original da API"):
            response = result.attrs.get("api_response")
            if response is None:
                response = {"predictions": json.loads(result.to_json(orient="records", double_precision=15)), "threshold": THRESHOLD}
            st.json(response)
            st.download_button("Baixar resultado em JSON", json.dumps(response, ensure_ascii=False, indent=2),
                               file_name=f"previsao_{customer['customerID']}.json", mime="application/json", key="single_json")
            docs_url = os.environ.get("CHURN_API_PUBLIC_URL")
            if docs_url:
                st.link_button("Abrir documentação da API", docs_url.rstrip("/") + "/docs")


def lookup(frame):
    with st.container(border=True, key="lookup_card"):
        st.markdown('<p class="card-eyebrow">ENCONTRE SEU CLIENTE</p>', unsafe_allow_html=True)
        with st.form("customer_lookup", border=False):
            field, submit = st.columns([3.2, 1.2], gap="medium", vertical_alignment="bottom")
            with field:
                customer_id = st.text_input("Código do cliente", placeholder=f"Ex.: {frame.customerID.iloc[0]}",
                                            key="customer_id", max_chars=100)
            with submit:
                submitted = st.form_submit_button("Consultar", type="primary", width="stretch")
        st.markdown('<p class="examples-label">Experimente um cliente da sua base</p>', unsafe_allow_html=True)
        examples = frame.customerID.astype(str).str.strip().drop_duplicates().head(4).tolist()
        with st.container(key="examples"):
            buttons = st.columns([1, 1, 1, 1, 1.3], gap="small")
            for index, example in enumerate(examples):
                buttons[index].button(example, key=f"example_{index}", on_click=select_example, args=(example,), width="stretch")
        pending = st.session_state.pop("pending_customer", None)
        if submitted or pending is not None:
            st.session_state.pop("customer_prediction", None)
            try:
                customer = customer_from_id(frame, pending if pending is not None else customer_id)
                with st.spinner("Consultando o modelo treinado..."):
                    result = predict_customers([customer], THRESHOLD)
                st.session_state["customer_prediction"] = (result, customer)
            except DashboardError as exc:
                st.error(str(exc))
    if "customer_prediction" in st.session_state:
        result, customer = st.session_state["customer_prediction"]
        show_prediction(result, customer)


def portfolio(frame):
    with st.expander("Consultar a base completa"):
        st.caption(f"Classifique os {len(frame):,} clientes de churn.csv com o mesmo modelo.")
        if st.button("Classificar toda a base", key="classify_base"):
            st.session_state.pop("portfolio_prediction", None)
            try:
                with st.spinner("Analisando os clientes da base..."):
                    result = predict_customers(customers_from_frame(frame), THRESHOLD)
                st.session_state["portfolio_prediction"] = result
            except DashboardError as exc:
                st.error(str(exc))
        result = st.session_state.get("portfolio_prediction")
        if result is not None:
            display = result.copy()
            display["Classificação"] = display.churn_prediction.map(CLASSIFICATION)
            st.dataframe(display, hide_index=True, width="stretch")
            st.download_button("Baixar classificações em CSV", display.to_csv(index=False).encode("utf-8-sig"),
                               file_name="classificacoes_churn.csv", mime="text/csv", key="portfolio_csv")
            with st.expander("Resposta original dos lotes da API"):
                st.json(result.attrs.get("api_response"), expanded=False)


def main():
    st.set_page_config(page_title="Churn Radar | Consulta de clientes", page_icon="📈", layout="wide")
    st.markdown(RADAR_STYLE, unsafe_allow_html=True)
    st.markdown('''<div class="radar-brand"><span class="radar-mark" aria-hidden="true">
        <svg width="21" height="21" viewBox="0 0 24 24" fill="none"><path d="M5 16L10 10L14 13L20 5M16 5H20V9"
        stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </span> CHURN RADAR</div>''', unsafe_allow_html=True)
    st.title("Qual a chance deste cliente cancelar?")
    st.markdown('<p class="radar-subtitle">Informe o código do cliente (<code>customerID</code>) e descubra a probabilidade de cancelamento com o modelo já treinado.</p>', unsafe_allow_html=True)
    try:
        frame = load_customer_base()
        if "customerID" not in frame or frame.customerID.astype("string").str.strip().eq("").any() or frame.customerID.isna().any():
            raise DashboardError("A base churn.csv precisa ter um customerID preenchido para cada cliente.")
    except DashboardError as exc:
        st.error(str(exc))
        return
    connected = check_health()
    status = "Modelo conectado" if connected else "Modelo iniciando ou indisponível"
    st.markdown(f'''<div class="radar-meta"><span><strong>churn.csv</strong> · {len(frame):,} clientes</span>
        <span><i class="status-dot{'' if connected else ' waiting'}"></i>{status}</span></div>''', unsafe_allow_html=True)
    lookup(frame)
    st.markdown('''<p class="radar-footer">Dados da sua base <strong>churn.csv</strong>, analisados pelo modelo treinado neste projeto.<br>
        A previsão estima permanência ou cancelamento do serviço; não representa garantia de pagamento.</p>''', unsafe_allow_html=True)
    portfolio(frame)


def cli():
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()),
        "--server.address", "127.0.0.1", *sys.argv[1:],
    ]))


if __name__ == "__main__":
    main()
