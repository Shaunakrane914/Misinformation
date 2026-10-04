"""
Aegis Protocol — Evaluation Dataset Adapters
===========================================
Modular dataset adapters for WELFake, AVeriTeC, and the India Multilingual Track.
"""

from .welfake import load_welfake_dataset, get_welfake_splits
from .averitec import AVeriTeCAdapter
from .india_track import load_india_gold_track

__all__ = [
    "load_welfake_dataset",
    "get_welfake_splits",
    "AVeriTeCAdapter",
    "load_india_gold_track",
]
