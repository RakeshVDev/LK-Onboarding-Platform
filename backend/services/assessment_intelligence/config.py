"""Configuration constants, taxonomy mappings, and default scoring parameters
for the Assessment Intelligence package.
"""

from typing import Any

DEFAULT_SCORING_VERSION_TAG = "v2.0-local-ml"

ALLOWED_ASSESSMENT_TYPES = frozenset({
    "psychometric",
    "cognitive",
    "logical_reasoning",
    "english_grammar",
    "comprehension",
    "composition",
    "technical",
    "algorithm",
    "programming",
})

DIFFICULTY_WEIGHTS: dict[str, float] = {
    "easy": 1.0,
    "medium": 1.15,
    "hard": 1.35,
}

BENCHMARK_TARGET_PERCENT = 75.0

PERCENTILE_BANDS: list[tuple[float, str]] = [
    (85.0, "Exceptional"),
    (70.0, "Proficient"),
    (50.0, "Developing"),
    (35.0, "Foundational"),
    (0.0, "Needs Immediate Focus"),
]


def resolve_percentile_band(score: float) -> str:
    val = float(score or 0.0)
    for threshold, label in PERCENTILE_BANDS:
        if val >= threshold:
            return label
    return "Needs Immediate Focus"


DEFAULT_DOMAIN_WEIGHTS: dict[str, dict[str, Any]] = {
    "psychometric": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {
            "personality_work_preferences": 1.0,
            "logical_reasoning": 1.0,
            "situational_judgement": 1.15,
            "emotional_intelligence": 1.15,
            "learning_adaptability": 1.10,
            "team_collaboration": 1.05,
        },
        "expected_duration_minutes": 15,
    },
    "logical_reasoning": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {
            "number_series": 1.0,
            "alphabet_series": 1.0,
            "coding_decoding": 1.1,
            "blood_relations": 1.0,
            "direction_distance": 1.0,
            "pattern_recognition": 1.15,
            "logical_statements": 1.2,
            "odd_one_out": 0.95,
            "analogy": 1.0,
        },
        "expected_duration_minutes": 30,
    },
    "cognitive": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {},
        "expected_duration_minutes": 30,
    },
    "english_grammar": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {
            "subject_verb_agreement": 1.1,
            "tenses_and_aspects": 1.1,
            "tenses": 1.1,
            "articles": 0.95,
            "prepositions": 1.0,
            "conjunctions": 1.0,
            "sentence_correction": 1.15,
            "error_detection": 1.1,
            "vocabulary": 1.0,
            "voice_and_speech": 1.05,
            "reading_comprehension": 1.15,
            "written_composition": 1.25,
        },
        "expected_duration_minutes": 15,
    },
    "composition": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {
            "topic_relevance": 1.2,
            "coherence_cohesion": 1.15,
            "grammar_mechanics": 1.15,
            "lexical_richness": 1.0,
            "structure_clarity": 1.1,
        },
        "expected_duration_minutes": 20,
    },
    "comprehension": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {
            "reading_comprehension": 1.2,
            "analytical_deduction": 1.25,
            "inference_evidence": 1.15,
            "vocabulary_in_context": 1.0,
        },
        "expected_duration_minutes": 25,
    },
    "technical": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {
            "data_structures": 1.2,
            "algorithms": 1.2,
            "databases_sql": 1.15,
            "system_design": 1.2,
            "python_programming": 1.1,
            "javascript_web": 1.1,
            "git_devops": 1.0,
            "networking": 1.0,
            "operating_systems": 1.05,
        },
        "expected_duration_minutes": 15,
    },
    "programming": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {
            "programming_logic": 1.15,
            "algorithm_understanding": 1.2,
            "code_output": 1.1,
            "problem_solving": 1.2,
            "debugging": 1.15,
            "time_complexity": 1.2,
            "data_structures": 1.15,
        },
        "expected_duration_minutes": 30,
    },
    "algorithm": {
        "difficulty_multipliers": DIFFICULTY_WEIGHTS,
        "dimension_weights": {
            "algorithm_understanding": 1.25,
            "time_complexity": 1.25,
            "problem_solving": 1.2,
            "code_quality": 1.1,
            "test_case_correctness": 1.3,
        },
        "expected_duration_minutes": 30,
    },
}

DIMENSION_LABELS: dict[str, str] = {
    # Psychometric
    "personality_work_preferences": "Work Style & Autonomy",
    "situational_judgement": "Situational Judgement",
    "emotional_intelligence": "Emotional Intelligence",
    "learning_adaptability": "Learning Agility",
    "team_collaboration": "Team Collaboration",
    # Cognitive & Logical Reasoning
    "logical_reasoning": "Deductive Logic",
    "number_series": "Number Series",
    "alphabet_series": "Alphabet Patterns",
    "coding_decoding": "Coding-Decoding",
    "blood_relations": "Relational Logic",
    "direction_distance": "Spatial Direction",
    "pattern_recognition": "Pattern Matrices",
    "logical_statements": "Syllogisms & Logic",
    "odd_one_out": "Classification",
    "analogy": "Analogies",
    "quantitative_reasoning": "Quantitative Patterning",
    "symbolic_decoding": "Symbolic & Cipher Logic",
    "spatial_relational": "Spatial & Relational Reasoning",
    "verbal_classification": "Conceptual Classification",
    "time_efficiency_index": "Cognitive Speed-Accuracy",
    # Grammar & Composition
    "english_grammar": "Grammar & Mechanics",
    "grammar_concord": "Grammar & Concord",
    "tenses_and_aspects": "Verb Tenses & Aspect",
    "subject_verb_agreement": "Subject-Verb Agreement",
    "articles_prepositions": "Articles & Prepositions",
    "voice_speech_connectors": "Voice, Speech & Connectors",
    "vocabulary_usage": "Vocabulary & Collocations",
    "sentence_syntax": "Sentence Correction & Syntax",
    "topic_relevance": "Prompt Relevance (TF-IDF)",
    "coherence_cohesion": "Discourse Coherence",
    "lexical_richness": "Lexical Diversity",
    "grammar_mechanics": "Grammar Mechanics",
    "readability_clarity": "Readability & Structure",
    "analytical_deduction": "Analytical Deduction",
    "inference_evidence": "Contextual Inference & Evidence",
    "vocabulary_in_context": "Vocabulary in Context",
    # Technical, Algorithm & Programming
    "technical_knowledge": "Core Engineering",
    "data_structures": "Data Structures",
    "algorithms": "Algorithm Design",
    "algorithm_understanding": "Algorithm Design",
    "databases_sql": "Databases & SQL",
    "backend_apis": "Backend & Web APIs",
    "language_fundamentals": "Language Fundamentals",
    "system_design": "System Architecture",
    "git_devops": "Git, Testing & DevOps",
    "programming": "Programming Mastery",
    "programming_logic": "Control Flow & Logic",
    "code_output": "Code Tracing",
    "problem_solving": "Problem Solving",
    "debugging": "Debugging & Edge Cases",
    "time_complexity": "Complexity & Big-O",
    "code_quality": "Code Modularity & Style",
    "test_case_correctness": "Test-Case Accuracy",
}


def format_dimension_label(key: str) -> str:
    clean = str(key or "").strip().lower()
    if clean in DIMENSION_LABELS:
        return DIMENSION_LABELS[clean]
    return clean.replace("_", " ").title() or "General Competency"

