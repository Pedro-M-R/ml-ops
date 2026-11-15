"""Cliente HTTP do painel; a inferência continua exclusivamente na FastAPI."""

import math
import os
from pathlib import Path

import httpx
import pandas as pd

BATCH_SIZE = 1000
MAX_CSV_ROWS = 50_000
NUMERIC_COLUMNS = ("SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges")
EXAMPLE_CUSTOMER = {
    "gender": "Female", "SeniorCitizen": 0, "Partner": "No", "Dependents": "No",
    "tenure": 12, "PhoneService": "Yes", "MultipleLines": "No",
    "InternetService": "Fiber optic", "OnlineSecurity": "No", "OnlineBackup": "No",
    "DeviceProtection": "No", "TechSupport": "No", "StreamingTV": "Yes",
    "StreamingMovies": "Yes", "Contract": "Month-to-month", "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check", "MonthlyCharges": 89.9, "TotalCharges": 1078.8,
}


class DashboardError(Exception):
    """Erro apropriado para exibição na interface, sem dados dos clientes."""


def uses_api_customers():
    return (os.environ.get("CHURN_CUSTOMER_SOURCE") or "api") == "api"


def load_customer_base():
    """Obtém a carteira da FastAPI; o CSV exige seleção explícita do modo legado."""
    if uses_api_customers():
        return _load_api_customers()
    root = Path(__file__).resolve().parents[2]
    configured = os.environ.get("CHURN_DATA_PATH")
    path = Path(configured) if configured else root / "data/churn.csv"
    if not configured and not path.is_file():
        # A base original continua versionada pelo DVC; a cópia acompanha o site.
        path = root / "frontend/data/churn.csv"
    if not path.is_file():
        raise DashboardError("Base não encontrada. O arquivo churn.csv precisa acompanhar esta instalação.")
    try:
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", nrows=MAX_CSV_ROWS + 1)
        customers_from_frame(frame)
    except (OSError, ValueError, UnicodeError) as exc:
        raise DashboardError("Não foi possível ler a base de clientes. Confira o arquivo CSV configurado.") from exc
    return frame


def _load_api_customers():
    """A tela recebe os registros pela API e nunca as credenciais do banco."""
    rows = []
    try:
        # A API no plano Free pode levar cerca de um minuto para retomar.
        with httpx.Client(base_url=api_url(), timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            while True:
                response = client.get("/customers", params={"limit": BATCH_SIZE, "offset": len(rows)})
                response.raise_for_status()
                page = response.json()
                batch = page["customers"]
                total = page["total"]
                if not isinstance(batch, list) or not isinstance(total, int) or not 1 <= total <= MAX_CSV_ROWS:
                    raise ValueError("Base fora do limite")
                if not batch or len(batch) > BATCH_SIZE or len(rows) + len(batch) > total:
                    raise ValueError("Página inválida")
                rows.extend(batch)
                if len(rows) == total:
                    break
        frame = pd.DataFrame(rows)
        customers_from_frame(frame)
        if frame.customerID.isna().any() or frame.customerID.str.strip().eq("").any() or frame.customerID.duplicated().any():
            raise ValueError("Identificadores inválidos")
        return frame
    except httpx.TimeoutException as exc:
        raise DashboardError(
            "A FastAPI ainda não respondeu. No primeiro acesso ela pode estar iniciando; aguarde e recarregue a página."
        ) from exc
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise DashboardError("Não foi possível consultar os clientes pela FastAPI. Confira o serviço configurado.") from exc


def customer_from_id(frame: pd.DataFrame, customer_id: str):
    """Localiza o registro existente; nunca inventa dados para um ID desconhecido."""
    code = customer_id.strip().casefold()
    if not code:
        raise DashboardError("Informe o código do cliente para consultar.")
    if "customerID" not in frame:
        raise DashboardError("A base churn.csv precisa da coluna customerID para localizar os clientes.")
    matches = frame.loc[frame.customerID.astype("string").str.strip().str.casefold().eq(code).fillna(False)]
    if matches.empty:
        source = "na base fornecida pela FastAPI" if uses_api_customers() else "no churn.csv"
        raise DashboardError(f"Cliente não encontrado {source}. Confira o código ou experimente um dos exemplos abaixo.")
    if len(matches) != 1:
        raise DashboardError("Há mais de um registro para esse código no churn.csv. Confira os identificadores da base.")
    return customers_from_frame(matches)[0]


def api_url():
    return os.environ.get("CHURN_API_URL", "http://127.0.0.1:8000").rstrip("/")


def check_health():
    try:
        path = "/ready" if uses_api_customers() else "/health"
        response = httpx.get(f"{api_url()}{path}", timeout=10.0)
        response.raise_for_status()
        return response.json().get("status") == "ok"
    except (httpx.HTTPError, ValueError, AttributeError):
        return False


def customers_from_frame(frame: pd.DataFrame):
    """Valida o CSV e preserva IDs textuais e números ausentes como null."""
    if not 1 <= len(frame) <= MAX_CSV_ROWS:
        raise DashboardError(f"Envie de 1 a {MAX_CSV_ROWS:,} clientes por arquivo.")
    required = set(EXAMPLE_CUSTOMER)
    missing = required - set(frame.columns)
    extra = set(frame.columns) - required - {"customerID", "Churn"}
    if missing:
        raise DashboardError("Colunas obrigatórias ausentes: " + ", ".join(sorted(missing)))
    if extra:
        raise DashboardError("Colunas desconhecidas: " + ", ".join(sorted(extra)))
    data = frame.drop(columns=["Churn"], errors="ignore").copy()
    for column in data:
        text = data[column].astype("string").str.strip()
        blank = data[column].isna() | text.eq("").fillna(True)
        if column in NUMERIC_COLUMNS:
            number = pd.to_numeric(text.mask(blank), errors="coerce")
            invalid = (~blank & number.isna()) | number.map(
                lambda value: False if pd.isna(value) else not math.isfinite(value) or value < 0
            )
            if column == "SeniorCitizen":
                invalid |= ~blank & ~number.isin([0, 1])
            if invalid.any():
                raise DashboardError(f"Confira os valores numéricos de {column}; use ponto decimal e valores não negativos.")
            data[column] = number.astype(object).where(~blank, None)
        elif column == "customerID":
            data[column] = text.astype(object).where(~blank, None)
        else:
            if blank.any():
                raise DashboardError(f"Preencha os valores de texto da coluna {column}.")
            data[column] = text
    return data.to_dict(orient="records")


def predict_customers(customers: list[dict], threshold: float):
    if not customers:
        raise DashboardError("Informe pelo menos um cliente.")
    predictions = []
    try:
        # A instância gratuita pode estar retomando após um período sem tráfego.
        with httpx.Client(base_url=api_url(), timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            for start in range(0, len(customers), BATCH_SIZE):
                batch = customers[start:start + BATCH_SIZE]
                response = client.post("/predict", json={"customers": batch, "threshold": threshold})
                if response.status_code in (400, 422):
                    raise DashboardError(
                        f"A API recusou o lote iniciado no cliente {start + 1}. Confira as colunas e os valores."
                    )
                response.raise_for_status()
                body = response.json()
                rows = body["predictions"]
                if len(rows) != len(batch) or body["threshold"] != threshold:
                    raise ValueError("Resposta incompatível com o lote")
                for row in rows:
                    probability = row["churn_probability"]
                    if (
                        not isinstance(probability, (int, float))
                        or not math.isfinite(probability) or not 0 <= probability <= 1
                        or row["churn_prediction"] != int(probability >= threshold)
                    ):
                        raise ValueError("Previsão inválida")
                predictions.extend(rows)
    except httpx.TimeoutException as exc:
        raise DashboardError("A API demorou para responder. Tente novamente.") from exc
    except httpx.HTTPError as exc:
        raise DashboardError("Não foi possível consultar a API. Confira se o serviço está em execução.") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise DashboardError("A API retornou uma resposta inesperada.") from exc
    result = pd.DataFrame(predictions)
    # Preserva os registros recebidos, inclusive a ausência de IDs opcionais.
    # Em CSVs grandes, une somente a lista dos lotes no mesmo contrato /predict.
    result.attrs["api_response"] = {"predictions": predictions, "threshold": body["threshold"]}
    return result
