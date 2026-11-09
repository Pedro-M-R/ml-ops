"""Permanência: consulta por customerID com a base e o modelo existentes."""

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

APP_STYLE = """<style>
    :root {--ink:#173532; --muted:#74817a; --accent:#176b58; --paper:#f5f5ef;}
    .stApp {background:#f5f5ef;color:var(--ink);}
    [data-testid="stHeader"] {background:transparent;}
    [data-testid="stMainBlockContainer"] {max-width:1240px;padding:2.4rem 2.5rem 2rem;}
    .app-bar {display:flex;justify-content:space-between;align-items:center;gap:20px;
        padding-bottom:22px;margin-bottom:40px;border-bottom:1px solid #dce2d7;flex-wrap:wrap;}
    .wordmark {display:flex;align-items:center;gap:12px;color:#173532;}
    .brand-symbol {display:grid;place-items:center;width:37px;height:37px;background:#173532;
        border-radius:9px;color:#d6edbb;font-size:23px;font-weight:750;}
    .brand-name {font-size:16px;font-weight:750;letter-spacing:-.04em;}
    .brand-subtitle {font-size:10px;letter-spacing:.11em;text-transform:uppercase;color:#7b877c;margin-top:2px;}
    .app-status {display:flex;gap:18px;align-items:center;font-size:11px;color:#7a857c;flex-wrap:wrap;}
    .status-dot {display:inline-block;width:6px;height:6px;border-radius:50%;background:#368663;margin-right:6px;}
    .status-dot.waiting {background:#b98436;}
    .intro-eyebrow {font-size:10px;font-weight:750;color:#8a957d;letter-spacing:.16em;margin:12px 0 18px;}
    h1 {font-family:Georgia,'Times New Roman',serif!important;font-weight:400!important;
        font-size:clamp(2.5rem,4.2vw,3.4rem)!important;line-height:1.08!important;
        letter-spacing:-.055em!important;text-align:left!important;color:#173532!important;
        padding:0!important;margin:0 0 22px!important;max-width:440px;}
    .intro-description {font-size:14px;color:#74817a;line-height:1.9;max-width:360px;margin:0 0 28px;}
    .source-card {position:relative;overflow:hidden;background:#193f37;border-radius:14px;
        padding:24px 26px;color:#e7eee0;max-width:365px;margin-top:30px;}
    .source-card:after {content:"";position:absolute;width:165px;height:165px;border:1px solid #ffffff13;
        border-radius:50%;top:-82px;right:-45px;box-shadow:0 0 0 25px #ffffff04,0 0 0 50px #ffffff03;pointer-events:none;}
    .source-label {font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#b0c6ad;margin-bottom:14px;}
    .source-count {font-family:Georgia,serif;font-size:52px;font-weight:400;line-height:1;color:#e6f0c8;letter-spacing:-.04em;}
    .source-description {font-size:12px;color:#c1d1bc;line-height:1.8;margin:7px 0 22px;}
    .source-foot {display:flex;justify-content:space-between;gap:15px;border-top:1px solid #ffffff1c;
        padding-top:14px;color:#abc1a9;font-size:10px;}
    .source-foot strong {color:#d1e1c5;font-weight:500;}
    .st-key-lookup_card {background:white;border:1px solid #dfe5da!important;border-radius:16px!important;
        padding:26px 30px!important;box-shadow:0 3px 5px #223b2803;margin-bottom:4px;}
    .card-eyebrow {font-size:10px;font-weight:750;letter-spacing:.12em;color:#8a987f;margin:0 0 10px;}
    .lookup-heading {font-size:24px;font-weight:650;letter-spacing:-.045em;color:#203c32;margin:0 0 6px;}
    .lookup-description {font-size:12px;color:#86907e;margin:0 0 20px;line-height:1.6;}
    .st-key-customer_id label p {font-size:12px;font-weight:550;color:#52604c;}
    .st-key-customer_id [data-baseweb="input"] {height:50px;background:#f9faf6;
        border:1px solid #dce4d5;border-radius:8px;box-shadow:none;}
    .st-key-customer_id input {font-size:14px;padding-left:14px;color:#203c32;}
    .st-key-customer_id [data-baseweb="input"]:focus-within {border-color:#428875;box-shadow:0 0 0 3px #176b580e;}
    .st-key-lookup_card [data-testid="stFormSubmitButton"] button {height:47px;
        background:#176b58;border:none;border-radius:8px;color:white;box-shadow:none;font-weight:600;font-size:13px;}
    .st-key-lookup_card [data-testid="stFormSubmitButton"] button:hover {background:#115442;color:white;}
    .st-key-lookup_card [data-testid="stFormSubmitButton"] button:focus-visible {outline:3px solid #a7cab1;outline-offset:3px;}
    .examples-label {font-size:10px;color:#96a08d;margin:14px 0 5px;letter-spacing:.04em;}
    .st-key-examples [data-testid="stButton"] button {min-height:35px;background:#f6f8f2;
        color:#58734d;border:1px solid #e4e9dd;border-radius:6px;box-shadow:none;font-size:11px;font-weight:500;}
    .st-key-examples [data-testid="stButton"] button:hover {background:#eaf0e2;border-color:#c9d9bc;}
    .st-key-prediction_card {background:#fff;border:1px solid #dfe5da!important;border-radius:16px!important;
        padding:24px 28px!important;box-shadow:none;margin-top:8px;}
    .result-heading {display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:18px;}
    .result-eyebrow {font-size:10px;font-weight:750;letter-spacing:.11em;color:#8a987f;margin:0 0 7px;}
    .result-id {font-size:17px;font-weight:650;color:#203c32;margin:0;}
    .class-badge {font-size:10px;font-weight:600;border-radius:5px;padding:6px 9px;}
    .class-badge.stay {background:#eaf4e6;color:#42733f;}
    .class-badge.leave {background:#fbefde;color:#a26924;}
    .verdict {font-size:21px;font-weight:650;letter-spacing:-.035em;line-height:1.3;margin:0 0 8px;color:#203c32;}
    .verdict-description {font-size:12px;line-height:1.7;color:#87917f;margin:0 0 20px;}
    .st-key-prediction_card [data-testid="stMetric"] {background:#f4f7ef;border:0;border-radius:8px;padding:14px 16px;}
    .st-key-prediction_card [data-testid="stMetricLabel"] p {color:#7c8e70;font-size:11px;}
    .st-key-prediction_card [data-testid="stMetricValue"] {font-family:Georgia,serif;color:#305c44;font-size:33px;font-weight:400;}
    .st-key-prediction_card [data-testid="stProgress"] > div > div {background:#e2eada;}
    .st-key-prediction_card [data-testid="stProgress"] > div > div > div {background:#5d8964;}
    .empty-result {border:1px dashed #d5dfcd;border-radius:14px;padding:24px;text-align:center;margin-top:10px;}
    .empty-icon {display:inline-grid;place-items:center;width:32px;height:32px;border-radius:50%;
        background:#e8eee1;color:#648360;font-size:17px;margin-bottom:10px;}
    .empty-title {color:#77886d;font-size:12px;font-weight:600;margin:0 0 5px;}
    .empty-description {color:#9aa58f;font-size:11px;line-height:1.6;margin:0;}
    .app-footer {border-top:1px solid #dce2d7;margin-top:32px;padding-top:16px;color:#919b87;
        font-size:10px;line-height:1.9;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;}
    [data-testid="stExpander"] {background:transparent;border-color:#dfe5d8;border-radius:8px;}
    [data-testid="stExpander"] summary p {font-size:11px;color:#84917a;}
    @media(max-width:700px) {
        [data-testid="stMainBlockContainer"] {padding:1.8rem 1.2rem;}
        .app-bar {margin-bottom:16px;gap:12px;padding-bottom:16px;}
        h1 {font-size:2.5rem!important;max-width:460px;}
        .intro-description {max-width:100%;margin-bottom:8px;font-size:13px;}
        .source-card {display:none;}
        .intro-eyebrow {margin-top:4px;margin-bottom:12px;}
        .st-key-lookup_card,.st-key-prediction_card {padding:20px!important;}
        .app-status {font-size:10px;gap:10px;}
        .verdict {font-size:19px;}
        .st-key-prediction_card [data-testid="stMetricValue"] {font-size:27px;}
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
        st.markdown(f'''<div class="result-heading"><div><p class="result-eyebrow">02 / RESULTADO DA ANÁLISE</p>
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
        st.markdown('''<p class="card-eyebrow">01 / CONSULTA INDIVIDUAL</p>
            <p class="lookup-heading">Localizar cliente</p>
            <p class="lookup-description">Busque pelo código registrado na sua carteira.</p>''', unsafe_allow_html=True)
        with st.form("customer_lookup", border=False):
            customer_id = st.text_input("Código do cliente", placeholder=f"Ex.: {frame.customerID.iloc[0]}",
                                        key="customer_id", max_chars=100)
            submitted = st.form_submit_button("Consultar", type="primary", width="stretch")
        st.markdown('<p class="examples-label">CLIENTES DA SUA BASE</p>', unsafe_allow_html=True)
        examples = frame.customerID.astype(str).str.strip().drop_duplicates().head(4).tolist()
        with st.container(key="examples"):
            for offset in range(0, len(examples), 2):
                buttons = st.columns(2, gap="small")
                for index, example in enumerate(examples[offset:offset + 2], start=offset):
                    buttons[index - offset].button(example, key=f"example_{index}", on_click=select_example,
                                                    args=(example,), width="stretch")
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
    else:
        st.markdown('''<div class="empty-result"><span class="empty-icon" aria-hidden="true">⌁</span>
            <p class="empty-title">Sua próxima análise começa aqui</p>
            <p class="empty-description">Consulte um cliente para visualizar a probabilidade<br>
            e a classificação do modelo.</p></div>''', unsafe_allow_html=True)


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
    st.set_page_config(page_title="Permanência | Análise de clientes", page_icon="🌿", layout="wide")
    st.markdown(APP_STYLE, unsafe_allow_html=True)
    try:
        frame = load_customer_base()
        if "customerID" not in frame or frame.customerID.astype("string").str.strip().eq("").any() or frame.customerID.isna().any():
            raise DashboardError("A base churn.csv precisa ter um customerID preenchido para cada cliente.")
    except DashboardError as exc:
        st.error(str(exc))
        return
    connected = check_health()
    status = "Modelo disponível" if connected else "Modelo iniciando ou indisponível"
    count = f"{len(frame):,}".replace(",", ".")
    st.markdown(f'''<div class="app-bar"><div class="wordmark">
        <span class="brand-symbol" aria-hidden="true">p</span><div><div class="brand-name">permanência</div>
        <div class="brand-subtitle">Análise de clientes</div></div></div>
        <div class="app-status"><span>Base: churn.csv</span>
        <span><i class="status-dot{'' if connected else ' waiting'}"></i>{status}</span></div></div>''', unsafe_allow_html=True)
    introduction, workspace = st.columns([0.86, 1.14], gap="large")
    with introduction:
        st.markdown('<p class="intro-eyebrow">RELACIONAMENTOS QUE CONTINUAM</p>', unsafe_allow_html=True)
        st.title("Entenda a permanência dos seus clientes.")
        st.markdown('''<p class="intro-description">Uma consulta simples para conhecer a tendência de cada cliente.
            Encontre o perfil, veja a previsão e tenha mais contexto para sua próxima decisão.</p>''', unsafe_allow_html=True)
        st.markdown(f'''<div class="source-card"><div class="source-label">Sua carteira, em perspectiva</div>
            <div class="source-count">{count}</div><p class="source-description">clientes disponíveis para análise<br>
            na base que você já utiliza.</p><div class="source-foot"><span>Fonte <strong>churn.csv</strong></span>
            <span>Modelo <strong>já treinado</strong></span></div></div>''', unsafe_allow_html=True)
    with workspace:
        lookup(frame)
    st.markdown('''<div class="app-footer"><span>Previsões com o modelo treinado neste projeto.</span>
        <span>Churn estima cancelamento do serviço; não garante pagamentos futuros.</span></div>''', unsafe_allow_html=True)
    portfolio(frame)


def cli():
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve()),
        "--server.address", "127.0.0.1", *sys.argv[1:],
    ]))


if __name__ == "__main__":
    main()
