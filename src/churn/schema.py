import pandera.pandas as pa


SIM_NAO = ["Yes", "No"]

SERVICO_INTERNET = [
    "Yes",
    "No",
    "No internet service",
]


ChurnSchema = pa.DataFrameSchema(
    {
        "customerID": pa.Column(
            str,
            nullable=False,
            unique=True,
        ),

        "gender": pa.Column(
            str,
            pa.Check.isin(["Male", "Female"]),
            nullable=False,
        ),

        "SeniorCitizen": pa.Column(
            int,
            pa.Check.isin([0, 1]),
            nullable=False,
        ),

        "Partner": pa.Column(
            str,
            pa.Check.isin(SIM_NAO),
            nullable=False,
        ),

        "Dependents": pa.Column(
            str,
            pa.Check.isin(SIM_NAO),
            nullable=False,
        ),

        "tenure": pa.Column(
            int,
            checks=[
                pa.Check.ge(0),
                pa.Check.le(72),
            ],
            nullable=False,
        ),

        "PhoneService": pa.Column(
            str,
            pa.Check.isin(SIM_NAO),
            nullable=False,
        ),

        "MultipleLines": pa.Column(
            str,
            pa.Check.isin([
                "Yes",
                "No",
                "No phone service",
            ]),
            nullable=False,
        ),

        "InternetService": pa.Column(
            str,
            pa.Check.isin([
                "DSL",
                "Fiber optic",
                "No",
            ]),
            nullable=False,
        ),

        "OnlineSecurity": pa.Column(
            str,
            pa.Check.isin(SERVICO_INTERNET),
            nullable=False,
        ),

        "OnlineBackup": pa.Column(
            str,
            pa.Check.isin(SERVICO_INTERNET),
            nullable=False,
        ),

        "DeviceProtection": pa.Column(
            str,
            pa.Check.isin(SERVICO_INTERNET),
            nullable=False,
        ),

        "TechSupport": pa.Column(
            str,
            pa.Check.isin(SERVICO_INTERNET),
            nullable=False,
        ),

        "StreamingTV": pa.Column(
            str,
            pa.Check.isin(SERVICO_INTERNET),
            nullable=False,
        ),

        "StreamingMovies": pa.Column(
            str,
            pa.Check.isin(SERVICO_INTERNET),
            nullable=False,
        ),

        "Contract": pa.Column(
            str,
            pa.Check.isin([
                "Month-to-month",
                "One year",
                "Two year",
            ]),
            nullable=False,
        ),

        "PaperlessBilling": pa.Column(
            str,
            pa.Check.isin(SIM_NAO),
            nullable=False,
        ),

        "PaymentMethod": pa.Column(
            str,
            pa.Check.isin([
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
            ]),
            nullable=False,
        ),

        "MonthlyCharges": pa.Column(
            float,
            checks=[
                pa.Check.ge(0),
                pa.Check.le(200),
            ],
            nullable=False,
            coerce=True,
        ),

        "TotalCharges": pa.Column(
            float,
            checks=[
                pa.Check.ge(0),
                pa.Check.le(10000),
            ],
            nullable=True,
            coerce=True,
        ),

        "Churn": pa.Column(
            str,
            pa.Check.isin(["Yes", "No"]),
            nullable=False,
        ),
    },

    checks=pa.Check(
        lambda df: len(df) > 0,
        error="dataset vazio",
    ),

    strict=True,
    unique_column_names=True,
    name="ChurnSchema",
)