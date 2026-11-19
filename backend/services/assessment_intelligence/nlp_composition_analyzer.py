"""Advanced Offline NLP Composition, Grammar Mechanics, Semantic Concept & Discourse Analyzer.

Combines pure-Python statistical NLP with supervised text quality models:
- Morphological lemmatization (`normalize_lemma`) & expanded stopword filtering
- Domain semantic concept cluster expansion (`SEMANTIC_CONCEPT_CLUSTERS`) for synonym/paraphrase matching
- Sublinear TF-IDF (`1 + log(tf)`) + BM25 saturation + corpus-trained IDF + char 3-gram similarity
- Adjacent sentence semantic continuity + 4-family rhetorical discourse connective analysis
- Syntactic rhythm variance, subordinate clause density, active/passive voice & subject-verb grammar checks
- Supervised Softmax Writing-Quality Classifier trained across assessment essays & short answers
"""

from collections import Counter, defaultdict
import math
import re
from typing import Any

from services.assessment_intelligence.config import (
    format_dimension_label,
    resolve_percentile_band,
)
from services.assessment_intelligence.ml_report_model import (
    get_trained_idf_map,
    predict_nlp_text_quality,
)


STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "he", "her", "him", "his", "in", "into", "is", "it", "its", "may", "might",
    "more", "most", "no", "not", "of", "on", "or", "our", "out", "over", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "them",
    "then", "there", "these", "they", "this", "those", "to", "under", "up",
    "was", "we", "were", "what", "when", "which", "who", "will", "with", "would",
    "you", "your",
})

DISCOURSE_FAMILIES: dict[str, frozenset[str]] = {
    "causal": frozenset({"therefore", "consequently", "thus", "hence", "accordingly", "because", "since", "so"}),
    "contrastive": frozenset({"however", "nevertheless", "although", "though", "whereas", "instead", "despite", "conversely"}),
    "additive": frozenset({"moreover", "furthermore", "additionally", "similarly", "likewise", "also", "besides"}),
    "sequential": frozenset({"firstly", "secondly", "thirdly", "meanwhile", "subsequently", "finally", "ultimately", "overall", "specifically"}),
}

DISCOURSE_CONNECTIVES: frozenset[str] = frozenset().union(*DISCOURSE_FAMILIES.values())

SUBORDINATE_MARKERS = frozenset({
    "because", "although", "though", "whereas", "unless", "until", "since",
    "while", "which", "whose", "where", "if", "whenever", "whether",
})

IRREGULAR_LEMMAS: dict[str, str] = {
    "running": "run",
    "ran": "run",
    "writing": "write",
    "wrote": "write",
    "written": "write",
    "queries": "query",
    "queues": "queue",
    "retries": "retry",
    "dependencies": "dependency",
    "processes": "process",
    "indexes": "index",
    "indices": "index",
    "analyses": "analysis",
    "analyzing": "analyze",
    "cached": "cache",
    "caching": "cache",
    "scaling": "scale",
    "scalable": "scale",
    "decoupled": "decouple",
    "decoupling": "decouple",
    "architectural": "architecture",
    "architectures": "architecture",
    "distributed": "distribute",
    "optimizing": "optimize",
    "optimization": "optimize",
    "normalized": "normalize",
    "normalization": "normalize",
    "collaborating": "collaborate",
    "collaboration": "collaborate",
    "communicating": "communicate",
    "communication": "communicate",
}

SEMANTIC_CONCEPT_CLUSTERS: dict[str, frozenset[str]] = {
    "async_messaging": frozenset({"async", "asynchronous", "nonblocking", "queue", "kafka", "rabbitmq", "broker", "event", "pub", "sub", "worker"}),
    "reliability_retry": frozenset({"idempotent", "idempotency", "retry", "dead-letter", "dlq", "resilient", "resilience", "fault", "backoff", "recover", "duplication"}),
    "microservices_arch": frozenset({"microservice", "service", "decouple", "boundary", "context", "api", "gateway", "rest", "grpc", "modular"}),
    "caching_perf": frozenset({"cache", "redis", "ttl", "latency", "throughput", "hit", "invalidation", "eviction", "bottleneck", "memory"}),
    "database_sql": frozenset({"sql", "database", "index", "join", "query", "acid", "transaction", "lock", "deadlock", "partition", "normalize", "schema"}),
    "algorithms_complexity": frozenset({"algorithm", "complexity", "big-o", "log", "linear", "quadratic", "binary", "recursion", "dynamic", "graph", "tree", "heap"}),
    "concurrency_os": frozenset({"thread", "process", "mutex", "semaphore", "deadlock", "concurrent", "parallel", "scheduler", "virtual"}),
    "security_auth": frozenset({"auth", "authentication", "authorization", "jwt", "token", "rbac", "sanitize", "xss", "csrf", "injection", "hash", "encrypt"}),
    "logic_deduction": frozenset({"series", "sequence", "pattern", "syllogism", "deduce", "deduction", "premise", "conclusion", "cipher", "relation", "direction"}),
    "grammar_syntax": frozenset({"tense", "verb", "subject", "agreement", "concord", "article", "preposition", "clause", "conjunction", "passive", "punctuation"}),
    "comprehension_evidence": frozenset({"passage", "author", "infer", "inference", "evidence", "claim", "tone", "argument", "context"}),
    "team_workplace": frozenset({"collaborate", "stakeholder", "feedback", "deadline", "conflict", "empathy", "align", "mentor", "ownership", "transparent"}),
}

_TERM_TO_CONCEPTS: dict[str, list[str]] = {}
for _ckey, _cwords in SEMANTIC_CONCEPT_CLUSTERS.items():
    for _cw in _cwords:
        _TERM_TO_CONCEPTS.setdefault(_cw, []).append(_ckey)

GRAMMAR_TOPIC_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("subject_verb_agreement", ("agreement", "neither", "either", "committee", "each of", "plural", "team", "subject-verb")),
    ("tenses_and_aspects", ("tense", "past tense", "next week", "years", "had", "will have", "wrote", "continuous", "perfect")),
    ("articles_prepositions", ("article", "preposition", "honest", "good at", "between you", "a ", "an ", "the ")),
    ("voice_speech_connectors", ("passive voice", "reported speech", "conjunction", "question tag", "said", "if i")),
    ("vocabulary_usage", ("spelled", "punctuation", "affect", "effect", "comparative", "vocabulary", "synonym", "antonym", "idiom")),
    ("sentence_syntax", ("grammatically correct", "correct sentence", "fewer", "less", "clause", "modifier")),
]

PASSIVE_AUX_RE = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+[a-z]+(?:ed|en)\b", re.IGNORECASE)
SV_DISAGREEMENT_RE = re.compile(
    r"\b(?:there\s+is\s+(?:many|several|two|three|four|multiple|various)|(?:he|she|it)\s+don't|(?:they|we)\s+(?:was|is)|doesn't\s+(?:has|had|went))\b",
    re.IGNORECASE,
)


def normalize_lemma(token: str) -> str:
    """Lightweight morphological normalizer for technical and academic English tokens."""
    w = (token or "").lower().strip("'-")
    if len(w) <= 3:
        return w
    if w in IRREGULAR_LEMMAS:
        return IRREGULAR_LEMMAS[w]
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ation") and len(w) > 7:
        return w[:-5]
    if w.endswith("ment") and len(w) > 6:
        return w[:-4]
    if w.endswith("ing") and len(w) > 5:
        stem = w[:-3]
        if len(stem) >= 3 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if w.endswith("ed") and len(w) > 4:
        stem = w[:-2]
        if len(stem) >= 3 and stem[-1] == stem[-2]:
            stem = stem[:-1]
        return stem
    if w.endswith("ly") and len(w) > 4:
        return w[:-2]
    if w.endswith("es") and len(w) > 4 and w[-3] in {"s", "x", "z", "h"}:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def _tokenize_words(text: str, drop_stopwords: bool = True, lemmatize: bool = False) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]*", (text or "").lower())
    out: list[str] = []
    for tok in tokens:
        if drop_stopwords and (tok in STOPWORDS or len(tok) <= 1):
            continue
        out.append(normalize_lemma(tok) if lemmatize else tok)
    return out


def expand_semantic_concepts(lemmas: list[str]) -> list[str]:
    """Map lemmatized words to canonical domain concept tags for semantic overlap matching."""
    concepts: list[str] = []
    for lm in lemmas:
        for ckey in _TERM_TO_CONCEPTS.get(lm, ()):
            concepts.append(f"__concept_{ckey}")
    return concepts


def extract_question_nlp_tokens(text: str, passage_text: str | None = None) -> list[str]:
    """Build combined lemma + bigram + semantic concept tokens for NLP classification."""
    combined = f"{text or ''} {passage_text or ''}".strip()
    lemmas = _tokenize_words(combined, drop_stopwords=True, lemmatize=True)
    bigrams = [f"{lemmas[i]}_{lemmas[i + 1]}" for i in range(len(lemmas) - 1)]
    concepts = expand_semantic_concepts(lemmas)
    return lemmas + bigrams + concepts


def _word_ngrams(tokens: list[str]) -> list[str]:
    grams = list(tokens)
    if len(tokens) >= 2:
        grams.extend(f"{tokens[i]}_{tokens[i + 1]}" for i in range(len(tokens) - 1))
    grams.extend(expand_semantic_concepts(tokens))
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
    """Compute sublinear TF-IDF + trained corpus IDF + semantic concept + char-3gram cosine similarity."""
    docs = [text_a or "", text_b or ""]
    if corpus_docs:
        docs.extend(d for d in corpus_docs if d)

    tokenized_docs = [_word_ngrams(_tokenize_words(d, drop_stopwords=True, lemmatize=True)) for d in docs]
    n_docs = len(tokenized_docs)
    avg_dl = sum(len(d) for d in tokenized_docs) / max(1, n_docs)
    df: Counter[str] = Counter()
    for doc_tokens in tokenized_docs:
        df.update(set(doc_tokens))

    trained_idf = get_trained_idf_map()

    def build_bm25_tfidf(tokens: list[str]) -> dict[str, float]:
        if not tokens:
            return {}
        tf = Counter(tokens)
        dl = len(tokens)
        k1 = 1.2
        b = 0.75
        norm_len = (1.0 - b) + b * (dl / max(1.0, avg_dl))
        vec: dict[str, float] = {}
        for term, cnt in tf.items():
            sub_tf = ((cnt * (k1 + 1.0)) / (cnt + k1 * norm_len)) * (1.0 + 0.25 * math.log1p(cnt))
            local_idf = math.log((1.0 + n_docs) / (1.0 + df.get(term, 0))) + 1.0
            idf = 0.65 * local_idf + 0.35 * trained_idf[term] if term in trained_idf else local_idf
            concept_boost = 1.25 if term.startswith("__concept_") else 1.0
            vec[term] = sub_tf * idf * concept_boost
        return vec

    vec_a = build_bm25_tfidf(tokenized_docs[0])
    vec_b = build_bm25_tfidf(tokenized_docs[1])
    word_sim = _cosine_sim(vec_a, vec_b)

    char_a = {k: float(v) for k, v in _char_trigrams(text_a).items()}
    char_b = {k: float(v) for k, v in _char_trigrams(text_b).items()}
    char_sim = _cosine_sim(char_a, char_b)

    return round(0.76 * word_sim + 0.24 * char_sim, 4)


def _split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", (text or "").strip()) if s.strip()]
    return parts if parts else ([text.strip()] if (text or "").strip() else [])


def _check_grammar_mechanics(text: str, sentences: list[str], all_words: list[str]) -> dict[str, Any]:
    issues: list[str] = []
    deductions = 0.0

    # 1. Duplicate consecutive words ("the the")
    dup_matches = re.findall(r"\b([a-zA-Z]+)\s+\1\b", text, flags=re.IGNORECASE)
    if dup_matches:
        issues.append(f"Repeated consecutive word detected ({dup_matches[0]}).")
        deductions += min(20.0, len(dup_matches) * 8.0)

    # 2. Subject-verb disagreement / tense inflection patterns
    sv_errors = SV_DISAGREEMENT_RE.findall(text)
    if sv_errors:
        issues.append(f"Subject-verb or auxiliary verb agreement error near '{sv_errors[0]}'.")
        deductions += min(18.0, len(sv_errors) * 9.0)

    # 3. Capitalization at sentence starts
    lowercase_starts = sum(1 for s in sentences if s and s[0].islower())
    if lowercase_starts > 0:
        issues.append(f"{lowercase_starts} sentence(s) do not start with a capital letter.")
        deductions += min(18.0, lowercase_starts * 6.0)

    # 4. Terminal punctuation on final/multiple sentences
    missing_end_punct = sum(1 for s in sentences if len(s.split()) >= 4 and s[-1] not in ".!?")
    if missing_end_punct > 0:
        issues.append(f"{missing_end_punct} sentence(s) lack terminal punctuation.")
        deductions += min(15.0, missing_end_punct * 5.0)

    # 5. Indefinite article heuristic ("a apple", excluding 'u'/'eu' sounds & 'one')
    bad_a = re.findall(r"\ba\s+(?!(?:user|unit|unique|uniform|university|european|one)\b)[aeiou][a-z]+\b", text, flags=re.IGNORECASE)
    if bad_a:
        issues.append("Possible indefinite article mismatch ('a' before vowel sound).")
        deductions += min(12.0, len(bad_a) * 6.0)

    # 6. Excessive sentence run-on check (> 42 words without break)
    run_ons = [s for s in sentences if len(_tokenize_words(s, drop_stopwords=False)) > 42]
    if run_ons:
        issues.append(f"{len(run_ons)} overly long sentence(s) (>42 words) may hinder clarity.")
        deductions += min(15.0, len(run_ons) * 7.0)

    if len(all_words) < 12:
        issues.append("Response is too brief for complete syntactic validation.")
        deductions += 25.0

    score = round(max(0.0, min(100.0, 100.0 - deductions)), 2)
    return {"mechanics_score": score, "issues": issues}


def _analyze_discourse_and_syntax(
    text: str,
    sentences: list[str],
    all_words: list[str],
) -> dict[str, Any]:
    """Extract rhetorical connective diversity, syntactic sentence rhythm, clause complexity, and voice balance."""
    lower_words = [w.lower() for w in all_words]
    families_used = {
        fam
        for fam, cues in DISCOURSE_FAMILIES.items()
        if any(w in cues for w in lower_words)
    }
    discourse_hits = sum(1 for w in lower_words if w in DISCOURSE_CONNECTIVES)
    subordinate_hits = sum(1 for w in lower_words if w in SUBORDINATE_MARKERS)

    sent_lengths = [max(1, len(_tokenize_words(s, drop_stopwords=False))) for s in sentences] or [0]
    avg_len = sum(sent_lengths) / max(1, len(sent_lengths))
    len_std = math.sqrt(sum((x - avg_len) ** 2 for x in sent_lengths) / max(1, len(sent_lengths)))
    # Balanced syntactic rhythm rewards varied sentences (std 3..10 words) without fragmentation
    rhythm_score = min(100.0, (min(len_std, 8.0) / 6.0) * 60.0 + min(40.0, (subordinate_hits / max(1, len(sentences))) * 35.0))

    passive_matches = PASSIVE_AUX_RE.findall(text or "")
    passive_ratio = round(len(passive_matches) / max(1, len(sentences)), 3)

    return {
        "discourse_families": sorted(families_used),
        "discourse_diversity": len(families_used),
        "discourse_hits": discourse_hits,
        "subordinate_ratio": round(subordinate_hits / max(1, len(sentences)), 3),
        "avg_sentence_len": round(avg_len, 2),
        "sentence_len_std": round(len_std, 2),
        "syntactic_rhythm_score": round(rhythm_score, 2),
        "passive_voice_ratio": passive_ratio,
    }


def analyze_composition_response(question: dict[str, Any], response_text: str) -> dict[str, Any]:
    """Grade an open-ended composition / essay / short-answer response using advanced NLP + Supervised Classifier."""
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
            "semantic_concept_coverage": 0.0,
            "discourse_diversity": 0,
            "syntactic_rhythm_score": 0.0,
            "nlp_quality_band": "weak_quality",
            "nlp_quality_confidence": 1.0,
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
    content_lemmas = _tokenize_words(text, drop_stopwords=True, lemmatize=True)
    ref_lemmas = _tokenize_words(reference_blob, drop_stopwords=True, lemmatize=True)
    word_count = len(all_words)

    # 1. Sublinear BM25/TF-IDF + Semantic Concept Cluster Relevance
    prompt_sim = tfidf_cosine_similarity(text, reference_blob, corpus_docs=sentences)
    resp_concepts = set(expand_semantic_concepts(content_lemmas))
    ref_concepts = set(expand_semantic_concepts(ref_lemmas))
    concept_overlap = (
        len(resp_concepts & ref_concepts) / max(1, len(ref_concepts))
        if ref_concepts
        else min(1.0, len(resp_concepts) / 3.0)
    )

    keyword_hits = 0
    if rubric_keywords:
        lower_text = text.lower()
        resp_lemma_set = set(content_lemmas)
        for kw in rubric_keywords:
            kw_clean = str(kw).lower().strip()
            if kw_clean in lower_text or normalize_lemma(kw_clean) in resp_lemma_set:
                keyword_hits += 1
        kw_coverage = keyword_hits / len(rubric_keywords)
        concept_coverage_pct = round(min(100.0, (0.65 * kw_coverage + 0.35 * concept_overlap) * 100.0), 2)
        relevance_score = round(
            min(100.0, (0.50 * min(1.0, prompt_sim * 1.85) + 0.35 * kw_coverage + 0.15 * concept_overlap) * 100.0),
            2,
        )
    else:
        concept_coverage_pct = round(min(100.0, concept_overlap * 100.0), 2)
        relevance_score = round(
            min(100.0, (0.78 * min(1.0, prompt_sim * 2.0) + 0.22 * concept_overlap) * 100.0),
            2,
        )

    # 2. Adjacent Sentence Semantic Coherence + Multi-Family Discourse Markers
    discourse = _analyze_discourse_and_syntax(text, sentences, all_words)
    if len(sentences) >= 2:
        adj_sims = [
            tfidf_cosine_similarity(sentences[i], sentences[i + 1], corpus_docs=sentences)
            for i in range(len(sentences) - 1)
        ]
        mean_adj = sum(adj_sims) / len(adj_sims)
        discourse_bonus = min(0.32, discourse["discourse_hits"] * 0.06 + discourse["discourse_diversity"] * 0.06)
        coherence_score = round(min(100.0, (min(1.0, mean_adj * 1.8) * 0.68 + discourse_bonus) * 100.0), 2)
    else:
        coherence_score = round(min(65.0, relevance_score * 0.65), 2)

    # 3. Mechanics & Grammar checks
    mechanics = _check_grammar_mechanics(text, sentences, all_words)

    # 4. Lexical Richness (Root TTR over morphological lemmas)
    unique_lemmas = len(set(content_lemmas))
    if content_lemmas:
        rttr = unique_lemmas / math.sqrt(len(content_lemmas))
        lexical_score = round(min(100.0, max(15.0, (rttr / 5.2) * 100.0)), 2)
    else:
        lexical_score = 0.0

    # 5. Readability & Syntactic Clarity (ARI + Syntactic Rhythm + Length adequacy)
    chars = sum(len(w) for w in all_words)
    sent_cnt = max(1, len(sentences))
    w_cnt = max(1, word_count)
    ari = 4.71 * (chars / w_cnt) + 0.5 * (w_cnt / sent_cnt) - 21.43
    min_target_words = int(sk.get("min_words") or 25)
    length_factor = min(1.0, word_count / max(15, min_target_words))
    clarity_base = 88.0 if 6.0 <= ari <= 15.0 else (72.0 if 3.5 <= ari < 6.0 or 15.0 < ari <= 18.5 else 55.0)
    readability_score = round((0.80 * clarity_base + 0.20 * discourse["syntactic_rhythm_score"]) * length_factor, 2)

    # 6. Supervised NLP Writing Quality Classifier (12 engineered features)
    nlp_feature_vec = [
        relevance_score,
        coherence_score,
        mechanics["mechanics_score"],
        lexical_score,
        readability_score,
        concept_coverage_pct,
        float(discourse["discourse_diversity"]),
        float(discourse["discourse_hits"]),
        float(discourse["subordinate_ratio"]),
        float(discourse["syntactic_rhythm_score"]),
        float(length_factor),
        float(min(40.0, max(0.0, ari))),
    ]
    sup_quality = predict_nlp_text_quality(nlp_feature_vec)

    composite = round(
        0.27 * relevance_score
        + 0.24 * coherence_score
        + 0.23 * mechanics["mechanics_score"]
        + 0.13 * lexical_score
        + 0.13 * readability_score,
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
        "semantic_concept_coverage": concept_coverage_pct,
        "discourse_diversity": discourse["discourse_diversity"],
        "discourse_families": discourse["discourse_families"],
        "syntactic_rhythm_score": discourse["syntactic_rhythm_score"],
        "passive_voice_ratio": discourse["passive_voice_ratio"],
        "nlp_quality_band": sup_quality["quality_band"],
        "nlp_quality_confidence": sup_quality["confidence"],
        "ari_grade": round(max(1.0, ari), 2),
        "keyword_hits": keyword_hits,
        "issues": mechanics["issues"],
    }


def _classify_grammar_question(question: dict[str, Any]) -> str:
    raw_cat = str(question.get("category") or "").strip().lower()
    if raw_cat and raw_cat not in {"english_grammar", "general"}:
        return raw_cat
    text = f"{question.get('question_text', '')} {question.get('instructions', '')}".lower()
    lemmas = set(_tokenize_words(text, drop_stopwords=True, lemmatize=True))
    for dim_key, keywords in GRAMMAR_TOPIC_RULES:
        if any(kw in text or normalize_lemma(kw.strip()) in lemmas for kw in keywords):
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
        "word_count": (
            int(sum(e["word_count"] for e in composition_evaluations))
            if composition_evaluations
            else 0
        ),
        "sentence_count": (
            int(sum(e["sentence_count"] for e in composition_evaluations))
            if composition_evaluations
            else 0
        ),
        "avg_word_count": (
            round(sum(e["word_count"] for e in composition_evaluations) / len(composition_evaluations), 1)
            if composition_evaluations
            else 0.0
        ),
        "topic_relevance": (
            round(sum(e["topic_relevance"] for e in composition_evaluations) / len(composition_evaluations), 2)
            if composition_evaluations
            else None
        ),
        "coherence_cohesion": (
            round(sum(e["coherence_cohesion"] for e in composition_evaluations) / len(composition_evaluations), 2)
            if composition_evaluations
            else None
        ),
        "grammar_mechanics": (
            round(sum(e["grammar_mechanics"] for e in composition_evaluations) / len(composition_evaluations), 2)
            if composition_evaluations
            else None
        ),
        "semantic_concept_coverage": (
            round(sum(e.get("semantic_concept_coverage", 0.0) for e in composition_evaluations) / len(composition_evaluations), 2)
            if composition_evaluations
            else None
        ),
        "discourse_diversity": (
            max(int(e.get("discourse_diversity", 0)) for e in composition_evaluations)
            if composition_evaluations
            else 0
        ),
        "nlp_quality_band": (
            composition_evaluations[-1].get("nlp_quality_band")
            if composition_evaluations
            else None
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
        "avg_grammar_mechanics": (
            round(sum(e["grammar_mechanics"] for e in composition_evaluations) / len(composition_evaluations), 2)
            if composition_evaluations
            else None
        ),
        "issues": [
            issue
            for e in composition_evaluations
            for issue in (e.get("issues") or [])
        ][:6],
        "grammar_issues": [
            issue
            for e in composition_evaluations
            for issue in (e.get("issues") or [])
        ][:6],
    }

    return {
        "mode": "composition_nlp" if composition_evaluations else "syntactic_clustering",
        "summary": summary_metrics,
        "composition_evaluations": composition_evaluations,
        "dimensions": dimensions,
    }
