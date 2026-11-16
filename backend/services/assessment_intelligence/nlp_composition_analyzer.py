"""Offline NLP Composition, Grammar Mechanics & Local TF-IDF Coherence Analyzer.

Uses pure Python (no external LLM calls or C-extension ML dependencies):
- Local TF-IDF cosine similarity (word unigrams/bigrams + character 3-gram blend)
  between candidate writing, prompt topics, and optional rubric/reference answers.
- Adjacent sentence semantic continuity (sentence-level TF-IDF coherence).
- Lexical diversity (Type-Token Ratio), Automated Readability Index (ARI),
  discourse connective density, and syntactic/mechanical grammar checks.
- Also classifies single-bucket English Grammar MCQ sessions into balanced
  syntactic dimensions so every grammar assessment yields rich spider charts.
"""

from collections import Counter, defaultdict
import math
import re
from typing import Any

from services.assessment_intelligence.config import (
    format_dimension_label,
    resolve_percentile_band,
)


STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "he", "in", "is", "it", "its", "of", "on", "or", "she",
    "that", "the", "their", "there", "these", "they", "this", "to", "was",
    "were", "will", "with", "you", "your",
})

DISCOURSE_CONNECTIVES = frozenset({
    "however", "therefore", "moreover", "furthermore", "additionally",
    "consequently", "meanwhile", "nevertheless", "although", "because",
    "since", "while", "firstly", "secondly", "finally", "overall",
    "specifically", "instead", "similarly", "accordingly", "thus",
})

GRAMMAR_TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("subject_verb_agreement", ("agreement", "neither", "either", "committee", "each of", "plural", "team", "subject-verb")),
    ("tenses_and_aspects", ("tense", "past tense", "next week", "years", "had", "will have", "wrote", "continuous", "perfect")),
    ("articles_prepositions", ("article", "preposition", "honest", "good at", "between you", "a ", "an ", "the ")),
    ("voice_speech_connectors", ("passive voice", "reported speech", "conjunction", "question tag", "said", "if i")),
    ("vocabulary_usage", ("spelled", "punctuation", "affect", "effect", "comparative", "vocabulary", "synonym", "antonym", "idiom")),
    ("sentence_syntax", ("grammatically correct", "correct sentence", "fewer", "less", "clause", "modifier")),
]


def _tokenize_words(text: str, drop_stopwords: bool = True) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]*", (text or "").lower())
    if drop_stopwords:
        return [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    return tokens


def _word_ngrams(tokens: list[str]) -> list[str]:
    grams = list(tokens)
    if len(tokens) >= 2:
        grams.extend(f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1))
    return grams


def _char_trigrams(text: str) -> Counter[str]:
    cleaned = re.sub(r"\s+", " ", (text or "").lower().strip())
    if len(cleaned) < 3:
        return Counter([cleaned]) if cleaned else Counter()
    return Counter(cleaned[i:i + 3] for i in range(len(cleaned) - 2))


def _cosine_sim(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    common = set(vec_a.keys()) & set(vec_b.keys())
    dot = sum(vec_a[k] * vec_b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def tfidf_cosine_similarity(text_a: str, text_b: str, corpus_docs: list[str] | None = None) -> float:
    """Compute local TF-IDF word-ngram + character-trigram blended cosine similarity (0..1)."""
    docs = [text_a or "", text_b or ""]
    if corpus_docs:
        docs.extend(d for d in corpus_docs if d)

    tokenized_docs = [_word_ngrams(_tokenize_words(d)) for d in docs]
    n_docs = len(tokenized_docs)
    df: Counter[str] = Counter()
    for doc_tokens in tokenized_docs:
        df.update(set(doc_tokens))

    def build_tfidf(tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        tf = Counter(tokens)
        total = len(tokens)
        vec: dict[str, float] = {}
        for term, cnt in tf.items():
            idf = math.log((1.0 + n_docs) / (1.0 + df.get(term, 0))) + 1.0
            vec[term] = (cnt / total) * idf
        return vec

    vec_a = build_tfidf(tokenized_docs[0])
    vec_b = build_tfidf(tokenized_docs[1])
    word_sim = _cosine_sim(vec_a, vec_b)

    char_a = {k: float(v) for k, v in _char_trigrams(text_a).items()}
    char_b = {k: float(v) for k, v in _char_trigrams(text_b).items()}
    char_sim = _cosine_sim(char_a, char_b)

    return round(0.70 * word_sim + 0.30 * char_sim, 4)


def _split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", (text or "").strip()) if s.strip()]
    return parts if parts else ([text.strip()] if (text or "").strip() else [])


def _check_grammar_mechanics(text: str, sentences: list[str], all_words: list[str]) -> dict[str, Any]:
    issues: list[str] = []
    deductions = 0.0

    # Duplicate consecutive words ("the the")
    dup_matches = re.findall(r"\b([a-zA-Z]+)\s+\1\b", text, flags=re.IGNORECASE)
    if dup_matches:
        issues.append(f"Repeated consecutive word detected ({dup_matches[0]}).")
        deductions += min(20.0, len(dup_matches) * 8.0)

    # Capitalization at sentence starts
    lowercase_starts = sum(1 for s in sentences if s and s[0].islower())
    if lowercase_starts > 0:
        issues.append(f"{lowercase_starts} sentence(s) do not start with a capital letter.")
        deductions += min(18.0, lowercase_starts * 6.0)

    # Terminal punctuation on final/multiple sentences
    missing_end_punct = sum(1 for s in sentences if len(s.split()) >= 4 and s[-1] not in ".!?")
    if missing_end_punct > 0:
        issues.append(f"{missing_end_punct} sentence(s) lack terminal punctuation.")
        deductions += min(15.0, missing_end_punct * 5.0)

    # Basic article heuristic ("a apple", excluding common 'u'/'eu' sounds like 'user', 'unit')
    bad_a = re.findall(r"\ba\s+(?!(?:user|unit|unique|uniform|university|european|one)\b)[aeiou][a-z]+\b", text, flags=re.IGNORECASE)
    if bad_a:
        issues.append("Possible indefinite article mismatch ('a' before vowel sound).")
        deductions += min(12.0, len(bad_a) * 6.0)

    # Excessive sentence run-on check (> 42 words without break)
    run_ons = [s for s in sentences if len(_tokenize_words(s, drop_stopwords=False)) > 42]
    if run_ons:
        issues.append(f"{len(run_ons)} overly long sentence(s) (>42 words) may hinder clarity.")
        deductions += min(15.0, len(run_ons) * 7.0)

    if len(all_words) < 12:
        issues.append("Response is too brief for complete syntactic validation.")
        deductions += 25.0

    score = round(max(0.0, min(100.0, 100.0 - deductions)), 2)
    return {"mechanics_score": score, "issues": issues}


def analyze_composition_response(question: dict[str, Any], response_text: str) -> dict[str, Any]:
    """Grade an open-ended composition / essay / short-answer response offline."""
    text = (response_text or "").strip()
    if not text:
        return {
            "normalized_score": 0.0,
            "word_count": 0,
            "sentence_count": 0,
            "topic_relevance": 0.0,
            "coherence_cohesion": 0.0,
            "grammar_mechanics": 0.0,
            "lexical_richness": 0.0,
            "readability_clarity": 0.0,
            "issues": ["No written response submitted."],
        }

    prompt_text = str(question.get("question_text") or "")
    sk = question.get("scoring_key") or {}
    rubric_keywords = sk.get("keywords") or sk.get("rubric_keywords") or []
    reference_answer = str(sk.get("reference_answer") or sk.get("exemplar") or "")

    reference_blob = " ".join(
        part for part in [prompt_text, reference_answer, " ".join(str(k) for k in rubric_keywords)] if part
    )
    sentences = _split_sentences(text)
    all_words = _tokenize_words(text, drop_stopwords=False)
    content_words = _tokenize_words(text, drop_stopwords=True)
    word_count = len(all_words)

    # 1. Local TF-IDF + char-ngram similarity to prompt & rubric
    prompt_sim = tfidf_cosine_similarity(text, reference_blob, corpus_docs=sentences)
    keyword_hits = 0
    if rubric_keywords:
        lower_text = text.lower()
        keyword_hits = sum(1 for kw in rubric_keywords if str(kw).lower() in lower_text)
        kw_coverage = keyword_hits / len(rubric_keywords)
        relevance_score = round(min(100.0, (0.60 * min(1.0, prompt_sim * 1.9) + 0.40 * kw_coverage) * 100.0), 2)
    else:
        relevance_score = round(min(100.0, min(1.0, prompt_sim * 2.15) * 100.0), 2)

    # 2. Adjacent sentence cosine coherence + discourse markers
    if len(sentences) >= 2:
        adj_sims = [
            tfidf_cosine_similarity(sentences[i], sentences[i + 1], corpus_docs=sentences)
            for i in range(len(sentences) - 1)
        ]
        mean_adj = sum(adj_sims) / len(adj_sims)
        discourse_hits = sum(1 for w in all_words if w in DISCOURSE_CONNECTIVES)
        discourse_bonus = min(0.30, discourse_hits * 0.08)
        coherence_score = round(min(100.0, (min(1.0, mean_adj * 1.85) * 0.70 + discourse_bonus) * 100.0), 2)
    else:
        coherence_score = round(min(65.0, relevance_score * 0.65), 2)

    # 3. Mechanics & Grammar checks
    mechanics = _check_grammar_mechanics(text, sentences, all_words)

    # 4. Lexical Richness (Root TTR to avoid unfair short-text bias)
    unique_content = len(set(content_words))
    if content_words:
        rttr = unique_content / math.sqrt(len(content_words))
        lexical_score = round(min(100.0, max(15.0, (rttr / 5.5) * 100.0)), 2)
    else:
        lexical_score = 0.0

    # 5. Readability & Structure clarity (Automated Readability Index target band ~ 8..14)
    chars = sum(len(w) for w in all_words)
    sent_cnt = max(1, len(sentences))
    w_cnt = max(1, word_count)
    ari = 4.71 * (chars / w_cnt) + 0.5 * (w_cnt / sent_cnt) - 21.43
    min_target_words = int(sk.get("min_words") or 25)
    length_factor = min(1.0, word_count / max(15, min_target_words))
    clarity_base = 88.0 if 6.0 <= ari <= 15.0 else (72.0 if 3.5 <= ari < 6.0 or 15.0 < ari <= 18.5 else 55.0)
    readability_score = round(clarity_base * length_factor, 2)

    composite = round(
        0.28 * relevance_score
        + 0.24 * coherence_score
        + 0.24 * mechanics["mechanics_score"]
        + 0.12 * lexical_score
        + 0.12 * readability_score,
        2,
    )

    return {
        "normalized_score": composite,
        "word_count": word_count,
        "sentence_count": len(sentences),
        "topic_relevance": relevance_score,
        "coherence_cohesion": coherence_score,
        "grammar_mechanics": mechanics["mechanics_score"],
        "lexical_richness": lexical_score,
        "readability_clarity": readability_score,
        "ari_grade": round(max(1.0, ari), 2),
        "keyword_hits": keyword_hits,
        "issues": mechanics["issues"],
    }


def _classify_grammar_question(question: dict[str, Any]) -> str:
    raw_cat = str(question.get("category") or "").strip().lower()
    if raw_cat and raw_cat not in {"english_grammar", "general"}:
        return raw_cat
    text = f"{question.get('question_text', '')} {question.get('instructions', '')}".lower()
    for dim_key, keywords in GRAMMAR_TOPIC_RULES:
        if any(kw in text for kw in keywords):
            return dim_key
    return "sentence_syntax"


def analyze_nlp_session(
    questions: list[dict[str, Any]],
    question_results: list[dict[str, Any]],
    category_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyze grammar MCQ sessions and/or open-text composition responses."""
    q_by_id = {q["id"]: q for q in questions}
    composition_evaluations: list[dict[str, Any]] = []
    sub_buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"score": 0.0, "max_score": 0.0, "count": 0.0})

    for qr in question_results:
        q = q_by_id.get(qr["question_id"], {})
        sub_detail = qr.get("sub_evaluation") or {}
        if qr.get("question_type") in {"short_answer", "essay", "composition"}:
            if not sub_detail and qr.get("answer"):
                sub_detail = analyze_composition_response(q, str(qr["answer"]))
            if sub_detail:
                composition_evaluations.append({
                    "question_id": qr["question_id"],
                    **sub_detail,
                })

        dim_key = _classify_grammar_question(q)
        sub_buckets[dim_key]["score"] += max(0.0, float(qr.get("points_awarded", 0.0) or 0.0))
        sub_buckets[dim_key]["max_score"] += max(0.0, float(qr.get("max_score", 1.0) or 1.0))
        sub_buckets[dim_key]["count"] += 1

    dimensions: list[dict[str, Any]] = []
    if composition_evaluations:
        avg = lambda field: round(sum(float(e.get(field, 0.0)) for e in composition_evaluations) / len(composition_evaluations), 2)
        for dim_key, field_name in [
            ("topic_relevance", "topic_relevance"),
            ("coherence_cohesion", "coherence_cohesion"),
            ("grammar_mechanics", "grammar_mechanics"),
            ("lexical_richness", "lexical_richness"),
            ("readability_clarity", "readability_clarity"),
        ]:
            val = avg(field_name)
            dimensions.append({
                "dimension_key": dim_key,
                "dimension_label": format_dimension_label(dim_key),
                "raw_score": val,
                "max_score": 100.0,
                "normalized_score": val,
                "percentile_band": resolve_percentile_band(val),
                "evidence": {"evaluated_essays": len(composition_evaluations)},
            })
    elif len(category_scores) >= 3:
        for cs in category_scores:
            norm = float(cs.get("weighted_percentage", cs["percentage"]))
            dimensions.append({
                "dimension_key": cs["category"],
                "dimension_label": format_dimension_label(cs["category"]),
                "raw_score": float(cs["score"]),
                "max_score": float(cs["max_score"]),
                "normalized_score": round(norm, 2),
                "percentile_band": resolve_percentile_band(norm),
                "evidence": {"question_count": cs.get("question_count", 0)},
            })
    else:
        for dim_key, vals in sub_buckets.items():
            pct = (vals["score"] / vals["max_score"] * 100.0) if vals["max_score"] > 0 else 0.0
            dimensions.append({
                "dimension_key": dim_key,
                "dimension_label": format_dimension_label(dim_key),
                "raw_score": round(vals["score"], 2),
                "max_score": round(vals["max_score"], 2),
                "normalized_score": round(pct, 2),
                "percentile_band": resolve_percentile_band(pct),
                "evidence": {"question_count": int(vals["count"]), "inferred_from_mcq_text": True},
            })

    summary_metrics = {
        "has_open_composition": bool(composition_evaluations),
        "composition_count": len(composition_evaluations),
        "avg_word_count": (
            round(sum(e["word_count"] for e in composition_evaluations) / len(composition_evaluations), 1)
            if composition_evaluations
            else 0.0
        ),
        "avg_coherence": (
            round(sum(e["coherence_cohesion"] for e in composition_evaluations) / len(composition_evaluations), 2)
            if composition_evaluations
            else None
        ),
        "avg_topic_relevance": (
            round(sum(e["topic_relevance"] for e in composition_evaluations) / len(composition_evaluations), 2)
            if composition_evaluations
            else None
        ),
        "grammar_issues": [
            issue
            for e in composition_evaluations
            for issue in (e.get("issues") or [])
        ][:6],
    }

    return {
        "summary": summary_metrics,
        "composition_evaluations": composition_evaluations,
        "dimensions": dimensions,
    }

