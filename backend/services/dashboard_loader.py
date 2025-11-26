import os
import logging
import random
from typing import List, Dict
import pandas as pd

logger = logging.getLogger(__name__)

def _stream_sample_csv(csv_path: str, n: int) -> pd.DataFrame:
    chunksize = 10000
    reservoir: List[Dict] = []
    total_seen = 0

    try_encodings = ["utf-8", "latin-1"]
    for enc in try_encodings:
        try:
            for chunk in pd.read_csv(
                csv_path,
                usecols=["title", "label"],
                encoding=enc,
                engine="python",
                on_bad_lines="skip",
                chunksize=chunksize,
            ):
                chunk = chunk.dropna(subset=["title"])  # noqa: PD002
                # Normalize label early and coerce to int
                chunk["label"] = pd.to_numeric(chunk["label"], errors="coerce").fillna(0).astype(int)

                # Reservoir sampling
                for _, row in chunk.iterrows():
                    total_seen += 1
                    item = {"claim": row["title"], "label": row["label"]}
                    if len(reservoir) < n:
                        reservoir.append(item)
                    else:
                        j = random.randint(0, total_seen - 1)
                        if j < n:
                            reservoir[j] = item
            break
        except UnicodeDecodeError:
            logger.warning("[DashboardLoader] UTF-8 decode failed, trying latin-1")
            continue

    if not reservoir:
        return pd.DataFrame(columns=["claim", "label"])

    # Deduplicate by claim
    df = pd.DataFrame(reservoir)
    df = df.drop_duplicates(subset=["claim"])  # noqa: PD002
    return df

def load_random_dashboard_claims(n: int = 15) -> List[Dict[str, str]]:
    try:
        csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "WELFake_Dataset.csv"))
        logger.info(f"[DashboardLoader] Loading CSV: {csv_path}")
        df = _stream_sample_csv(csv_path, max(n * 3, 50))  # oversample then reduce
        logger.info(f"[DashboardLoader] Stream-sampled rows: {len(df)}")
        df["label"] = df["label"].apply(lambda x: "True" if int(x) == 1 else "False")
        if n <= 0:
            logger.info("[DashboardLoader] Requested sample size <= 0, returning empty list")
            return []
        sample_n = min(n, len(df))
        sampled = df.sample(n=sample_n, replace=False, random_state=None)
        logger.info(f"[DashboardLoader] Sampled {sample_n} claims")
        return [{"claim": row["claim"], "label": row["label"]} for _, row in sampled.iterrows()]
    except Exception as e:
        logger.error(f"[DashboardLoader] Error loading claims: {str(e)}")
        raise
