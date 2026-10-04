"""
Aegis Protocol — WELFake Dataset Adapter
========================================
Scientific loader and preprocessor for the WELFake dataset.
Strict isolation:
- No ground truth leakage into features or pipelines
- Content-level deduplication to prevent cross-partition leakage
- Empirical accounting of raw rows, clean rows, excluded rows, duplicates, and class balance
- Deterministic stratified train/validation/test splits with 0 content overlap
"""

import os
from typing import Dict, Any, Tuple
import pandas as pd
from sklearn.model_selection import train_test_split


DEFAULT_WELFAKE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "WELFake_Dataset.xlsx")
)


def load_welfake_dataset(
    filepath: str = DEFAULT_WELFAKE_PATH,
    deduplicate: bool = True,
    verbose: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Loads, cleans, audits, and content-deduplicates the local WELFake dataset.
    Returns:
        clean_df: Cleaned dataframe with non-null 'title' and valid 'label' (0=Real, 1=Fake)
        metadata: Auditable provenance metadata (counts, exclusions, distributions)
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"WELFake dataset not found at {filepath}")

    raw_df = pd.read_excel(filepath)
    raw_rows = len(raw_df)

    # Clean rows missing title or label
    df = raw_df.dropna(subset=["title", "label"]).copy()
    rows_after_dropna = len(df)

    # Cast and validate labels (only binary 0 or 1 permitted)
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    df = df.dropna(subset=["label"]).copy()
    df["label"] = df["label"].astype(int)
    df = df[df["label"].isin([0, 1])].copy()
    rows_valid_labels = len(df)

    # Content-level normalization for deduplication
    df["normalized_title"] = df["title"].astype(str).str.strip().str.lower()
    dup_count = int(df["normalized_title"].duplicated().sum())

    if deduplicate:
        df = df.drop_duplicates(subset=["normalized_title"]).copy().reset_index(drop=True)

    clean_rows = len(df)

    # Class distribution
    class_0_count = int((df["label"] == 0).sum())
    class_1_count = int((df["label"] == 1).sum())

    metadata: Dict[str, Any] = {
        "dataset_name": "WELFake (Word Embedding-enabled Lightweight Fake News)",
        "file_path": filepath,
        "file_size_bytes": os.path.getsize(filepath),
        "raw_row_count": raw_rows,
        "rows_after_dropna": rows_after_dropna,
        "rows_valid_labels": rows_valid_labels,
        "duplicate_titles_count": dup_count,
        "deduplicated": deduplicate,
        "clean_row_count": clean_rows,
        "excluded_invalid_rows": raw_rows - rows_valid_labels,
        "class_distribution": {
            "0_real": class_0_count,
            "1_fake": class_1_count,
            "class_0_percentage": round(class_0_count / clean_rows * 100, 2),
            "class_1_percentage": round(class_1_count / clean_rows * 100, 2),
        },
        "scientific_note": (
            "WELFake is an article/headline classification dataset. "
            "It measures NLP stance/authenticity classification on news headlines, "
            "not live multi-source web evidence retrieval."
        )
    }

    if verbose:
        print("=" * 70)
        print("WELFAKE DATASET AUDIT")
        print(f"File: {filepath}")
        print(f"Raw rows: {raw_rows} | Clean rows: {clean_rows} (Deduplicated: {dup_count})")
        print(f"Class 0 (Real): {class_0_count} ({metadata['class_distribution']['class_0_percentage']}%)")
        print(f"Class 1 (Fake): {class_1_count} ({metadata['class_distribution']['class_1_percentage']}%)")
        print("=" * 70)

    return df, metadata


def get_welfake_splits(
    df: pd.DataFrame,
    train_size: float = 0.70,
    val_size: float = 0.15,
    test_size: float = 0.15,
    seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Creates deterministic stratified train, validation, and test splits.
    Guarantees zero row and zero content overlap across partitions.
    """
    assert abs((train_size + val_size + test_size) - 1.0) < 1e-6, "Split ratios must sum to 1.0"

    # Step 1: Split train vs temp (val + test)
    temp_size = val_size + test_size
    train_df, temp_df = train_test_split(
        df,
        train_size=train_size,
        stratify=df["label"],
        random_state=seed
    )

    # Step 2: Split temp into val and test proportionally
    relative_val_size = val_size / temp_size
    val_df, test_df = train_test_split(
        temp_df,
        train_size=relative_val_size,
        stratify=temp_df["label"],
        random_state=seed
    )

    train_df = train_df.reset_index(drop=True)
    val_df = val_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)

    # Strict audit of zero content duplication across partitions
    train_titles = set(train_df["normalized_title"])
    val_titles = set(val_df["normalized_title"])
    test_titles = set(test_df["normalized_title"])

    assert len(train_titles & test_titles) == 0, "FATAL: Duplicate content between train and test splits!"
    assert len(train_titles & val_titles) == 0, "FATAL: Duplicate content between train and val splits!"
    assert len(val_titles & test_titles) == 0, "FATAL: Duplicate content between val and test splits!"

    return train_df, val_df, test_df


class WelfakeDataset:
    """Class wrapper for WELFake dataset loading, deduplication, and splitting."""

    def __init__(self, filepath: str = DEFAULT_WELFAKE_PATH, deduplicate: bool = True):
        self.filepath = filepath
        self.deduplicate = deduplicate
        self._df, self._metadata = load_welfake_dataset(filepath, deduplicate=deduplicate, verbose=False)

    def get_dataset_statistics(self) -> Dict[str, Any]:
        return {
            "filepath": self.filepath,
            "raw_rows": self._metadata["raw_row_count"],
            "clean_rows": self._metadata["clean_row_count"],
            "excluded_missing_or_invalid_rows": self._metadata["excluded_invalid_rows"],
            "duplicate_titles_removed": self._metadata["duplicate_titles_count"],
            "deduplicated": self.deduplicate,
            "class_distribution": {
                0: self._metadata["class_distribution"]["0_real"],
                1: self._metadata["class_distribution"]["1_fake"],
            },
            "task_scope_note": self._metadata["scientific_note"],
        }

    def get_splits(
        self,
        train_size: float = 0.70,
        val_size: float = 0.15,
        test_size: float = 0.15,
        seed: int = 42,
    ) -> Dict[str, pd.DataFrame]:
        train_df, val_df, test_df = get_welfake_splits(
            self._df,
            train_size=train_size,
            val_size=val_size,
            test_size=test_size,
            seed=seed,
        )
        return {
            "train": train_df,
            "val": val_df,
            "test": test_df,
        }
