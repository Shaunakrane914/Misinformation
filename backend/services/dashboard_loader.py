import os
import logging
from typing import List, Dict
import pandas as pd

logger = logging.getLogger(__name__)

def _read_csv_safely(csv_path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(
            csv_path,
            usecols=["title", "label"],
            encoding="utf-8",
            engine="python",
            on_bad_lines="skip",
        )
    except UnicodeDecodeError:
        logger.warning("[DashboardLoader] UTF-8 decode failed, trying latin-1")
        return pd.read_csv(
            csv_path,
            usecols=["title", "label"],
            encoding="latin-1",
            engine="python",
            on_bad_lines="skip",
        )

def load_random_dashboard_claims(n: int = 15) -> List[Dict[str, str]]:
    try:
        csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "WELFake_Dataset.csv"))
        logger.info(f"[DashboardLoader] Loading CSV: {csv_path}")
        df = _read_csv_safely(csv_path)  # nosec
        logger.info(f"[DashboardLoader] Loaded rows: {len(df)}")
        df = df.dropna(subset=["title"]).drop_duplicates(subset=["title"])  # noqa: PD002
        df["label"] = pd.to_numeric(df["label"], errors="coerce").fillna(0).astype(int)
        df["label"] = df["label"].apply(lambda x: "True" if x == 1 else "False")
        if n <= 0:
            logger.info("[DashboardLoader] Requested sample size <= 0, returning empty list")
            return []
        sample_n = min(n, len(df))
        sampled = df.sample(n=sample_n, replace=False, random_state=None)
        logger.info(f"[DashboardLoader] Sampled {sample_n} claims")
        return [{"claim": row["title"], "label": row["label"]} for _, row in sampled.iterrows()]
    except Exception as e:
        logger.error(f"[DashboardLoader] Error loading claims: {str(e)}")
        raise
