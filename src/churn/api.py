"""API FastAPI para o pipeline de churn exportado pelo MLflow."""

from contextlib import asynccontextmanager
from typing import Annotated, Literal

import mlflow.pyfunc
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse, Response
from mlflow.exceptions import MlflowException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from churn.deploy import selected_path

MAX_BATCH_SIZE = 1000
NUMERIC_COLUMNS = ("SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges")
NonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Threshold = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Scalar = str | float | int | bool | None


class CustomerInput(BaseModel):
    """Entradas brutas; categorias novas são tratadas pelo pipeline treinado."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    customerID: str | None = None
    gender: str
    SeniorCitizen: Literal[0, 1] | None
    Partner: str
    Dependents: str
    tenure: NonNegative | None
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: NonNegative | None
    TotalCharges: NonNegative | None


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customers: list[CustomerInput] = Field(min_length=1, max_length=MAX_BATCH_SIZE)
    threshold: Threshold = 0.5


class CustomerPrediction(BaseModel):
    customerID: str | None = None
    churn_probability: Threshold
    churn_prediction: Literal[0, 1]


class PredictionResponse(BaseModel):
    predictions: list[CustomerPrediction]
    threshold: Threshold


class DataFrameSplit(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    columns: list[str] = Field(min_length=1)
    data: list[list[Scalar]] = Field(min_length=1, max_length=MAX_BATCH_SIZE)
    index: list[Scalar] | None = None

    @model_validator(mode="after")
    def validate_dimensions(self):
        if len(set(self.columns)) != len(self.columns):
            raise ValueError("As colunas não podem se repetir.")
        if any(len(row) != len(self.columns) for row in self.data):
            raise ValueError("Cada linha deve ter o mesmo tamanho de columns.")
        if self.index is not None and len(self.index) != len(self.data):
            raise ValueError("index e data devem ter o mesmo número de linhas.")
        return self


class InvocationsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    dataframe_split: DataFrameSplit | None = None
    dataframe_records: list[dict[str, Scalar]] | None = Field(
        default=None, min_length=1, max_length=MAX_BATCH_SIZE,
    )

    @model_validator(mode="after")
    def validate_format(self):
        if (self.dataframe_split is None) == (self.dataframe_records is None):
            raise ValueError("Informe exatamente um de dataframe_split ou dataframe_records.")
        if self.dataframe_records is not None:
            columns = self.dataframe_records[0].keys()
            if not columns or any(row.keys() != columns for row in self.dataframe_records):
                raise ValueError("Todos os registros devem informar as mesmas colunas.")
        return self

    def to_frame(self) -> pd.DataFrame:
        if self.dataframe_split is not None:
            return pd.DataFrame(**self.dataframe_split.model_dump(exclude_none=True))
        return pd.DataFrame(self.dataframe_records)


class InvocationsResponse(BaseModel):
    predictions: list[tuple[Threshold, Threshold]]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


def _probabilities(model, frame: pd.DataFrame) -> np.ndarray:
    # A assinatura MLflow usa double; inteiros JSON também precisam virar float.
    try:
        for column in NUMERIC_COLUMNS:
            if column in frame:
                frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
                if np.isinf(frame[column]).any():
                    raise ValueError("Valores numéricos devem ser finitos ou null.")
        result = np.asarray(model.predict(frame), dtype=float)
    except (MlflowException, ValueError, TypeError, OverflowError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Entrada incompatível com o modelo. Confira as colunas e os tipos dos valores.",
        ) from exc
    if (
        result.shape != (len(frame), 2)
        or not np.isfinite(result).all()
        or (result < 0).any()
        or (result > 1).any()
        or not np.allclose(result.sum(axis=1), 1)
    ):
        raise HTTPException(status_code=500, detail="O modelo não retornou duas probabilidades válidas por cliente.")
    return result


def create_app(model_uri: str | None = None) -> FastAPI:
    """Cria a aplicação sem carregar o modelo durante o import do módulo."""

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        uri = model_uri or selected_path()
        if uri.startswith("models:"):
            from churn.tracking import configure_tracking

            configure_tracking()
        application.state.model = mlflow.pyfunc.load_model(uri)
        try:
            yield
        finally:
            del application.state.model

    application = FastAPI(
        title="API de previsão de churn",
        description="Inferência com o pipeline selecionado no MLflow. Lotes de até 1.000 clientes.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Não ecoar dados de clientes nem valores NaN/Infinity no JSON de erro.
        errors = [
            {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        status = 400 if request.url.path == "/invocations" else 422
        return JSONResponse(status_code=status, content={"detail": errors})

    @application.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    @application.get("/favicon.ico", include_in_schema=False, status_code=204)
    def favicon():
        return Response(status_code=204)

    @application.get("/health", response_model=HealthResponse, tags=["Saúde"])
    @application.get("/ping", response_model=HealthResponse, tags=["Saúde"])
    def health(request: Request):
        """Confirma que a aplicação iniciou e carregou o modelo."""
        if getattr(request.app.state, "model", None) is None:
            raise HTTPException(status_code=503, detail="Modelo indisponível.")
        return HealthResponse()

    @application.post(
        "/predict", response_model=PredictionResponse, response_model_exclude_none=True,
        tags=["Previsões"],
        responses={400: {"description": "Entrada incompatível com o modelo."},
                   500: {"description": "Probabilidades inválidas retornadas pelo modelo."}},
    )
    def predict(payload: PredictionRequest, request: Request):
        """Retorna probabilidade e classe de churn no limiar informado (padrão 0,5)."""
        frame = pd.DataFrame([
            customer.model_dump(exclude={"customerID"}) for customer in payload.customers
        ])
        probabilities = _probabilities(request.app.state.model, frame)
        return PredictionResponse(
            predictions=[
                CustomerPrediction(
                    customerID=customer.customerID,
                    churn_probability=float(probability),
                    churn_prediction=int(probability >= payload.threshold),
                )
                for customer, probability in zip(payload.customers, probabilities[:, 1])
            ],
            threshold=payload.threshold,
        )

    @application.post(
        "/invocations", response_model=InvocationsResponse, tags=["Previsões"],
        responses={400: {"description": "JSON, formato ou dados incompatíveis com o modelo."},
                   500: {"description": "Probabilidades inválidas retornadas pelo modelo."}},
    )
    def invocations(payload: InvocationsRequest, request: Request):
        """Compatibilidade MLflow: retorna [P(não churn), P(churn)] por linha."""
        try:
            frame = payload.to_frame()
        except (ValueError, TypeError, OverflowError) as exc:
            raise HTTPException(status_code=400, detail="Não foi possível construir a tabela de entrada.") from exc
        probabilities = _probabilities(request.app.state.model, frame)
        return {"predictions": probabilities.tolist()}

    def openapi():
        if application.openapi_schema is None:
            schema = get_openapi(
                title=application.title, version=application.version,
                description=application.description, routes=application.routes,
            )
            # A rota legada usa 400 para erros de validação em vez do padrão 422.
            schema["paths"]["/invocations"]["post"]["responses"].pop("422", None)
            application.openapi_schema = schema
        return application.openapi_schema

    application.openapi = openapi
    return application


app = create_app()
