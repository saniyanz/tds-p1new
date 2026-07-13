"""Registry mapping operation names to their handler functions.

Handlers are plain callables; the dispatcher inspects their signature to bind
parameters extracted by the planner.
"""
from __future__ import annotations

from operations import (
    audio,
    clone_git,
    comments,
    contacts,
    credit_card,
    dates,
    docs,
    email,
    fetch_api,
    format_file,
    image,
    logs,
    markdown,
    scrape,
    sql_query,
    tickets,
)

OPERATION_REGISTRY: dict[str, object] = {
    "format_file": format_file.handle_format_file,
    "count_dates": dates.handle_count_dates,
    "sort_contacts": contacts.handle_sort_contacts,
    "extract_logs": logs.handle_extract_logs,
    "index_docs": docs.handle_index_docs,
    "extract_email": email.handle_extract_email,
    "extract_credit_card": credit_card.handle_extract_credit_card,
    "find_similar_comments": comments.handle_find_similar_comments,
    "query_tickets": tickets.handle_query_tickets,
    "fetch_api": fetch_api.handle_fetch_api,
    "clone_git": clone_git.handle_clone_git,
    "run_sql_query": sql_query.handle_run_sql_query,
    "scrape_website": scrape.handle_scrape_website,
    "resize_image": image.handle_resize_image,
    "transcribe_audio": audio.handle_transcribe_audio,
    "md_to_html": markdown.handle_md_to_html,
}

# Canonical list of supported operations (used by the planner prompt).
SUPPORTED_OPERATIONS = sorted(OPERATION_REGISTRY.keys())

__all__ = ["OPERATION_REGISTRY", "SUPPORTED_OPERATIONS"]
