import os
import logging
import random
from typing import List, Dict
import zipfile
import time
import pandas as pd

logger = logging.getLogger(__name__)

def _stream_sample_csv(csv_path: str, n: int) -> pd.DataFrame:
    chunksize = 10000
    reservoir: List[Dict] = []
    total_seen = 0
    scan_limit = int(os.getenv("DASHBOARD_SCAN_LIMIT", "20000"))
    
    try_encodings = ["utf-8", "latin-1"]
    for enc in try_encodings:
        try:
            for chunk in pd.read_csv(
                csv_path,
                usecols=["title", "label"],
                encoding=enc,
                engine="python",
                on_bad_lines="skip",
                encoding_errors="replace",
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
                    if total_seen >= scan_limit:
                        break
                if total_seen >= scan_limit:
                    break
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


def _stream_sample_zip(zip_path: str, n: int) -> pd.DataFrame:
    chunksize = 10000
    reservoir: List[Dict] = []
    total_seen = 0
    scan_limit = int(os.getenv("DASHBOARD_SCAN_LIMIT", "20000"))

    with zipfile.ZipFile(zip_path, 'r') as z:
        # Pick first CSV inside the zip
        inner_csv = next((name for name in z.namelist() if name.lower().endswith('.csv')), None)
        if not inner_csv:
            logger.error(f"[DashboardLoader] No CSV found in zip: {zip_path}")
            return pd.DataFrame(columns=["claim", "label"])
        logger.info(f"[DashboardLoader] Reading zipped CSV: {inner_csv}")
        try_encodings = ["utf-8", "latin-1"]
        for enc in try_encodings:
            try:
                with z.open(inner_csv) as f:
                    for chunk in pd.read_csv(
                        f,
                        usecols=["title", "label"],
                        encoding=enc,
                        engine="python",
                        on_bad_lines="skip",
                        encoding_errors="replace",
                        chunksize=chunksize,
                    ):
                        chunk = chunk.dropna(subset=["title"])  # noqa: PD002
                        chunk["label"] = pd.to_numeric(chunk["label"], errors="coerce").fillna(0).astype(int)
                        for _, row in chunk.iterrows():
                            total_seen += 1
                            item = {"claim": row["title"], "label": row["label"]}
                            if len(reservoir) < n:
                                reservoir.append(item)
                            else:
                                j = random.randint(0, total_seen - 1)
                                if j < n:
                                    reservoir[j] = item
                            if total_seen >= scan_limit:
                                break
                        if total_seen >= scan_limit:
                            break
                break
            except UnicodeDecodeError:
                logger.warning("[DashboardLoader] UTF-8 decode failed in zip, trying latin-1")
                continue

    if not reservoir:
        return pd.DataFrame(columns=["claim", "label"])
    df = pd.DataFrame(reservoir)
    df = df.drop_duplicates(subset=["claim"])  # noqa: PD002
    return df

def load_random_dashboard_claims(n: int = 15) -> List[Dict[str, str]]:
    try:
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        zip_path = os.path.join(data_dir, "WELFake_Dataset.zip")
        csv_path = os.path.join(data_dir, "WELFake_Dataset.csv")

        if os.path.exists(zip_path):
            logger.info(f"[DashboardLoader] Loading ZIP: {zip_path}")
            df = _stream_sample_zip(zip_path, max(n * 3, 50))
        else:
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


_CACHE_DATA: List[Dict[str, str]] = []
_CACHE_AT: float = 0.0

def get_dashboard_claims_cached(n: int = 15, ttl_seconds: int = 60) -> List[Dict[str, str]]:
    global _CACHE_DATA, _CACHE_AT
    now = time.time()
    if _CACHE_DATA and (now - _CACHE_AT) < ttl_seconds:
        logger.info(f"[DashboardLoader] Using cached dashboard claims ({len(_CACHE_DATA)})")
        # Return a random subset to keep perceived freshness
        if len(_CACHE_DATA) > n:
            return random.sample(_CACHE_DATA, n)
        return _CACHE_DATA[:]
    logger.info("[DashboardLoader] Cache miss; regenerating claims sample")
    data = load_random_dashboard_claims(n=n)
    _CACHE_DATA = data
    _CACHE_AT = now
    return data
