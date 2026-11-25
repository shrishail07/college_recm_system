from typing import Optional
import pandas as pd
from app.config import DATA_PATH


def _to_clean_int(val: object) -> Optional[int]:
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s in ("", "N/A", "NA", "None", "null"):
        return None
    return int(float(s))


def load_college_dataframe() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df.columns = [c.strip() for c in df.columns]

    int_cols = [
        "Total Regular Intake",
        "Government Quota Seats",
        "COMEDK Seats",
        "Management Seats",
        "SNQ Seats",
        "Government Fee (INR)",
        "Private Fee (INR)",
        "SNQ Fee (INR)",
    ]
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].apply(_to_clean_int)

    df["KCET Code"] = df["KCET Code"].astype(str).str.strip()
    df["Branch Code"] = df["Branch Code"].astype(str).str.strip()
    df["Branch Name"] = df["Branch Name"].astype(str).str.strip()
    df["District"] = df["District"].astype(str).str.strip()
    df["College Name"] = df["College Name"].astype(str).str.strip()
    df["program_id"] = df["KCET Code"] + "_" + df["Branch Code"]
    return df
