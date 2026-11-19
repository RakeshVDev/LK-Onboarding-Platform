from typing import Any

try:
    from services.assessment_intelligence.config import DEFAULT_SCORING_VERSION_TAG
    from services.assessment_intelligence.ml_report_model import predict_report_intelligence
    from services.assessment_intelligence.nlg_report_synthesizer import (
        AntiRepetitionState,
        build_variation_rng,
        synthesize_category_interpretation,
        synthesize_category_recommendation,
        synthesize_deep_analytics_bundle,
        synthesize_development_area,
        synthesize_executive_summary,
        synthesize_strength_bullet,
    )
except Exception:  # pragma: no cover - standalone import fallback
    DEFAULT_SCORING_VERSION_TAG = "v3.0-supervised-ml-nlp"
    predict_report_intelligence = None
    AntiRepetitionState = None
    build_variation_rng = None
    synthesize_category_interpretation = None
    synthesize_category_recommendation = None
    synthesize_deep_analytics_bundle = None
    synthesize_development_area = None
    synthesize_executive_summary = None
    synthesize_strength_bullet = None


CATEGORY_LABELS = {
    # English Grammar Categories
    "english_grammar": "English Grammar & Syntax",
    "subject_verb_agreement": "Subject-Verb Agreement",
    "tenses_and_aspects": "Tenses & Aspects",
    "tenses": "Verb Tenses",
    "articles": "Articles & Determiners",
    "prepositions": "Prepositions & Phrasal Verbs",
    "conjunctions": "Conjunctions & Connectors",
    "voice_and_speech": "Active/Passive Voice & Direct/Indirect Speech",
    "active_passive_voice": "Active & Passive Voice",
    "direct_indirect_speech": "Direct & Reported Speech",
    "sentence_correction": "Sentence Correction & Syntax",
    "error_detection": "Error Detection & Spotting",
    "vocabulary": "Corporate Vocabulary & Usage",
    "synonyms_antonyms": "Synonyms & Antonyms",
    "idioms_collocations": "Idioms & Professional Collocations",
    "reading_comprehension": "Reading Comprehension & Analysis",
    "analytical_deduction": "Analytical Deduction & Evidence",
    "inference_evidence": "Contextual Inference & Evidence",
    "vocabulary_in_context": "Vocabulary in Context",

    # Logical Reasoning Categories
    "logical_reasoning": "Logical Reasoning & Deductive Logic",
    "number_series": "Number Series & Sequences",
    "alphabet_series": "Alphabet Series & Letter Patterns",
    "coding_decoding": "Coding-Decoding & Cipher Logic",
    "blood_relations": "Family Trees & Blood Relations",
    "direction_distance": "Direction & Spatial Distance",
    "pattern_recognition": "Pattern Recognition & Matrices",
    "logical_statements": "Logical Statements, Syllogisms & Assumptions",
    "odd_one_out": "Classification & Odd One Out",
    "analogy": "Analogy & Semantic Relationships",

    # Technical Categories
    "technical": "Core Technical Engineering",
    "technical_knowledge": "Engineering Fundamentals & Architecture",
    "data_structures": "Data Structures & Memory Efficiency",
    "algorithms": "Algorithms & Computational Complexity",
    "python_programming": "Python Programming & Standard Library",
    "javascript_web": "JavaScript, TypeScript & Modern Web",
    "databases_sql": "Databases, Relational Models & SQL",
    "system_design": "System Design & Distributed Systems",
    "git_devops": "Git, CI/CD & DevOps Practices",
    "networking": "Computer Networks & Protocols (HTTP/TCP)",
    "operating_systems": "Operating Systems & Concurrency",

    # Programming Categories
    "programming": "Programming & Software Implementation",
    "programming_logic": "Programming Logic & Control Flow",
    "algorithm_understanding": "Algorithm Design & Analysis",
    "code_output": "Code Output Prediction & Tracing",
    "problem_solving": "Algorithmic Problem Solving",
    "debugging": "Code Debugging & Error Handling",
    "time_complexity": "Time & Space Complexity",

    # Psychometric Categories
    "psychometric": "Behavioral & Cognitive Profile",
    "personality_work_preferences": "Personality & Work Preferences",
    "situational_judgement": "Situational Judgement & Decision Making",
    "emotional_intelligence": "Emotional Intelligence & Empathy",
    "learning_adaptability": "Learning Agility & Adaptability",
    "team_collaboration": "Team Collaboration & Workplace Ethics",
}


CATEGORY_RECOMMENDATIONS = {
    # English Grammar
    "english_grammar": "Review core English grammar principles, sentence structures, and punctuation rules.",
    "subject_verb_agreement": "Focus on subject-verb concord, singular vs. plural collective nouns, and compound subjects.",
    "tenses_and_aspects": "Practise perfect, continuous, and conditional tenses with real-world timeline scenarios.",
    "tenses": "Review past, present, and future continuous and perfect forms.",
    "articles": "Study definite ('the') versus indefinite ('a/an') article placement and zero-article rules.",
    "prepositions": "Practise prepositional phrases and dependent prepositions (e.g., 'proficient in', 'responsible for').",
    "conjunctions": "Work on coordinating and subordinating conjunctions to form well-connected complex sentences.",
    "voice_and_speech": "Convert sentences between active and passive voice and direct to indirect reported speech.",
    "active_passive_voice": "Emphasise active voice for clear, direct corporate communication.",
    "direct_indirect_speech": "Practise shifting pronouns, tense backshifting, and reporting verbs.",
    "sentence_correction": "Solve sentence correction exercises targeting run-ons, comma splices, and dangling modifiers.",
    "error_detection": "Practise identifying grammatical errors in business correspondence and project documentation.",
    "vocabulary": "Expand high-frequency corporate and technical vocabulary through targeted reading and usage.",
    "synonyms_antonyms": "Build vocabulary depth by learning contextual word nuances and collocations.",
    "idioms_collocations": "Review standard professional idioms and common business collocations.",
    "reading_comprehension": "Practise speed reading and contextual inference from engineering and industry passages.",
    "analytical_deduction": "Verify each conclusion strictly against explicit statements inside the provided passage.",
    "inference_evidence": "Distinguish author-supported implications from external assumptions during reading analysis.",
    "vocabulary_in_context": "Determine unfamiliar terms using surrounding sentence logic and tone cues.",

    # Logical Reasoning
    "logical_reasoning": "Solve analytical reasoning problems, logical deductions, and structured case puzzles.",
    "number_series": "Practise recognizing arithmetic, geometric, alternating, and polynomial progression series.",
    "alphabet_series": "Learn position numbering (A=1 to Z=26) and backward mapping to quickly solve letter patterns.",
    "coding_decoding": "Work on shift ciphers, reverse mapping, and substitution algorithms.",
    "blood_relations": "Map relationships systematically using standard family tree diagrams.",
    "direction_distance": "Draw vector paths on compass grids to quickly solve net displacement problems.",
    "pattern_recognition": "Practise matrix completion, rotation, reflection, and sequence extrapolation.",
    "logical_statements": "Study syllogistic deduction rules, Venn diagrams, and validity of assumptions.",
    "odd_one_out": "Identify subtle semantic, mathematical, or structural discrepancies.",
    "analogy": "Analyze precise functional, proportional, and category-based relationships.",

    # Technical
    "technical": "Reinforce core computer science fundamentals, architecture patterns, and software engineering principles.",
    "technical_knowledge": "Deepen understanding of software architectures, client-server models, and design patterns.",
    "data_structures": "Review arrays, linked lists, stacks, queues, hash maps, trees, and graphs with operations costs.",
    "algorithms": "Practise sorting, searching, recursion, dynamic programming, and greedy algorithms.",
    "python_programming": "Study Python data models, list comprehensions, generators, decorators, and OOP paradigms.",
    "javascript_web": "Master ES6+ syntax, asynchronous programming (Promises, async/await), DOM, and API integration.",
    "databases_sql": "Write complex SQL joins, aggregations, subqueries, and study indexing and ACID transactions.",
    "system_design": "Study load balancing, caching strategies, microservices architecture, and database sharding.",
    "git_devops": "Practise Git branching workflows, merge conflict resolution, CI/CD pipelines, and containerization.",
    "networking": "Review OSI model layers, TCP/UDP differences, HTTP/HTTPS status codes, and DNS resolution.",
    "operating_systems": "Study process scheduling, threads, synchronization primitives (mutex/semaphore), and virtual memory.",

    # Programming
    "programming": "Implement hands-on coding problems daily and analyze time and space complexity.",
    "programming_logic": "Practise breaking down complex requirements into clean conditional logic and modular functions.",
    "algorithm_understanding": "Trace algorithm step execution by hand to build intuition for edge cases.",
    "code_output": "Strengthen code tracing skills, variable scoping rules, and operator precedence.",
    "problem_solving": "Participate in competitive programming challenges on LeetCode/HackerRank.",
    "debugging": "Use structured debugging techniques and logging to isolate and fix logic errors.",
    "time_complexity": "Calculate Big-O time and space complexity for iterative and recursive routines.",

    # Psychometric
    "psychometric": "Reflect on workplace behavioral tendencies, collaboration styles, and personal growth goals.",
    "personality_work_preferences": "Identify your preferred working style, communication approach, and collaboration habits.",
    "situational_judgement": "Work through workplace scenarios involving prioritisation, decision-making, and accountability.",
    "emotional_intelligence": "Practise active listening, emotional awareness, constructive communication, and empathy.",
    "learning_adaptability": "Set continuous learning goals, welcome constructive feedback, and adapt to unfamiliar tools.",
    "team_collaboration": "Promote open teamwork, cross-functional empathy, and ethical professional conduct.",
}


def get_report_title(assessment_type: str, template_name: str | None = None) -> str:
    clean_type = (assessment_type or "").lower().strip()
    if clean_type == "english_grammar":
        return "English Grammar Assessment Report"
    if clean_type == "logical_reasoning":
        return "Logical Reasoning Assessment Report"
    if clean_type == "technical":
        return "Technical Assessment Report"
    if clean_type == "programming":
        return "Programming Assessment Report"
    if clean_type == "psychometric":
        return "Psychometric Assessment Report"
    if template_name:
        return f"{template_name} Report"
    return "Assessment Performance Report"


def get_skill_level(assessment_type: str, percentage: float) -> str:
    clean_type = (assessment_type or "").lower().strip()

    if clean_type == "english_grammar":
        if percentage >= 85:
            return "Advanced / Professional Working Proficiency (C2)"
        if percentage >= 70:
            return "Proficient / Effective Operational Proficiency (C1/B2)"
        if percentage >= 50:
            return "Intermediate / Working Knowledge (B1)"
        return "Foundational / Needs Language Reinforcement"

    if clean_type in {"technical", "programming"}:
        if percentage >= 85:
            return "Advanced Engineering Competency"
        if percentage >= 70:
            return "Proficient / Production Ready"
        if percentage >= 50:
            return "Intermediate / Developing Developer"
        return "Novice / Foundational Fundamentals Needed"

    if clean_type == "logical_reasoning":
        if percentage >= 85:
            return "Exceptional Analytical & Deductive Aptitude"
        if percentage >= 70:
            return "Strong Problem Solving & Critical Reasoning"
        if percentage >= 50:
            return "Moderate Logical Reasoning Capability"
        return "Developing / Foundational Practice Required"

    # Default / Psychometric
    if percentage >= 85:
        return "High Readiness & Alignment"
    if percentage >= 70:
        return "Strong Professional Readiness"
    if percentage >= 50:
        return "Moderate Alignment & Adaptability"
    return "Developing Core Attributes"


def generate_assessment_report(
    category_scores: list[dict[str, Any]],
    assessment_type: str = "psychometric",
    template_name: str | None = None,
    total_questions: int | None = None,
    correct_count: int | None = None,
    incorrect_count: int | None = None,
    unattempted_count: int | None = None,
    time_taken_seconds: int | None = None,
    tab_switch_count: int | None = 0,
    session_id: int | None = None,
    learner_user_id: int | None = None,
    prior_report_texts: list[str] | None = None,
) -> dict:
    """Generate an assessment-specific performance and diagnostic report.

    Computes accurate totals, domain-tailored summaries, category interpretations,
    strengths, development areas, and actionable recommendations.
    Never uses psychological/personality wording on technical, grammar, or logical assessments.
    """
    if not category_scores:
        raise ValueError("At least one category score is required to generate the report")

    clean_type = (assessment_type or "psychometric").lower().strip()
    report_title = get_report_title(clean_type, template_name)

    total_score = 0.0
    total_max_score = 0.0

    strengths: list[str] = []
    development_areas: list[str] = []
    recommendations: list[str] = []
    category_interpretations: dict[str, str] = {}
    normalized_scores: list[dict[str, Any]] = []

    for item in category_scores:
        category = item["category"]
        score = float(item["score"])
        max_score = float(item["max_score"])

        if max_score <= 0:
            raise ValueError(f"Invalid maximum score for category '{category}'")

        if score < 0 or score > max_score:
            raise ValueError(f"Invalid score ({score}) for category '{category}' with max {max_score}")

        percentage = round(score / max_score * 100, 2)

        normalized_scores.append({
            "category": category,
            "score": round(score, 2),
            "max_score": round(max_score, 2),
            "percentage": percentage,
        })

        total_score += score
        total_max_score += max_score

        label = CATEGORY_LABELS.get(category, category.replace("_", " ").title())

        # Generate domain-appropriate interpretation
        if clean_type == "english_grammar":
            if percentage >= 80:
                interpretation = f"High proficiency in {label}. Accurate syntax, correct usage, and consistent sentence mechanics."
            elif percentage >= 60:
                interpretation = f"Solid functional understanding of {label}. Minor inconsistencies under timed constraints."
            elif percentage >= 40:
                interpretation = f"Basic grasp of {label}. Demonstrates errors in complex sentences or ambiguous contexts."
            else:
                interpretation = f"{label} is a key priority for improvement. Focus on core grammar rules and practice exercises."

        elif clean_type in {"technical", "programming"}:
            if percentage >= 80:
                interpretation = f"Demonstrates strong technical mastery in {label}. Solid conceptual depth and problem-solving execution."
            elif percentage >= 60:
                interpretation = f"Good foundational understanding of {label}. Could benefit from deeper practice with edge cases and optimization."
            elif percentage >= 40:
                interpretation = f"Moderate grasp of {label}. Requires targeted study of core fundamentals and practical coding/querying."
            else:
                interpretation = f"{label} requires foundational technical study. Recommended for curriculum refresher modules."

        elif clean_type == "logical_reasoning":
            if percentage >= 80:
                interpretation = f"Excellent deductive accuracy and speed in {label}. Rapid pattern recognition and structured reasoning."
            elif percentage >= 60:
                interpretation = f"Good analytical capability in {label}. Consistent performance with standard logical patterns."
            elif percentage >= 40:
                interpretation = f"Moderate reasoning in {label}. Inconsistencies observed in multi-step deductive sequences."
            else:
                interpretation = f"{label} is a priority area. Focus on structured problem breakdown and pattern recognition practice."

        else:  # psychometric
            if percentage >= 80:
                interpretation = f"Strong indicator for {label}. Demonstrates highly effective behavioral and cognitive attributes."
            elif percentage >= 60:
                interpretation = f"Developing well in {label}. Consistent practice can help strengthen this capability."
            elif percentage >= 40:
                interpretation = f"Further development in {label} may be beneficial. Practise relevant skills through structured activities."
            else:
                interpretation = f"{label} is an area for further practice. Start with guided activities and self-reflection."

        category_interpretations[category] = interpretation

        # Strengths & Development Areas
        if percentage >= 70:
            strengths.append(f"{label}: {percentage}% — strong performance demonstrated in this evaluation.")
        elif percentage < 50:
            development_areas.append(f"{label}: {percentage}% — priority area recommended for structured review.")
            rec = CATEGORY_RECOMMENDATIONS.get(
                category,
                f"Review {label} fundamentals through practice modules and analyze missed questions."
            )
            if rec not in recommendations:
                recommendations.append(rec)

    overall_percentage = round((total_score / total_max_score * 100), 2) if total_max_score > 0 else 0.0
    skill_level = get_skill_level(clean_type, overall_percentage)

    # Domain-specific executive summary
    if clean_type == "english_grammar":
        if overall_percentage >= 80:
            summary = (
                "Your English Grammar assessment demonstrates superior verbal proficiency, correct syntactic construction, "
                "and strong professional communication accuracy suitable for client-facing and engineering documentation."
            )
        elif overall_percentage >= 60:
            summary = (
                "Your assessment indicates competent language skills with good overall comprehension. "
                "Refining subtle grammar rules, verb tenses, and complex sentence mechanics will elevate your writing to an executive standard."
            )
        elif overall_percentage >= 40:
            summary = (
                "Your assessment shows opportunities for grammatical improvement. Focused practice in sentence correction, "
                "subject-verb agreement, and prepositional usage is recommended to ensure clear corporate communication."
            )
        else:
            summary = (
                "Your assessment indicates foundational language support is needed. Regular practice with core English grammar "
                "rules, error spotting, and professional vocabulary modules is strongly advised."
            )

    elif clean_type in {"technical", "programming"}:
        if overall_percentage >= 80:
            summary = (
                "Your technical assessment demonstrates excellent engineering fundamentals, clear understanding of core architectural "
                "principles, and robust problem-solving ability across the evaluated domains."
            )
        elif overall_percentage >= 60:
            summary = (
                "Your assessment reflects a solid technical foundation. Strengthening practical concepts in databases, algorithms, "
                "and modern system architecture will accelerate your development velocity."
            )
        elif overall_percentage >= 40:
            summary = (
                "Your assessment indicates several technical knowledge gaps across core topics. A structured review of data structures, "
                "database queries, and web fundamentals is recommended before taking on complex projects."
            )
        else:
            summary = (
                "Foundational engineering revision is required. We recommend revisiting core computer science principles, practical coding exercises, "
                "and guided technical training modules."
            )

    elif clean_type == "logical_reasoning":
        if overall_percentage >= 80:
            summary = (
                "Exceptional logical reasoning performance. Demonstrates sharp analytical skills, rapid pattern decoding, "
                "and high cognitive problem-solving agility under timed conditions."
            )
        elif overall_percentage >= 60:
            summary = (
                "Strong analytical capability. Good overall accuracy in solving sequential, relational, and deductive puzzles, "
                "with minor room for speed and pattern optimization."
            )
        elif overall_percentage >= 40:
            summary = (
                "Moderate performance in logical reasoning. Solving structured pattern sets, series sequences, and relational diagrams "
                "will help increase your analytical consistency."
            )
        else:
            summary = (
                "Logical reasoning practice is recommended. Working through step-by-step logic puzzles and series deduction exercises "
                "will build confidence and analytical speed."
            )

    else:  # psychometric
        if overall_percentage >= 80:
            summary = (
                "Your assessment shows strong overall behavioral alignment and readiness. Continue developing your capabilities "
                "through practical workplace collaboration and continuous learning."
            )
        elif overall_percentage >= 60:
            summary = (
                "Your assessment shows a developing behavioral profile. Build on your stronger areas and practise the dimensions "
                "that benefit from further personal reflection."
            )
        elif overall_percentage >= 40:
            summary = (
                "Your assessment indicates opportunities for growth across several dimensions. Structured mentoring and guided exercises "
                "can help strengthen your workplace adaptability."
            )
        else:
            summary = (
                "Your assessment indicates that foundational developmental practice would be beneficial. Focus on self-awareness, "
                "communication exercises, and constructive feedback."
            )

    if not strengths:
        strengths.append(f"Demonstrated consistent commitment across all {len(category_scores)} assessment sections.")

    if not development_areas:
        development_areas.append("Demonstrated well-balanced competency across all evaluated categories; maintain continuous learning.")

    if not recommendations:
        if clean_type == "english_grammar":
            recommendations.append("Read high-standard technical documentation and corporate publications to maintain language sharpness.")
        elif clean_type in {"technical", "programming"}:
            recommendations.append("Continue building end-to-end projects and reviewing modern software engineering best practices.")
        elif clean_type == "logical_reasoning":
            recommendations.append("Continue solving challenging analytical problem sets to preserve logical acuity.")
        else:
            recommendations.append("Maintain a proactive learning routine and seek continuous 360 feedback from peers and mentors.")

    # Format human-readable time taken if available
    time_taken_str = None
    if time_taken_seconds is not None and time_taken_seconds >= 0:
        mins = time_taken_seconds // 60
        secs = time_taken_seconds % 60
        time_taken_str = f"{mins} min{'s' if mins != 1 else ''} {secs} sec{'s' if secs != 1 else ''}"

    ml_dimensions = [
        {
            "dimension_key": str(cs.get("category", "general")),
            "dimension_label": CATEGORY_LABELS.get(
                str(cs.get("category", "")),
                str(cs.get("category", "General")).replace("_", " ").title(),
            ),
            "normalized_score": float(cs.get("percentage", overall_percentage)),
        }
        for cs in normalized_scores
    ]
    q_total = total_questions if total_questions is not None else int(total_max_score or 0)
    ans_count = (q_total - int(unattempted_count or 0)) if (q_total and unattempted_count is not None) else q_total
    ans_ratio = (float(ans_count) / float(q_total)) if q_total else 1.0

    ml_insights = (
        predict_report_intelligence(
            assessment_type=clean_type,
            overall_pct=float(overall_percentage),
            weighted_pct=float(overall_percentage),
            dimensions=ml_dimensions,
            domain_analysis=None,
            time_taken_seconds=time_taken_seconds,
            expected_duration_minutes=20,
            tab_switch_count=int(tab_switch_count or 0),
            answered_ratio=ans_ratio,
            prior_report_texts=prior_report_texts,
            session_id=session_id,
            learner_user_id=learner_user_id,
        )
        if predict_report_intelligence is not None
        else None
    )

    nlg_meta: dict[str, Any] = {}
    if synthesize_executive_summary is not None and AntiRepetitionState is not None and build_variation_rng is not None:
        rng, variation_seed = build_variation_rng(
            assessment_type=clean_type,
            overall_pct=float(overall_percentage),
            session_id=session_id,
            learner_user_id=learner_user_id,
            variation_salt=f"base:{len(normalized_scores)}:{q_total}",
        )
        nlg_state = AntiRepetitionState(prior_report_texts=prior_report_texts)
        sorted_ml_dims = sorted(ml_dimensions, key=lambda d: d["normalized_score"], reverse=True)
        top_key = sorted_ml_dims[0]["dimension_key"] if sorted_ml_dims else None
        weak_key = sorted_ml_dims[-1]["dimension_key"] if sorted_ml_dims else None
        time_ratio = (
            min(2.0, float(time_taken_seconds) / (20.0 * 60.0))
            if time_taken_seconds is not None and time_taken_seconds >= 0
            else 0.72
        )
        uplift_pts = float((ml_insights or {}).get("estimated_uplift_points", 10.0))

        category_interpretations = {}
        strengths = []
        development_areas = []
        recommendations = []

        for cs in normalized_scores:
            cat = cs["category"]
            pct = float(cs["percentage"])
            lbl = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
            band = "Exceptional" if pct >= 85 else ("Proficient" if pct >= 70 else ("Developing" if pct >= 50 else "Foundational"))
            category_interpretations[cat] = synthesize_category_interpretation(
                clean_type=clean_type,
                dim_key=cat,
                dim_label=lbl,
                pct=pct,
                state=nlg_state,
                rng=rng,
                is_top=(cat == top_key),
                is_weakest=(cat == weak_key),
            )
            if pct >= 70.0:
                strengths.append(
                    synthesize_strength_bullet(
                        clean_type=clean_type,
                        dim_label=lbl,
                        score_pct=pct,
                        percentile_band=band,
                        cohort_avg=None,
                        state=nlg_state,
                        rng=rng,
                    )
                )
            elif pct < 50.0:
                development_areas.append(
                    synthesize_development_area(
                        clean_type=clean_type,
                        dim_label=lbl,
                        score_pct=pct,
                        percentile_band=band,
                        cohort_avg=None,
                        state=nlg_state,
                        rng=rng,
                    )
                )
                recommendations.append(
                    synthesize_category_recommendation(
                        clean_type=clean_type,
                        category_key=cat,
                        dim_label=lbl,
                        score_pct=pct,
                        hard_easy_gap=0.0,
                        time_ratio=time_ratio,
                        uplift_pts=uplift_pts,
                        state=nlg_state,
                        rng=rng,
                        priority_rank=len(recommendations) + 1,
                    )
                )

        if not strengths:
            strengths.append(
                nlg_state.pick_best(
                    [
                        f"Completed every evaluated section across all {len(normalized_scores)} categories consistently.",
                        f"Demonstrated steady participation across all {len(normalized_scores)} tracked assessment sections.",
                    ],
                    rng=rng,
                )
            )
        if not development_areas:
            development_areas.append(
                nlg_state.pick_best(
                    [
                        "No critical sub-skill gaps detected; continue sharpening depth through higher-difficulty scenarios.",
                        "Well-balanced score distribution across categories — focus on speed optimization and complex cases.",
                    ],
                    rng=rng,
                )
            )
        if not recommendations:
            weakest_dim = sorted_ml_dims[-1] if sorted_ml_dims else None
            if weakest_dim and weakest_dim["normalized_score"] < 75.0:
                recommendations.append(
                    synthesize_category_recommendation(
                        clean_type=clean_type,
                        category_key=weakest_dim["dimension_key"],
                        dim_label=weakest_dim["dimension_label"],
                        score_pct=float(weakest_dim["normalized_score"]),
                        hard_easy_gap=0.0,
                        time_ratio=time_ratio,
                        uplift_pts=uplift_pts,
                        state=nlg_state,
                        rng=rng,
                        priority_rank=1,
                    )
                )
            else:
                recommendations.append(
                    nlg_state.pick_best(
                        [
                            "Advance to higher-complexity problem sets paired with regular peer and mentor feedback.",
                            "Challenge strong proficiency through timed stretch scenarios and structured design reviews.",
                        ],
                        rng=rng,
                    )
                )

        if ml_insights:
            for ml_rec in ml_insights.get("ml_recommendations") or []:
                covered = {lbl.split(":")[0].lower() for lbl in development_areas}
                if not any(part in ml_rec.lower() for part in covered) and ml_rec not in recommendations:
                    recommendations.append(ml_rec)
                    nlg_state.register(ml_rec)

        summary = synthesize_executive_summary(
            clean_type=clean_type,
            template_name=template_name,
            overall_pct=float(overall_percentage),
            weighted_pct=float(overall_percentage),
            skill_level=skill_level,
            dimensions=ml_dimensions,
            domain_analysis={},
            ml_insights=ml_insights or {},
            cohort_averages=None,
            total_q=q_total,
            state=nlg_state,
            rng=rng,
        )
        nlg_meta = {"variation_seed": variation_seed, **nlg_state.uniqueness_stats()}
    elif ml_insights:
        for ml_rec in ml_insights.get("ml_recommendations") or []:
            if ml_rec not in recommendations:
                recommendations.append(ml_rec)
        if clean_type == "psychometric":
            summary = (
                f"{summary} Supervised developmental pattern: {ml_insights['diagnostic_pattern_label']} "
                f"(Readiness Index {ml_insights['ml_mastery_index']:.1f}/100, {ml_insights['predicted_tier_label']})."
            )
        else:
            summary = (
                f"{summary} Supervised ML profile: {ml_insights['diagnostic_pattern_label']} "
                f"(Mastery Index {ml_insights['ml_mastery_index']:.1f}/100, tier: {ml_insights['predicted_tier_label']})."
            )

    focus_areas_out: list[str] = list((ml_insights or {}).get("development_focus_areas") or [])
    for area in development_areas:
        if area not in focus_areas_out and len(focus_areas_out) < 5:
            focus_areas_out.append(area)

    deep_analytics = (
        synthesize_deep_analytics_bundle(
            clean_type=clean_type,
            overall_pct=float(overall_percentage),
            weighted_pct=float(overall_percentage),
            dimensions=ml_dimensions,
            domain_analysis={},
            ml_insights=ml_insights,
            total_questions=int(q_total or 0),
            correct_answers=int(correct_count or 0),
            incorrect_answers=int(incorrect_count or 0),
            unattempted_questions=int(unattempted_count or 0),
            time_taken_seconds=time_taken_seconds,
            expected_duration_minutes=20,
            session_id=session_id,
            learner_user_id=learner_user_id,
        )
        if synthesize_deep_analytics_bundle is not None
        else {}
    )

    report_data = {
        "report_title": report_title,
        "assessment_type": clean_type,
        "template_name": template_name or report_title.replace(" Report", ""),
        "skill_level": skill_level,
        "summary": summary,
        "strengths": strengths,
        "development_areas": development_areas,
        "recommendations": recommendations,
        "category_interpretations": category_interpretations,
        "overall_percentage": overall_percentage,
        "weighted_percentage": overall_percentage,
        "total_score": round(total_score, 2),
        "max_score": round(total_max_score, 2),
        "category_scores": normalized_scores,
        "total_questions": total_questions if total_questions is not None else int(total_max_score),
        "correct_answers": correct_count,
        "incorrect_answers": incorrect_count,
        "unattempted_questions": unattempted_count,
        "time_taken_seconds": time_taken_seconds,
        "time_taken_str": time_taken_str,
        "tab_switch_count": int(tab_switch_count or 0),
        "proctoring_status": "Clean" if not tab_switch_count else ("Warning Issued" if tab_switch_count < 3 else "Terminated (Limit Reached)"),
        "ml_insights": ml_insights,
        "deep_analytics": deep_analytics,
        "nlg_metadata": nlg_meta,
        "intelligence": {
            "scoring_version": DEFAULT_SCORING_VERSION_TAG,
            "weighted_percentage": overall_percentage,
            "ml_insights": ml_insights,
            "deep_analytics": deep_analytics,
            "development_focus_areas": focus_areas_out,
            "role_readiness_fit": (ml_insights or {}).get("role_readiness_fit") or [],
            "nlg_metadata": nlg_meta,
        },
    }

    report_lines = [
        f"============================================================",
        f"  {report_title.upper()}",
        f"============================================================",
        f"Candidate Assessment Type: {clean_type.replace('_', ' ').title()}",
        f"Overall Score:            {total_score:.2f} / {total_max_score:.2f} ({overall_percentage:.1f}%)",
        f"Skill / Performance Level: {skill_level}",
    ]

    if total_questions is not None:
        report_lines.append(f"Total Questions:           {total_questions}")
    if correct_count is not None:
        report_lines.append(f"Correct Answers:           {correct_count}")
    if incorrect_count is not None:
        report_lines.append(f"Incorrect Answers:         {incorrect_count}")
    if unattempted_count is not None:
        report_lines.append(f"Unattempted:               {unattempted_count}")
    if time_taken_str is not None:
        report_lines.append(f"Time Taken:                {time_taken_str}")

    if ml_insights:
        report_lines.extend([
            f"Readiness Tier:           {ml_insights['predicted_tier_label']} ({ml_insights['readiness_confidence'] * 100:.0f}% confidence)",
            f"Mastery Index:            {ml_insights['ml_mastery_index']:.1f} / 100 (Est. Uplift +{ml_insights['estimated_uplift_points']:.1f} pts)",
        ])

    report_lines.extend([
        "",
        "EXECUTIVE SUMMARY:",
        summary,
        "",
        *(
            [
                "DIAGNOSTIC INSIGHT:",
                f"  • Pattern: {ml_insights['diagnostic_pattern_label']}",
                *[f"  • Fit:     {fit}" for fit in (ml_insights.get("role_readiness_fit") or [])],
                "",
            ]
            if ml_insights
            else []
        ),
        "CATEGORY BREAKDOWN & INTERPRETATIONS:",
    ])

    for category, interp in category_interpretations.items():
        lbl = CATEGORY_LABELS.get(category, category.replace("_", " ").title())
        report_lines.append(f"  • {lbl}: {interp}")

    report_lines.extend([
        "",
        "STRENGTHS:",
        *[f"  + {item}" for item in strengths],
        "",
        "AREAS FOR IMPROVEMENT:",
        *[f"  - {item}" for item in development_areas],
        "",
        "RECOMMENDATIONS:",
        *[f"  → {item}" for item in recommendations],
        "",
    ])

    if clean_type == "psychometric":
        report_lines.append("Note: This report provides developmental feedback. It is not a clinical diagnosis or an employment-suitability decision.")
    else:
        report_lines.append(f"Note: This official {report_title} certifies candidate proficiency demonstrated during the timed ASE Assessment Tool examination.")

    return {
        "report_data": report_data,
        "report_text": "\n".join(report_lines),
        "ai_model": f"{clean_type}-supervised-ml-v3",
    }
