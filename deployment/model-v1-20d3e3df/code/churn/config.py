from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHURN_", env_file=".env", protected_namespaces=()
    )

    data_path: Path = PROJECT_ROOT / "data/churn.csv"
    model_path: Path = PROJECT_ROOT / "models/model.pkl"

    target: str = "Churn"
    id_column: str = "customerID"

    test_size: float = 0.25
    n_estimators: int = 200
    random_state: int = 42
    positive_label: str = "Yes"


settings = Settings()
