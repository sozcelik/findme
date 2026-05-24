"""
AEO (Answer Engine Optimization) scorer.
Analyzes article markdown and returns a 0-100 score indicating how likely
the content is to be cited by AI models (ChatGPT, Perplexity, Claude, etc.).
"""

import re
from dataclasses import dataclass


@dataclass
class AEOBreakdown:
    question_headings: int      # H2/H3s phrased as questions
    has_lists: bool             # bullet/numbered lists present
    has_tables: bool            # markdown tables present
    has_faq: bool               # FAQ section present
    faq_count: int              # number of FAQ items
    has_numbers: bool           # specific stats/numbers present
    has_comparison: bool        # comparison/vs content
    summary_paragraph: bool     # short first paragraph (featured snippet ready)
    definition_present: bool    # direct "X is ..." definition in first 300 chars
    total_score: int


def score_content(markdown: str) -> AEOBreakdown:
    lines = markdown.splitlines()
    text = markdown.lower()

    # --- Question headings (25 pts) ---
    heading_pattern = re.compile(r"^#{1,3}\s+(.+)", re.MULTILINE)
    headings = heading_pattern.findall(markdown)
    question_words = ("what", "how", "why", "when", "which", "who", "does", "can",
                      "nedir", "nasıl", "neden", "ne zaman", "hangi", "kim", "mı", "mi")
    question_headings = sum(
        1 for h in headings
        if "?" in h or any(h.lower().startswith(w) for w in question_words)
    )

    # --- Lists (15 pts) ---
    has_lists = bool(re.search(r"^[\-\*\+]\s+.+", markdown, re.MULTILINE)) or \
                bool(re.search(r"^\d+\.\s+.+", markdown, re.MULTILINE))

    # --- Tables (10 pts) ---
    has_tables = bool(re.search(r"^\|.+\|", markdown, re.MULTILINE))

    # --- FAQ section (20 pts) ---
    has_faq = bool(re.search(r"#{1,3}\s*(faq|frequently asked|sık sorulan|sıkça)", text))
    faq_items = re.findall(r"#{1,3}\s+.+\?", markdown)
    faq_count = len(faq_items)

    # --- Specific numbers/data (10 pts) ---
    has_numbers = bool(re.search(r"\b\d+[\.,]?\d*\s*(%|x|times|ms|kb|mb|gb|\$|€|£|tl)\b", text)) or \
                  bool(re.search(r"\b\d{4}\b", text)) or \
                  bool(re.search(r"\b\d+\s*(million|billion|thousand|milyon|milyar)\b", text))

    # --- Comparison content (10 pts) ---
    has_comparison = bool(re.search(
        r"\b(vs\.?|versus|compared to|alternative|karşılaştır|farkı|fark)\b", text
    ))

    # --- Summary paragraph (5 pts) ---
    # First non-heading paragraph should be ≤ 3 sentences
    first_para = ""
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("!"):
            first_para = stripped
            break
    sentences = re.split(r"[.!?]+", first_para)
    summary_paragraph = 0 < len([s for s in sentences if s.strip()]) <= 3

    # --- Direct definition (5 pts) ---
    first_500 = markdown[:500].lower()
    definition_present = bool(re.search(
        r"\b(is a |is an |refers to|defined as|nedir[:\s]|şudur[:\s]|olarak tanımlanır)", first_500
    ))

    # --- Calculate total score ---
    score = 0
    score += min(question_headings * 8, 25)   # max 25
    score += 15 if has_lists else 0
    score += 10 if has_tables else 0
    score += 15 if has_faq else 0
    score += min(faq_count * 2, 5)            # bonus for more FAQ items, max 5
    score += 10 if has_numbers else 0
    score += 10 if has_comparison else 0
    score += 5 if summary_paragraph else 0
    score += 5 if definition_present else 0

    return AEOBreakdown(
        question_headings=question_headings,
        has_lists=has_lists,
        has_tables=has_tables,
        has_faq=has_faq,
        faq_count=faq_count,
        has_numbers=has_numbers,
        has_comparison=has_comparison,
        summary_paragraph=summary_paragraph,
        definition_present=definition_present,
        total_score=min(score, 100),
    )


def score_to_dict(breakdown: AEOBreakdown) -> dict:
    return {
        "aeo_score": breakdown.total_score,
        "breakdown": {
            "question_headings": breakdown.question_headings,
            "has_lists": breakdown.has_lists,
            "has_tables": breakdown.has_tables,
            "has_faq": breakdown.has_faq,
            "faq_count": breakdown.faq_count,
            "has_numbers": breakdown.has_numbers,
            "has_comparison": breakdown.has_comparison,
            "summary_paragraph": breakdown.summary_paragraph,
            "definition_present": breakdown.definition_present,
        },
        "suggestions": _suggestions(breakdown),
    }


def _suggestions(b: AEOBreakdown) -> list[str]:
    tips = []
    if b.question_headings < 3:
        tips.append("Rephrase H2/H3 headings as questions (e.g. 'What is X?' instead of 'About X')")
    if not b.has_faq:
        tips.append("Add a FAQ section with at least 5 questions")
    if not b.has_tables:
        tips.append("Add a comparison table — models frequently cite structured comparisons")
    if not b.has_numbers:
        tips.append("Include specific numbers, percentages, or statistics")
    if not b.definition_present:
        tips.append("Start with a direct definition: 'X is a ...' in the first paragraph")
    if not b.has_comparison:
        tips.append("Add a vs/alternatives section — high citation value for commercial queries")
    return tips
