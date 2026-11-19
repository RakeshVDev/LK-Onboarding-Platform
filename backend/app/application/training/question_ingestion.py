"""Local Offline NLP Question Extraction, Auto-Categorization & Bulk Upload Use Case.

Zero external AI APIs. Combines structured column mapping (CSV/Excel/tables)
with heuristic NLP block parsing (PDF/DOCX/PPTX) and weighted keyword-TF
auto-categorization + lexical complexity difficulty estimation.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.application.training.multi_set_selector import (
    build_numeric_scoring_key,
    normalize_question_set,
)
from app.application.training.ports import DocumentParserPort, QuestionBankRepository, RawExtractedDocument
from app.domain.training import (
    IngestionRowIssue,
    IngestionSummary,
    ParsedQuestionCandidate,
)

# Lexicon weights for 100% local offline NLP auto-categorization
CATEGORY_KEYWORD_LEXICON: dict[str, tuple[str, ...]] = {
    "reading_comprehension": (
        "passage", "according to the passage", "author implies", "author argues",
        "text states", "paragraph", "inference", "in the context of the passage",
    ),
    "logical_reasoning": (
        "series", "sequence", "missing number", "odd one out", "analogy",
        "blood relation", "sister", "brother", "north", "south", "east", "west",
        "coded as", "syllogism", "all ", "some ", "conclusions", "pattern",
    ),
    "cognitive": (
        "deduction", "analytical", "percentage", "ratio", "critical thinking",
        "assumption", "strengthen", "weaken", "throughput", "matrix",
    ),
    "programming": (
        "python", "javascript", "typescript", "sql", "query", "algorithm",
        "complexity", "o(log n)", "o(n)", "binary search", "linked list",
        "function", "output of", "debug", "stack", "queue", "fastapi", "hash",
    ),
    "english_grammar": (
        "sentence", "grammar", "tense", "preposition", "conjunction",
        "subject-verb", "synonym", "antonym", "idiom", "passive voice",
        "correct usage", "fill in the blank", "vocab", "grammar precision",
    ),
    "psychometric": (
        "teammate", "deadline", "collaborate", "feedback", "stakeholder",
        "workplace", "approach suits you", "how do you react", "peer", "conflict",
    ),
}

HEADER_ALIASES: dict[str, str] = {
    "q": "question_text",
    "question": "question_text",
    "questiontext": "question_text",
    "question_text": "question_text",
    "prompt": "question_text",
    "category": "category",
    "topic": "category",
    "domain": "category",
    "subject": "category",
    "difficulty": "difficulty",
    "level": "difficulty",
    "questiontype": "question_type",
    "question_type": "question_type",
    "type": "question_type",
    "set": "question_set",
    "questionset": "question_set",
    "question_set": "question_set",
    "setcode": "question_set",
    "a": "option_a",
    "optiona": "option_a",
    "option_a": "option_a",
    "opt_a": "option_a",
    "b": "option_b",
    "optionb": "option_b",
    "option_b": "option_b",
    "opt_b": "option_b",
    "c": "option_c",
    "optionc": "option_c",
    "option_c": "option_c",
    "opt_c": "option_c",
    "d": "option_d",
    "optiond": "option_d",
    "option_d": "option_d",
    "opt_d": "option_d",
    "options": "options_blob",
    "choices": "options_blob",
    "answer": "correct_answer",
    "correct": "correct_answer",
    "correctanswer": "correct_answer",
    "correct_answer": "correct_answer",
    "correctoption": "correct_answer",
    "correct_option": "correct_answer",
    "ans": "correct_answer",
    "explanation": "explanation",
    "rationale": "explanation",
    "passage": "passage_text",
    "readingpassage": "passage_text",
    "reading_passage": "passage_text",
    "passagetext": "passage_text",
    "passage_text": "passage_text",
    "context": "passage_text",
    "score": "max_score",
    "maxscore": "max_score",
    "max_score": "max_score",
    "marks": "max_score",
    "negativemarks": "negative_marks",
    "negative_marks": "negative_marks",
    "instructions": "instructions",
}


def _norm_key(raw: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]", "", (raw or "").strip().lower().replace(" ", "_").replace("-", "_"))
    return HEADER_ALIASES.get(cleaned, HEADER_ALIASES.get(cleaned.replace("_", ""), cleaned))


def _predict_question_ml_safe(text: str) -> tuple[list[str], dict[str, Any]]:
    try:
        from services.assessment_intelligence.ml_report_model import predict_question_nlp
        from services.assessment_intelligence.nlp_composition_analyzer import (
            extract_question_nlp_tokens,
        )

        tokens = extract_question_nlp_tokens(text)
        return tokens, predict_question_nlp(tokens)
    except Exception:
        return [], {}


def _infer_category_nlp(text: str, passage_text: str | None = None, default_category: str | None = None) -> tuple[str, bool]:
    if passage_text and len(passage_text.strip()) > 40:
        return "reading_comprehension", True

    combined = f"{text or ''} {passage_text or ''}"
    haystack = combined.lower()
    tokens, ml_pred = _predict_question_ml_safe(combined)
    token_set = set(tokens)

    scores: dict[str, float] = {}
    for category, keywords in CATEGORY_KEYWORD_LEXICON.items():
        score = 0.0
        for kw in keywords:
            if kw in haystack or (kw in token_set):
                score += 2.0 if " " in kw else 1.2
        if score > 0:
            scores[category] = score

    nb_cat = ml_pred.get("category")
    nb_conf = float(ml_pred.get("category_confidence") or 0.0)
    if nb_cat and nb_conf >= 0.45:
        if nb_cat in scores:
            scores[nb_cat] += nb_conf * 2.2
        elif not scores and nb_conf >= 0.55:
            scores[nb_cat] = nb_conf * 2.2

    if scores:
        best = max(scores.items(), key=lambda item: item[1])[0]
        return best, True
    if nb_cat and nb_conf >= 0.42:
        return str(nb_cat), True
    if default_category and default_category.strip():
        return default_category.strip().lower().replace(" ", "_"), False
    return "general_aptitude", True


def _infer_difficulty_nlp(text: str, explicit: str | None = None) -> str:
    if explicit and explicit.strip():
        val = explicit.strip().capitalize()
        if val in {"Easy", "Medium", "Hard"}:
            return val
        if val.lower() in {"beginner", "basic", "low", "1"}:
            return "Easy"
        if val.lower() in {"advanced", "complex", "high", "3"}:
            return "Hard"
        if val.lower() in {"intermediate", "moderate", "2"}:
            return "Medium"

    t = (text or "").lower()
    hard_signals = ("worst-case", "time complexity", "syllogism", "contrapositive", "weaken", "deadlock", "n+1", "must be true", "eigen", "recursive")
    if len(t) > 200 or any(tok in t for tok in hard_signals):
        return "Hard"
    if len(t) < 75 and "?" in t and not any(tok in t for tok in ("if ", "unless", "whereas", "although")):
        return "Easy"
    _, ml_pred = _predict_question_ml_safe(text or "")
    nb_diff = ml_pred.get("difficulty")
    nb_conf = float(ml_pred.get("difficulty_confidence") or 0.0)
    if nb_diff in {"Easy", "Medium", "Hard"} and nb_conf >= 0.58:
        return str(nb_diff)
    return "Medium"


def _resolve_correct_ids(
    raw_ans: str | None,
    options: list[dict[str, str]],
) -> list[str]:
    if not raw_ans:
        return []
    cleaned = str(raw_ans).strip()
    if not cleaned:
        return []

    # Comma-separated multi-select or single letter A/B/C/D
    parts = [p.strip() for p in re.split(r"[,;/|]", cleaned) if p.strip()]
    resolved: list[str] = []
    id_by_text = {opt["text"].strip().lower(): opt["id"] for opt in options if opt.get("text")}
    valid_ids = {opt["id"].upper() for opt in options}

    for part in parts:
        upper = re.sub(r"[^A-Z0-9]", "", part.upper())
        if upper in valid_ids and upper not in resolved:
            resolved.append(upper)
            continue
        # Handle "Option B" or "(B)" or numeric "1" -> "A"
        m_letter = re.match(r"^(?:OPTION\s*)?\(?([A-F])\)?$", part.strip(), re.I)
        if m_letter:
            lid = m_letter.group(1).upper()
            if lid in valid_ids and lid not in resolved:
                resolved.append(lid)
                continue
        if upper.isdigit():
            idx = int(upper) - 1
            if 0 <= idx < len(options):
                oid = options[idx]["id"]
                if oid not in resolved:
                    resolved.append(oid)
                continue
        matched_by_text = id_by_text.get(part.lower())
        if matched_by_text and matched_by_text not in resolved:
            resolved.append(matched_by_text)

    return resolved


class LocalNLPQuestionExtractor:
    """Transforms parsed table rows OR freeform document text blocks into validated Question Candidates."""

    QUESTION_START_RE = re.compile(r"^(?:Q(?:uestion)?\s*[\.#:-]?\s*\d+[\).:-]|\d{1,3}[\).])\s+(.+)$", re.I)
    OPTION_RE = re.compile(r"^(?:\(?([A-Da-d])\)?[\).:-]|Option\s+([A-Da-d])[\).:-]?)\s+(.+)$", re.I)
    ANSWER_RE = re.compile(r"^(?:Correct\s+Option|Correct\s+Answer|Answer|Ans)\s*[:\-]\s*(.+)$", re.I)
    DIFFICULTY_RE = re.compile(r"^(?:Difficulty|Level)\s*[:\-]\s*(.+)$", re.I)
    CATEGORY_RE = re.compile(r"^(?:Category|Topic|Subject|Domain)\s*[:\-]\s*(.+)$", re.I)
    SET_RE = re.compile(r"^(?:Question\s*Set|Set)\s*[:\-]\s*([A-Ca-c1-3])", re.I)
    PASSAGE_RE = re.compile(r"^(?:Reading\s+)?Passage(?:\s+[A-Z0-9]+)?\s*[:\-]?\s*(.*)$", re.I)
    EXPLANATION_RE = re.compile(r"^(?:Explanation|Rationale)\s*[:\-]\s*(.+)$", re.I)

    def extract(
        self,
        raw_doc: RawExtractedDocument,
        *,
        default_category: str | None = None,
        default_set: str = "A",
    ) -> list[ParsedQuestionCandidate]:
        candidates: list[ParsedQuestionCandidate] = []
        if raw_doc.table_rows:
            candidates.extend(
                self._extract_from_rows(
                    raw_doc.table_rows,
                    default_category=default_category,
                    default_set=default_set,
                )
            )
        if raw_doc.text_blocks:
            candidates.extend(
                self._extract_from_text_blocks(
                    raw_doc.text_blocks,
                    default_category=default_category,
                    default_set=default_set,
                    start_row_num=len(candidates) + 1,
                )
            )
        return candidates

    def _extract_from_rows(
        self,
        rows: list[dict[str, str]],
        *,
        default_category: str | None,
        default_set: str,
    ) -> list[ParsedQuestionCandidate]:
        results: list[ParsedQuestionCandidate] = []
        for idx, raw_row in enumerate(rows, start=1):
            norm = {_norm_key(k): ("" if v is None else str(v).strip()) for k, v in raw_row.items() if k is not None}
            q_text = norm.get("question_text", "").strip()
            if not q_text:
                continue

            options: list[dict[str, str]] = []
            for label, field in (("A", "option_a"), ("B", "option_b"), ("C", "option_c"), ("D", "option_d")):
                opt_val = norm.get(field, "").strip()
                if opt_val:
                    options.append({"id": label, "text": opt_val})

            if not options and norm.get("options_blob"):
                parts = [p.strip() for p in re.split(r"\|\||;|\n|\|", norm["options_blob"]) if p.strip()]
                for o_idx, part in enumerate(parts[:6]):
                    cleaned_part = re.sub(r"^\(?[A-F]\)?[\).:-]\s*", "", part).strip()
                    options.append({"id": chr(65 + o_idx), "text": cleaned_part or part})

            passage_text = norm.get("passage_text") or None
            explicit_cat = norm.get("category") or ""
            if explicit_cat:
                category = explicit_cat.lower().replace(" ", "_")
                auto_cat = False
            else:
                category, auto_cat = _infer_category_nlp(q_text, passage_text, default_category)

            difficulty = _infer_difficulty_nlp(q_text, norm.get("difficulty"))
            q_set = normalize_question_set(norm.get("question_set") or default_set)
            q_type = (norm.get("question_type") or "").strip().lower() or (
                "multiple_choice" if options else "short_answer"
            )
            correct_ids = _resolve_correct_ids(norm.get("correct_answer"), options)

            max_score = 1.0
            try:
                if norm.get("max_score"):
                    max_score = max(0.5, float(norm["max_score"]))
            except ValueError:
                max_score = 1.0

            neg_marks = 0.0
            try:
                if norm.get("negative_marks"):
                    neg_marks = max(0.0, float(norm["negative_marks"]))
            except ValueError:
                neg_marks = 0.0

            scoring_key = build_numeric_scoring_key(options, correct_ids, max_score)
            if len(correct_ids) > 1 and q_type == "multiple_choice":
                q_type = "multiple_select"

            results.append(
                ParsedQuestionCandidate(
                    row_number=idx,
                    question_text=q_text,
                    category=category,
                    difficulty=difficulty,
                    question_type=q_type,
                    question_set=q_set,
                    options=options,
                    correct_option_ids=correct_ids,
                    scoring_key=scoring_key,
                    max_score=max_score,
                    negative_marks=neg_marks,
                    instructions=norm.get("instructions") or None,
                    explanation=norm.get("explanation") or None,
                    passage_text=passage_text,
                    auto_categorized=auto_cat,
                )
            )
        return results

    def _extract_from_text_blocks(
        self,
        blocks: list[str],
        *,
        default_category: str | None,
        default_set: str,
        start_row_num: int = 1,
    ) -> list[ParsedQuestionCandidate]:
        lines: list[str] = []
        for block in blocks:
            for ln in str(block or "").splitlines():
                stripped = ln.strip()
                if stripped:
                    lines.append(stripped)

        results: list[ParsedQuestionCandidate] = []
        current_passage: str | None = None
        reading_passage = False
        passage_lines: list[str] = []

        current: dict[str, Any] | None = None
        q_counter = start_row_num

        def flush_current() -> None:
            nonlocal q_counter, current
            if not current or not current.get("question_text"):
                current = None
                return
            q_text = current["question_text"].strip()
            options = current["options"]
            ans_raw = current.get("answer_raw")
            correct_ids = _resolve_correct_ids(ans_raw, options)
            if not correct_ids and current.get("starred_ids"):
                correct_ids = list(current["starred_ids"])
            p_text = current.get("passage_text") or current_passage
            explicit_cat = current.get("category")
            if explicit_cat:
                category = explicit_cat.lower().replace(" ", "_")
                auto_cat = False
            else:
                category, auto_cat = _infer_category_nlp(q_text, p_text, default_category)

            difficulty = _infer_difficulty_nlp(q_text, current.get("difficulty"))
            q_set = normalize_question_set(current.get("question_set") or default_set)
            q_type = "multiple_select" if len(correct_ids) > 1 else ("multiple_choice" if options else "short_answer")
            scoring_key = build_numeric_scoring_key(options, correct_ids, 1.0)

            results.append(
                ParsedQuestionCandidate(
                    row_number=q_counter,
                    question_text=q_text,
                    category=category,
                    difficulty=difficulty,
                    question_type=q_type,
                    question_set=q_set,
                    options=options,
                    correct_option_ids=correct_ids,
                    scoring_key=scoring_key,
                    explanation=current.get("explanation"),
                    passage_text=p_text,
                    auto_categorized=auto_cat,
                )
            )
            q_counter += 1
            current = None

        for line in lines:
            p_match = self.PASSAGE_RE.match(line)
            if p_match and not self.QUESTION_START_RE.match(line):
                flush_current()
                reading_passage = True
                passage_lines = [p_match.group(1).strip()] if p_match.group(1).strip() else []
                current_passage = None
                continue

            q_match = self.QUESTION_START_RE.match(line)
            if q_match:
                if reading_passage:
                    current_passage = "\n".join(passage_lines).strip() or None
                    reading_passage = False
                flush_current()
                current = {
                    "question_text": q_match.group(1).strip(),
                    "options": [],
                    "starred_ids": [],
                    "passage_text": current_passage,
                }
                continue

            if reading_passage:
                passage_lines.append(line)
                continue

            if current is None:
                continue

            opt_match = self.OPTION_RE.match(line)
            if opt_match:
                letter = (opt_match.group(1) or opt_match.group(2)).upper()
                opt_text = opt_match.group(3).strip()
                if opt_text.endswith("*") or opt_text.endswith("[correct]"):
                    opt_text = re.sub(r"(\*|\[correct\])$", "", opt_text, flags=re.I).strip()
                    current["starred_ids"].append(letter)
                current["options"].append({"id": letter, "text": opt_text})
                continue

            ans_match = self.ANSWER_RE.match(line)
            if ans_match:
                current["answer_raw"] = ans_match.group(1).strip()
                continue

            diff_match = self.DIFFICULTY_RE.match(line)
            if diff_match:
                current["difficulty"] = diff_match.group(1).strip()
                continue

            cat_match = self.CATEGORY_RE.match(line)
            if cat_match:
                current["category"] = cat_match.group(1).strip()
                continue

            set_match = self.SET_RE.match(line)
            if set_match:
                current["question_set"] = set_match.group(1).strip()
                continue

            exp_match = self.EXPLANATION_RE.match(line)
            if exp_match:
                current["explanation"] = exp_match.group(1).strip()
                continue

            # Append continuation lines onto active question text before options arrive
            if not current["options"]:
                current["question_text"] = f"{current['question_text']} {line}".strip()

        if reading_passage and passage_lines:
            current_passage = "\n".join(passage_lines).strip()
        flush_current()
        return results


class BulkQuestionIngestionUseCase:
    """Orchestrates parsing, validation, NLP auto-categorization, and DB Question Bank insertion."""

    def __init__(
        self,
        parser: DocumentParserPort,
        repo: QuestionBankRepository,
        extractor: LocalNLPQuestionExtractor | None = None,
    ):
        self.parser = parser
        self.repo = repo
        self.extractor = extractor or LocalNLPQuestionExtractor()

    def execute(
        self,
        *,
        template_id: int,
        filename: str,
        content: bytes,
        created_by_user_id: int,
        default_set: str = "A",
        default_category: str | None = None,
        dry_run: bool = False,
    ) -> IngestionSummary:
        if not self.repo.template_exists(template_id):
            raise LookupError(f"Assessment template {template_id} not found.")

        inferred_default_cat = default_category or self.repo.get_template_type(template_id) or "general_aptitude"
        raw_doc = self.parser.parse(filename, content)
        candidates = self.extractor.extract(
            raw_doc,
            default_category=inferred_default_cat,
            default_set=normalize_question_set(default_set),
        )

        valid_candidates: list[ParsedQuestionCandidate] = []
        issues: list[IngestionRowIssue] = []

        for item in candidates:
            errors: list[str] = []
            warnings: list[str] = list(item.warnings)

            if len(item.question_text.strip()) < 5:
                errors.append("Question text must be at least 5 characters.")

            if item.question_type in {"multiple_choice", "single_choice", "multiple_select", "true_false"}:
                if len(item.options) < 2:
                    errors.append("Choice question requires at least 2 options.")
                elif not item.correct_option_ids:
                    errors.append("Missing valid correct answer matching provided options.")

            if item.auto_categorized:
                warnings.append(f"Auto-categorized via local NLP as '{item.category}'.")

            issue = IngestionRowIssue(
                row_number=item.row_number,
                valid=(len(errors) == 0),
                question_preview=item.question_text[:120],
                category=item.category,
                question_set=item.question_set,
                difficulty=item.difficulty,
                errors=errors,
                warnings=warnings,
            )
            issues.append(issue)
            if not errors:
                valid_candidates.append(item)

        inserted_ids: list[int] = []
        if not dry_run and valid_candidates:
            inserted_ids = self.repo.bulk_insert(
                template_id=template_id,
                candidates=valid_candidates,
                created_by_user_id=created_by_user_id,
            )
            valid_idx = 0
            for issue in issues:
                if issue.valid and valid_idx < len(inserted_ids):
                    issue.bank_question_id = inserted_ids[valid_idx]
                    valid_idx += 1

        cat_counts = Counter(c.category for c in valid_candidates)
        set_counts = Counter(c.question_set for c in valid_candidates)

        return IngestionSummary(
            filename=raw_doc.filename,
            file_format=raw_doc.file_format,
            template_id=template_id,
            dry_run=dry_run,
            total_detected=len(candidates),
            valid_count=len(valid_candidates),
            inserted_count=len(inserted_ids),
            failed_count=len(candidates) - len(valid_candidates),
            items=issues,
            detected_categories=dict(cat_counts),
            detected_sets=dict(set_counts),
        )
