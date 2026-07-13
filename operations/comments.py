"""A9: find the most similar pair of comments using embeddings + cosine."""
from __future__ import annotations

import numpy as np
from agent import llm
from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def handle_find_similar_comments() -> str:
    input_path = validate_path("comments.txt", settings.data_dir)
    output_path = validate_path("comments-similar.txt", settings.data_dir)
    comments = [
        line.strip()
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(comments) < 2:
        raise ValueError("Not enough comments to find a similar pair.")

    embeddings = {c: np.array(llm.get_embedding(c)) for c in comments}
    max_sim = -1.0
    best = ("", "")
    for i in range(len(comments)):
        for j in range(i + 1, len(comments)):
            sim = _cosine(embeddings[comments[i]], embeddings[comments[j]])
            if sim > max_sim:
                max_sim, best = sim, (comments[i], comments[j])

    output_path.write_text(f"{best[0]}\n{best[1]}\n", encoding="utf-8")
    return "Operation 'find_similar_comments' completed: similar comments found."
