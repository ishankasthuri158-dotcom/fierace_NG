"""Shared save/load helpers for model dicts.

Format is chosen by file extension: ``.pkl``/``.pickle`` uses pickle,
anything else (default) uses JSON.

Only unpickle files you trust/generated yourself -- pickle.load executes
arbitrary code embedded in the file.
"""
from __future__ import annotations

import json
import pickle

_PICKLE_EXTS = (".pkl", ".pickle")


def save_model(data: dict, path: str) -> None:
    if path.endswith(_PICKLE_EXTS):
        with open(path, "wb") as fh:
            pickle.dump(data, fh)
    else:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)


def load_model(path: str) -> dict:
    if path.endswith(_PICKLE_EXTS):
        with open(path, "rb") as fh:
            return pickle.load(fh)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
