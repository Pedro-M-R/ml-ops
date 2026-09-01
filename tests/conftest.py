import pandas as pd
import pytest


@pytest.fixture
def raw_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "customerID": ["a", "b", "c", "d"],
            "gender": ["Male", "Female", "Male", "Female"],
            "tenure": [1, 12, 24, 0],
            "MonthlyCharges": [29.9, 59.9, 89.9, 19.9],
            "TotalCharges": ["29.9", "718.8", " ", "0"],
            "Churn": ["No", "Yes", "No", "Yes"],
        }
    )
