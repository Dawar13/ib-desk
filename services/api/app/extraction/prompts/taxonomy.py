"""Soft section taxonomy.

A guide, not a cage. The discovery prompt includes these common section keys so
recurring concepts map to stable keys across runs rather than the model inventing
a different key each time for the same idea. The model may add new sections when
the document warrants, and must propose qualitative insight sections, not only
numeric ones. Nothing here assumes the document is about a company.
"""

from __future__ import annotations

TAXONOMY_VERSION = "1"

# key, label, and when to use it. Spans company, market, person, deal, and
# qualitative insight so the same concept maps to the same key each run.
SECTION_TAXONOMY: list[dict[str, str]] = [
    {
        "key": "overview",
        "label": "Overview",
        "use": "A concise summary of the subject and what the document is fundamentally about.",
    },
    {
        "key": "identity",
        "label": "Identity and basics",
        "use": "Founding year, headquarters, legal form, website, and similar identity facts.",
    },
    {
        "key": "products_services",
        "label": "Products and services",
        "use": "What the subject builds, sells, or offers.",
    },
    {
        "key": "business_model",
        "label": "Business model",
        "use": "How the subject makes money: pricing, channels, unit economics.",
    },
    {
        "key": "financials",
        "label": "Financials",
        "use": "Revenue, growth, margins, profitability, and reported figures by period.",
    },
    {
        "key": "traction_metrics",
        "label": "Traction and metrics",
        "use": "Operating metrics such as users, ARR, GMV, retention, by period where given.",
    },
    {
        "key": "investors_capital",
        "label": "Investors and capital",
        "use": "Investors, rounds, amounts raised, ownership, and capital structure.",
    },
    {
        "key": "valuation",
        "label": "Valuation",
        "use": "Valuations, multiples, and how they were derived.",
    },
    {"key": "market", "label": "Market", "use": "Market size, growth, segments, and dynamics."},
    {
        "key": "competition",
        "label": "Competition",
        "use": "Competitors and competitive positioning.",
    },
    {
        "key": "customers",
        "label": "Customers",
        "use": "Named customers, segments, concentration, and retention.",
    },
    {
        "key": "team_leadership",
        "label": "Team and leadership",
        "use": "Founders, executives, board, and key people.",
    },
    {
        "key": "deal",
        "label": "Deal",
        "use": "Transaction details: type, structure, price, terms, status, and parties.",
    },
    {
        "key": "comparables",
        "label": "Comparable transactions",
        "use": "Similar past deals used to inform valuation.",
    },
    {"key": "risks", "label": "Risks", "use": "Risks, dependencies, and concerns."},
    {
        "key": "catalysts",
        "label": "Catalysts and why now",
        "use": "Why the subject is timely: why a founder may sell, why a market is attractive.",
    },
    {
        "key": "buyers_acquirers",
        "label": "Potential buyers or acquirers",
        "use": "Likely strategic or financial acquirers and the rationale.",
    },
    {"key": "timeline", "label": "Timeline", "use": "Dated milestones and events."},
    {
        "key": "insight",
        "label": "Key insight",
        "use": "Qualitative insight and judgment that helps a banker, grounded in the text.",
    },
]


def taxonomy_text() -> str:
    """Render the taxonomy as a bulleted list for inclusion in the prompt."""
    return "\n".join(
        f"- {entry['key']}: {entry['label']}. {entry['use']}" for entry in SECTION_TAXONOMY
    )
