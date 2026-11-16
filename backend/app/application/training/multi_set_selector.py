"""Multi-Set Question Provider (Set A, Set B, Set C) & Comprehension Passages.

Provides 3 distinct, non-overlapping question sets per core assessment category
(psychometric, cognitive, logical_reasoning, programming, and comprehension)
to prevent candidate collusion while staying 100% deterministic and offline.
"""

from __future__ import annotations

from typing import Any

VALID_SETS = ("A", "B", "C")


def normalize_question_set(raw_set: str | None) -> str:
    val = str(raw_set or "A").strip().upper()
    if val.startswith("SET"):
        val = val.replace("SET", "").strip(" _:-")
    return val if val in VALID_SETS else "A"


def assign_question_set_for_candidate(
    *,
    template_id: int,
    learner_user_id: int,
    configured_set: str | None = None,
    existing_session_count: int = 0,
) -> str:
    """Assigns Set A, B, or C; rotates fairly across candidates unless admin pinned a specific set."""
    cfg = str(configured_set or "").strip().upper()
    if cfg in VALID_SETS:
        return cfg
    idx = (int(template_id) * 7 + int(learner_user_id) * 13 + int(existing_session_count)) % len(VALID_SETS)
    return VALID_SETS[idx]


def build_numeric_scoring_key(
    options: list[dict[str, str]],
    correct_ids: list[str],
    max_score: float = 1.0,
) -> dict[str, float]:
    """Maps every option letter to a numeric score compatible with assessment_scoring.py."""
    correct_set = {str(cid).strip().upper() for cid in correct_ids if str(cid).strip()}
    if not options:
        return {}
    return {
        str(opt["id"]).strip().upper(): (
            float(max_score) if str(opt["id"]).strip().upper() in correct_set else 0.0
        )
        for opt in options
        if opt.get("id")
    }


def _mcq(
    *,
    q_set: str,
    category: str,
    difficulty: str,
    text: str,
    options: list[str],
    answer: str,
    explanation: str = "",
    passage_text: str | None = None,
) -> dict[str, Any]:
    opt_dicts = [{"id": key, "text": opt} for key, opt in zip("ABCD", options)]
    return {
        "question_set": q_set,
        "category": category,
        "difficulty": difficulty,
        "question_type": "multiple_choice",
        "question_text": text,
        "passage_text": passage_text,
        "instructions": "Read carefully and select the best answer." if not passage_text else "Answer strictly based on the reading passage provided.",
        "explanation": explanation,
        "options": opt_dicts,
        "scoring_key": build_numeric_scoring_key(opt_dicts, [answer.upper()], 1.0),
        "max_score": 1.0,
        "negative_marks": 0.0,
    }


def _likert(
    *,
    q_set: str,
    category: str,
    text: str,
    options: list[str],
    scores: dict[str, int] | None = None,
) -> dict[str, Any]:
    return {
        "question_set": q_set,
        "category": category,
        "difficulty": "Medium",
        "question_type": "single_choice",
        "question_text": text,
        "instructions": "Select the option that most accurately reflects your workplace behavior.",
        "options": [{"id": key, "text": opt} for key, opt in zip("ABCD", options)],
        "scoring_key": scores or {"A": 4, "B": 3, "C": 2, "D": 1},
        "max_score": 4.0,
        "negative_marks": 0.0,
    }


# ---------------------------------------------------------------------------
# READING COMPREHENSION PASSAGES (Sets A, B, C)
# ---------------------------------------------------------------------------

BUILTIN_COMPREHENSION_PASSAGES: dict[str, dict[str, str]] = {
    "A": {
        "title": "Idempotency & Resilience in Distributed API Gateways",
        "passage": (
            "Modern enterprise platforms rely heavily on asynchronous message queues and distributed "
            "microservices to process millions of concurrent transactions without blocking client requests. "
            "In high-throughput networks, transient packet drops and gateway timeouts frequently cause clients "
            "or intermediate proxies to retry identical write operations. Without idempotency keys, a retried "
            "payment or enrolment mutation can accidentally create duplicate ledger records or double-bill customers.\n\n"
            "To mitigate this risk safely, platform engineers attach a deterministic UUID idempotency token "
            "to each state-mutating request. When the API gateway receives a retry bearing an already-recorded token "
            "within a bounded time-to-live (TTL) window, it short-circuits downstream execution and replays the "
            "stored canonical response. Crucially, idempotency does not eliminate the need for circuit breakers: "
            "while idempotency guarantees exactly-once observable state mutations, circuit breakers protect failing "
            "downstream databases from cascading retry storms by tripping open once error thresholds exceed configured tolerances."
        ),
    },
    "B": {
        "title": "Zero-Trust Identity Boundaries & Principle of Least Privilege",
        "passage": (
            "Traditional perimeter security assumed that every service operating inside a corporate virtual "
            "private network could be trusted implicitly. However, as cloud deployments spanned multiple regions "
            "and hybrid identity providers, lateral movement after a single compromised container became a primary "
            "incident vector. Zero-Trust Architecture eliminates implicit network trust by authenticating and "
            "authorizing every internal service-to-service and user-to-resource request independently.\n\n"
            "Within a Zero-Trust onboarding system, role-based access control (RBAC) is paired with attribute "
            "checks such as approved department membership and verification state. Even if a newly hired candidate "
            "holds a valid session token, authorization checks reject cross-department reads because identity "
            "authentication merely proves who the caller is, whereas policy enforcement determines what resources "
            "the caller is permitted to touch at that exact stage of their lifecycle."
        ),
    },
    "C": {
        "title": "Structured Telemetry, Post-Incident Reviews & Blameless Engineering Culture",
        "passage": (
            "High-reliability software organizations distinguish sharply between surface symptoms and systemic "
            "root causes during production outages. Latency spikes reported by customer dashboards are often merely "
            "downstream indicators of thread-pool exhaustion or lock contention triggered by an unindexed database migration. "
            "Correlating structured JSON logs, distributed trace spans, and golden latency percentiles allows teams "
            "to pinpoint failing code paths within minutes instead of guessing across services.\n\n"
            "Equally important is how teams conduct post-incident reviews. Research across DevOps cohorts demonstrates "
            "that blameless retrospectives yield significantly richer remediation plans than punitive audits. When "
            "engineers do not fear personal reprimand for honest human mistakes, they disclose near-misses transparently "
            "and convert individual errors into automated safeguards—such as pre-merge migration checks and circuit alerts."
        ),
    },
}


def _build_comprehension_sets() -> dict[str, list[dict[str, Any]]]:
    p_a = BUILTIN_COMPREHENSION_PASSAGES["A"]["passage"]
    p_b = BUILTIN_COMPREHENSION_PASSAGES["B"]["passage"]
    p_c = BUILTIN_COMPREHENSION_PASSAGES["C"]["passage"]
    return {
        "A": [
            _mcq(
                q_set="A",
                category="reading_comprehension",
                difficulty="Easy",
                passage_text=p_a,
                text="According to the passage, what primarily triggers duplicate ledger records when retrying requests?",
                options=[
                    "Overly long database TTL indexes",
                    "Missing idempotency keys during network retries",
                    "Blocking synchronous client threads",
                    "Excessive UUID generation overhead",
                ],
                answer="B",
                explanation="The passage states retried mutations without idempotency keys cause duplicate ledger records.",
            ),
            _mcq(
                q_set="A",
                category="analytical_deduction",
                difficulty="Medium",
                passage_text=p_a,
                text="How does the API gateway respond to a repeated request arriving inside the configured TTL window?",
                options=[
                    "It rejects the caller with a 503 timeout error",
                    "It deletes the first ledger transaction before running again",
                    "It skips downstream execution and returns the cached canonical response",
                    "It generates a new random UUID token automatically",
                ],
                answer="C",
                explanation="The gateway short-circuits downstream execution and replays the stored canonical response.",
            ),
            _mcq(
                q_set="A",
                category="inference_evidence",
                difficulty="Medium",
                passage_text=p_a,
                text="Why does the author emphasize pairing circuit breakers with idempotency keys?",
                options=[
                    "Because circuit breakers generate UUIDs faster",
                    "Because idempotency prevents duplicate mutations but does not stop retry storms hitting struggling databases",
                    "Because circuit breakers eliminate the need for TTL storage",
                    "Because asynchronous queues cannot operate without HTTP 200 codes",
                ],
                answer="B",
                explanation="Idempotency prevents duplicate mutations; circuit breakers prevent cascading retry overload.",
            ),
            _mcq(
                q_set="A",
                category="vocabulary_in_context",
                difficulty="Medium",
                passage_text=p_a,
                text="In the context of the passage, 'short-circuits' most nearly means:",
                options=[
                    "Causes an electrical hardware failure",
                    "Bypasses redundant processing steps cleanly",
                    "Terminates active user sessions",
                    "Compresses payload headers before transmission",
                ],
                answer="B",
                explanation="Here short-circuiting means bypassing redundant downstream execution by returning stored output.",
            ),
            _mcq(
                q_set="A",
                category="analytical_deduction",
                difficulty="Hard",
                passage_text=p_a,
                text="Which condition MUST hold for a client to safely experience exactly-once mutation semantics?",
                options=[
                    "Sending the same deterministic idempotency token within the TTL window",
                    "Changing the UUID token on every HTTP retry",
                    "Disabling circuit breakers until the queue drains",
                    "Routing writes through unauthenticated proxies",
                ],
                answer="A",
                explanation="Retrying requires the same deterministic UUID idempotency token within the TTL window.",
            ),
        ],
        "B": [
            _mcq(
                q_set="B",
                category="reading_comprehension",
                difficulty="Easy",
                passage_text=p_b,
                text="What flaw in traditional perimeter security prompted organizations to adopt Zero-Trust Architecture?",
                options=[
                    "Virtual private networks could not encrypt TLS traffic",
                    "Implicit trust inside the internal network enabled lateral movement once one container was breached",
                    "Session tokens expired too slowly across single-region hosts",
                    "RBAC policies refused all internal calls",
                ],
                answer="B",
                explanation="Compromising one internal container allowed lateral movement under implicit network trust.",
            ),
            _mcq(
                q_set="B",
                category="analytical_deduction",
                difficulty="Medium",
                passage_text=p_b,
                text="According to the passage, why might a request with a valid session token still be denied?",
                options=[
                    "Because the caller's lifecycle attributes or department permissions forbid access to that resource",
                    "Because Zero-Trust disables JSON Web Tokens entirely",
                    "Because containers cannot verify region metadata",
                    "Because internal requests bypass authentication altogether",
                ],
                answer="A",
                explanation="Authentication proves identity, while attribute/RBAC policy enforcement governs access rights.",
            ),
            _mcq(
                q_set="B",
                category="inference_evidence",
                difficulty="Medium",
                passage_text=p_b,
                text="Which distinction best summarizes the closing sentence of the passage?",
                options=[
                    "Speed vs. availability",
                    "Authentication (who you are) vs. authorization (what you may access)",
                    "Encryption at rest vs. compression in transit",
                    "Multi-region replication vs. manual failover",
                ],
                answer="B",
                explanation="Identity authentication proves who the caller is; policy enforcement determines permitted actions.",
            ),
            _mcq(
                q_set="B",
                category="vocabulary_in_context",
                difficulty="Medium",
                passage_text=p_b,
                text="What does 'implicitly' mean in the first sentence?",
                options=[
                    "Explicitly logged on disk",
                    "Automatically assumed without continuous verification",
                    "Cryptographically signed with RSA",
                    "Temporarily revoked after login",
                ],
                answer="B",
                explanation="'Trusted implicitly' contrasts with Zero-Trust's requirement for independent per-request verification.",
            ),
            _mcq(
                q_set="B",
                category="analytical_deduction",
                difficulty="Hard",
                passage_text=p_b,
                text="Under Zero-Trust onboarding rules described here, when may a learner read Department B materials?",
                options=[
                    "As soon as they sign in from the corporate VPN",
                    "Never, unless policy attributes explicitly verify membership/approval for Department B",
                    "Whenever their password hash matches",
                    "During off-peak deployment windows",
                ],
                answer="B",
                explanation="Attribute checks such as approved department membership enforce strict isolation.",
            ),
        ],
        "C": [
            _mcq(
                q_set="C",
                category="reading_comprehension",
                difficulty="Easy",
                passage_text=p_c,
                text="What concrete database issue does the passage cite as a possible underlying cause of latency spikes?",
                options=[
                    "Over-compressed JSON log exports",
                    "Unindexed database migration triggering lock contention",
                    "Excessive golden latency alerts",
                    "Frequent blameless retrospective meetings",
                ],
                answer="B",
                explanation="The passage mentions lock contention or thread-pool exhaustion from an unindexed database migration.",
            ),
            _mcq(
                q_set="C",
                category="analytical_deduction",
                difficulty="Medium",
                passage_text=p_c,
                text="Why do blameless retrospectives lead to stronger system reliability than punitive audits?",
                options=[
                    "They remove the need to inspect distributed traces",
                    "Engineers openly share near-misses, enabling teams to build automated guardrails",
                    "Managers resolve database locks manually during meetings",
                    "Teams eliminate all human deployments altogether",
                ],
                answer="B",
                explanation="Psychological safety encourages honest disclosure and turns mistakes into automated safeguards.",
            ),
            _mcq(
                q_set="C",
                category="inference_evidence",
                difficulty="Medium",
                passage_text=p_c,
                text="Which trio of telemetry signals does the author connect to rapid root-cause isolation?",
                options=[
                    "Structured logs, distributed trace spans, and latency percentiles",
                    "Manual SSH checks, email threads, and CPU temperature",
                    "Annual surveys, code formatting rules, and billing alerts",
                    "Unit coverage reports, favicon assets, and DNS leases",
                ],
                answer="A",
                explanation="The first paragraph highlights correlating structured JSON logs, trace spans, and golden percentiles.",
            ),
            _mcq(
                q_set="C",
                category="vocabulary_in_context",
                difficulty="Medium",
                passage_text=p_c,
                text="As used in paragraph two, 'remediation plans' refers to:",
                options=[
                    "Employee disciplinary contracts",
                    "Actionable corrective measures that prevent recurring failures",
                    "Marketing announcements after downtime",
                    "Hardware deprecation budgets",
                ],
                answer="B",
                explanation="Remediation plans transform disclosed failure modes into concrete engineering fixes and checks.",
            ),
            _mcq(
                q_set="C",
                category="analytical_deduction",
                difficulty="Hard",
                passage_text=p_c,
                text="What would contradict the passage's recommended engineering practice?",
                options=[
                    "Adding an automated schema lint check in CI after a bad migration",
                    "Penalizing an engineer who reported a staging configuration near-miss",
                    "Tracing slow API latency down to a specific lock-contended SQL statement",
                    "Attaching request correlation IDs across microservice hops",
                ],
                answer="B",
                explanation="Punishing disclosed mistakes runs directly counter to blameless retrospective findings.",
            ),
        ],
    }


def _build_cognitive_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "A": [
            _mcq(
                q_set="A", category="logical_deduction", difficulty="Easy",
                text="All cloud architects understand networking. Priya is a cloud architect. Which conclusion must be true?",
                options=["Priya manages billing only", "Priya understands networking", "No developers understand networking", "Networking requires zero protocols"],
                answer="B", explanation="Universal affirmative deduction applies directly to Priya.",
            ),
            _mcq(
                q_set="A", category="numerical_reasoning", difficulty="Medium",
                text="A server processes 240 requests per minute. After a 25% throughput optimization, how many requests can it process in 5 minutes?",
                options=["1,200", "1,400", "1,500", "1,650"],
                answer="C", explanation="240 * 1.25 = 300 req/min; over 5 minutes = 1,500 requests.",
            ),
            _mcq(
                q_set="A", category="pattern_analysis", difficulty="Medium",
                text="Complete the alphanumeric matrix sequence: B2, E5, I9, N14, ?",
                options=["S19", "T20", "U21", "R18"],
                answer="B", explanation="Letter index & number both grow by +3, +4, +5, +6 -> 14 + 6 = 20 (T20).",
            ),
            _mcq(
                q_set="A", category="critical_thinking", difficulty="Hard",
                text="After shifting sprint reviews to Thursday, defect leakage fell by 18%. What assumption would WEAKEN claiming the day change caused the drop?",
                options=[
                    "Automated integration tests were deployed into CI the same week",
                    "Team members preferred Thursday afternoons",
                    "Product owners attended every review",
                    "Story point velocity remained stable",
                ],
                answer="A", explanation="An automated CI test suite introduces a clear confounding cause.",
            ),
            _mcq(
                q_set="A", category="abstract_reasoning", difficulty="Medium",
                text="Mirror : Reflection :: Filter : ?",
                options=["Opacity", "Refinement", "Distortion", "Friction"],
                answer="B", explanation="A mirror produces a reflection; a filter produces refinement/purification.",
            ),
        ],
        "B": [
            _mcq(
                q_set="B", category="logical_deduction", difficulty="Easy",
                text="No staging builds are deployed directly to production without QA sign-off. Release 4.2 reached production. Therefore:",
                options=["Release 4.2 bypassed staging rules without QA", "If Release 4.2 came from staging, it received QA sign-off", "QA sign-off guarantees zero bugs", "All releases happen weekly"],
                answer="B", explanation="By contrapositive consistency with staging policy, QA sign-off occurred if sourced from staging.",
            ),
            _mcq(
                q_set="B", category="numerical_reasoning", difficulty="Medium",
                text="If 6 engineers complete a migration in 14 hours at equal pace, how many hours will 8 engineers require for an identical migration?",
                options=["9.5 hours", "10.5 hours", "11.0 hours", "12.0 hours"],
                answer="B", explanation="Total work = 6 * 14 = 84 engineer-hours; 84 / 8 = 10.5 hours.",
            ),
            _mcq(
                q_set="B", category="pattern_analysis", difficulty="Medium",
                text="Identify the next term in the sequence: 4, 9, 19, 39, 79, ?",
                options=["149", "158", "159", "169"],
                answer="C", explanation="Each term doubles the previous and adds 1: 79 * 2 + 1 = 159.",
            ),
            _mcq(
                q_set="B", category="critical_thinking", difficulty="Hard",
                text="A portal reports 99.9% uptime yet customer complaints spiked. Which metric best explains the discrepancy?",
                options=[
                    "Health check endpoints stayed 200 OK while login checkout endpoints timed out",
                    "CPU temperature remained 48°C",
                    "Database backups ran on Sundays",
                    "Static CSS assets used browser caching",
                ],
                answer="A", explanation="Synthetic health probes passing do not guarantee critical user journeys succeeded.",
            ),
            _mcq(
                q_set="B", category="abstract_reasoning", difficulty="Medium",
                text="Compass : Navigation :: Blueprint : ?",
                options=["Concrete", "Architecture", "Paint", "Excavation"],
                answer="B", explanation="A compass guides navigation; a blueprint guides architectural construction.",
            ),
        ],
        "C": [
            _mcq(
                q_set="C", category="logical_deduction", difficulty="Easy",
                text="Either the webhook failed OR the subscriber queue was full. Monitoring confirms the queue had 80% free capacity. What must be true?",
                options=["The queue dropped the packet randomly", "The webhook failed", "Both guarantees succeeded", "Traffic exceeded disk limits"],
                answer="B", explanation="Disjunctive syllogism: A or B, not B => A.",
            ),
            _mcq(
                q_set="C", category="numerical_reasoning", difficulty="Medium",
                text="An API response drops from 320 ms to 200 ms after query indexing. What is the percentage reduction in latency?",
                options=["32.5%", "37.5%", "40.0%", "60.0%"],
                answer="B", explanation="(320 - 200) / 320 = 120 / 320 = 37.5%.",
            ),
            _mcq(
                q_set="C", category="pattern_analysis", difficulty="Medium",
                text="Find the missing value: 11, 13, 17, 25, 41, ?",
                options=["65", "69", "73", "77"],
                answer="C", explanation="Differences double: +2, +4, +8, +16, +32 -> 41 + 32 = 73.",
            ),
            _mcq(
                q_set="C", category="critical_thinking", difficulty="Hard",
                text="A training cohort scored 15% higher after adding pair programming. What control check best isolates the effect of pair programming?",
                options=[
                    "Comparing against a parallel cohort covering the same syllabus individually",
                    "Changing assessment difficulty for the second group",
                    "Measuring typing speed in words per minute",
                    "Deploying a new office theme",
                ],
                answer="A", explanation="An equivalent control cohort isolates the instructional intervention.",
            ),
            _mcq(
                q_set="C", category="abstract_reasoning", difficulty="Medium",
                text="Anchor : Stability :: Beacon : ?",
                options=["Darkness", "Guidance", "Harbor", "Tide"],
                answer="B", explanation="An anchor provides stability; a beacon provides guidance.",
            ),
        ],
    }


def _build_programming_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "A": [
            _mcq(
                q_set="A", category="time_complexity", difficulty="Easy",
                text="What is the worst-case time complexity of binary search on a sorted array of n elements?",
                options=["O(1)", "O(log n)", "O(n)", "O(n log n)"],
                answer="B", explanation="Each comparison halves the remaining search interval.",
            ),
            _mcq(
                q_set="A", category="code_output", difficulty="Medium",
                text="What is the output of Python: nums = [1, 2, 3]; print([x * x for x in nums if x % 2 == 1])?",
                options=["[1, 4, 9]", "[1, 9]", "[4]", "[1, 3]"],
                answer="B", explanation="Odd elements 1 and 3 are squared -> [1, 9].",
            ),
            _mcq(
                q_set="A", category="data_structures", difficulty="Medium",
                text="Which data structure provides O(1) average lookup AND preserves insertion order in Python 3.7+?",
                options=["set", "dict", "heapq", "tuple"],
                answer="B", explanation="Python dicts offer hash-table O(1) average lookup and guaranteed insertion order.",
            ),
            _mcq(
                q_set="A", category="debugging", difficulty="Medium",
                text="In FastAPI/SQLAlchemy, what causes stale reads or 'DetachedInstanceError' after closing a DB session?",
                options=[
                    "Using async routes without uvicorn",
                    "Accessing unloaded lazy relationships after the Session closes",
                    "Missing CORS middleware headers",
                    "Returning Pydantic dicts instead of tuples",
                ],
                answer="B", explanation="Lazy attributes require an active session unless eagerly loaded or detached safely.",
            ),
            _mcq(
                q_set="A", category="databases_sql", difficulty="Hard",
                text="Which SQL clause filters groups AFTER aggregation (`COUNT`, `AVG`) has been computed?",
                options=["WHERE", "HAVING", "DISTINCT", "ORDER BY"],
                answer="B", explanation="WHERE filters raw rows before grouping; HAVING filters aggregated groups.",
            ),
        ],
        "B": [
            _mcq(
                q_set="B", category="time_complexity", difficulty="Medium",
                text="What is the average-case time complexity of Merge Sort on an unsorted array of size n?",
                options=["O(n)", "O(log n)", "O(n log n)", "O(n^2)"],
                answer="C", explanation="Merge Sort recursively divides in log n levels with O(n) merging per level.",
            ),
            _mcq(
                q_set="B", category="code_output", difficulty="Medium",
                text="In JavaScript/TypeScript, what does `typeof null` evaluate to?",
                options=["'null'", "'undefined'", "'object'", "'boolean'"],
                answer="C", explanation="For historical language compatibility, `typeof null` returns `'object'`.",
            ),
            _mcq(
                q_set="B", category="data_structures", difficulty="Easy",
                text="Which traversal visits nodes level by level using a FIFO queue?",
                options=["Depth-First Search (DFS)", "Breadth-First Search (BFS)", "Post-order Traversal", "Topological Backtracking"],
                answer="B", explanation="BFS explores neighbors layer-by-layer using a queue.",
            ),
            _mcq(
                q_set="B", category="debugging", difficulty="Medium",
                text="Why does `SELECT * FROM users WHERE email = NULL` fail to match NULL rows in standard SQL?",
                options=[
                    "NULL requires `IS NULL` because any equality check `= NULL` evaluates to UNKNOWN",
                    "VARCHAR columns cannot store NULL",
                    "Indexes block NULL comparisons",
                    "SQL turns NULL into empty string automatically",
                ],
                answer="A", explanation="Three-valued logic evaluates `= NULL` to UNKNOWN; always use `IS NULL`.",
            ),
            _mcq(
                q_set="B", category="algorithms", difficulty="Hard",
                text="Which algorithm finds shortest weighted paths in a graph with only non-negative edge weights?",
                options=["Dijkstra's Algorithm", "Kruskal's MST", "QuickSelect", "Rabin-Karp"],
                answer="A", explanation="Dijkstra computes single-source shortest paths efficiently when edge weights >= 0.",
            ),
        ],
        "C": [
            _mcq(
                q_set="C", category="time_complexity", difficulty="Medium",
                text="What is the space complexity of recursive Depth-First Search on a balanced binary tree of n nodes?",
                options=["O(1)", "O(log n)", "O(n^2)", "O(2^n)"],
                answer="B", explanation="Call stack depth equals tree height, which is O(log n) for balanced trees.",
            ),
            _mcq(
                q_set="C", category="code_output", difficulty="Medium",
                text="In Python, what happens when a function uses a mutable default argument `def add(item, bucket=[]):`?",
                options=[
                    "A fresh list is allocated per call",
                    "The single list instance is shared across successive calls omitting `bucket`",
                    "Python raises TypeError at definition time",
                    "Lists become immutable tuples automatically",
                ],
                answer="B", explanation="Default argument objects are evaluated once when the function is defined.",
            ),
            _mcq(
                q_set="C", category="data_structures", difficulty="Medium",
                text="Which structure best implements an Undo history stack where the most recent action reverses first?",
                options=["LIFO Stack", "Min-Heap", "Circular Ring Buffer only", "Adjacency Matrix"],
                answer="A", explanation="Undo operations follow Last-In-First-Out (LIFO) ordering.",
            ),
            _mcq(
                q_set="C", category="debugging", difficulty="Hard",
                text="What is an N+1 query problem in ORM-backed REST APIs?",
                options=[
                    "Deploying one extra database replica in staging",
                    "Executing 1 query for parent rows plus N separate lazy queries for each child record",
                    "Sorting results by descending primary keys",
                    "Returning HTTP 201 instead of 200",
                ],
                answer="B", explanation="N+1 queries serialize round-trips per item; resolve via joinedload/selectinload.",
            ),
            _mcq(
                q_set="C", category="problem_solving", difficulty="Medium",
                text="How can you detect a cycle in a singly linked list in O(1) extra memory?",
                options=[
                    "Store every visited node pointer in a HashSet",
                    "Use Floyd's slow (1 step) and fast (2 steps) pointers",
                    "Sort node values in place",
                    "Reverse the entire list twice",
                ],
                answer="B", explanation="Floyd's tortoise-and-hare pointers detect cycles using O(1) auxiliary space.",
            ),
        ],
    }


def _build_logical_extra_sets() -> dict[str, list[dict[str, Any]]]:
    """Distinct Set B & Set C logical reasoning questions (Set A delegates to baseline 25)."""
    return {
        "B": [
            _mcq(q_set="B", category="number_series", difficulty="Easy", text="Find the next number: 7, 14, 28, 56, ?", options=["98", "112", "114", "126"], answer="B", explanation="Multiply by 2 each step -> 56 * 2 = 112."),
            _mcq(q_set="B", category="number_series", difficulty="Medium", text="Find the missing term: 1, 4, 9, 16, 25, ?, 49", options=["32", "35", "36", "40"], answer="C", explanation="Perfect squares: 6^2 = 36."),
            _mcq(q_set="B", category="alphabet_series", difficulty="Medium", text="Complete the pattern: ACE, FHJ, KMO, ?", options=["PRT", "PQS", "OQS", "QSU"], answer="A", explanation="Each letter shifts +5 from the prior group: K+5=P, M+5=R, O+5=T."),
            _mcq(q_set="B", category="coding_decoding", difficulty="Medium", text="If CODE is written as DPEF (+1 shift), how is LOGIC written?", options=["MPHJD", "MPHJE", "NQIKF", "KNFHB"], answer="A", explanation="Shifting L-O-G-I-C by +1 yields M-P-H-J-D."),
            _mcq(q_set="B", category="blood_relations", difficulty="Medium", text="Ananya is the sister of Vikram. Vikram is the father of Riya. How is Ananya related to Riya?", options=["Mother", "Cousin", "Aunt", "Grandmother"], answer="C", explanation="Father's sister is aunt."),
            _mcq(q_set="B", category="direction_distance", difficulty="Medium", text="Karan walks 6 km North, then turns East and walks 8 km. What is his shortest distance from the start?", options=["10 km", "12 km", "14 km", "9 km"], answer="A", explanation="Right triangle legs 6 and 8 give hypotenuse 10 km."),
            _mcq(q_set="B", category="logical_statements", difficulty="Hard", text="Some engineers are designers. All designers are creative. Which conclusion MUST follow?", options=["All engineers are creative", "Some engineers are creative", "No designer is an engineer", "Only designers are creative"], answer="B", explanation="The engineers who are designers must be creative."),
            _mcq(q_set="B", category="odd_one_out", difficulty="Easy", text="Select the odd one out: Python, Java, FastAPI, C++", options=["Python", "Java", "FastAPI", "C++"], answer="C", explanation="FastAPI is a web framework; the others are programming languages."),
            _mcq(q_set="B", category="analogy", difficulty="Easy", text="Compiler : Executable :: Blueprint : ?", options=["Building", "Hammer", "Inspector", "Permit"], answer="A", explanation="A compiler produces an executable; a blueprint guides constructing a building."),
            _mcq(q_set="B", category="pattern_recognition", difficulty="Medium", text="Find next number: 100, 95, 85, 70, 50, ?", options=["30", "25", "20", "35"], answer="B", explanation="Subtract -5, -10, -15, -20, -25 -> 50 - 25 = 25."),
        ],
        "C": [
            _mcq(q_set="C", category="number_series", difficulty="Easy", text="Find the next number: 3, 9, 27, 81, ?", options=["162", "216", "243", "324"], answer="C", explanation="Powers of 3 -> 81 * 3 = 243."),
            _mcq(q_set="C", category="number_series", difficulty="Medium", text="Complete: 8, 12, 18, 26, 36, ?", options=["44", "46", "48", "52"], answer="C", explanation="Differences increase by +2: +4, +6, +8, +10, +12 -> 36 + 12 = 48."),
            _mcq(q_set="C", category="alphabet_series", difficulty="Medium", text="Complete the sequence: Z, X, U, Q, L, ?", options=["G", "F", "E", "H"], answer="B", explanation="Backward gaps: -2, -3, -4, -5, -6 -> L(12) - 6 = F(6)."),
            _mcq(q_set="C", category="coding_decoding", difficulty="Medium", text="If TEST is coded as 20-5-19-20, what is API coded as?", options=["1-16-9", "2-15-9", "1-15-8", "3-16-10"], answer="A", explanation="A=1, P=16, I=9."),
            _mcq(q_set="C", category="blood_relations", difficulty="Medium", text="Meera points to a photo and says, 'He is the only son of my mother's father.' Who is in the photo?", options=["Meera's cousin", "Meera's maternal uncle", "Meera's brother", "Meera's nephew"], answer="B", explanation="Mother's father's only son is maternal uncle."),
            _mcq(q_set="C", category="direction_distance", difficulty="Medium", text="Sneha faces South, turns 90° clockwise, then turns 180°. Which direction does she face now?", options=["North", "East", "West", "South"], answer="B", explanation="South -> clockwise 90° = West -> +180° = East."),
            _mcq(q_set="C", category="logical_statements", difficulty="Hard", text="No outdated APIs are secure. Some REST endpoints are outdated APIs. What follows?", options=["All REST endpoints are insecure", "Some REST endpoints are not secure", "All secure APIs are REST", "No conclusion possible"], answer="B", explanation="Those REST endpoints that are outdated cannot be secure."),
            _mcq(q_set="C", category="odd_one_out", difficulty="Easy", text="Choose the odd one out: PostgreSQL, SQLite, Angular, MSSQL", options=["PostgreSQL", "SQLite", "Angular", "MSSQL"], answer="C", explanation="Angular is a frontend UI framework; the others are relational databases."),
            _mcq(q_set="C", category="analogy", difficulty="Easy", text="Latency : Speed :: Memory Leak : ?", options=["Bandwidth", "Stability", "Throughput", "Encryption"], answer="B", explanation="Latency degrades speed; memory leaks degrade system stability."),
            _mcq(q_set="C", category="pattern_recognition", difficulty="Medium", text="Complete: 2, 5, 11, 23, 47, ?", options=["91", "93", "95", "99"], answer="C", explanation="Multiply by 2 and add 1: 47 * 2 + 1 = 95."),
        ],
    }


def _build_psychometric_extra_sets() -> dict[str, list[dict[str, Any]]]:
    opts_collab = [
        "Collaborate closely with stakeholders and align priorities transparently.",
        "Balance independent execution with scheduled peer check-ins.",
        "Complete drafts solo first and share near final delivery.",
        "Defer alignment until formal escalation.",
    ]
    return {
        "B": [
            _likert(q_set="B", category="personality_work_preferences", text="When onboarding onto an unfamiliar codebase, how do you ramp up fastest?", options=["Pair with mentors and document architecture notes systematically", "Read specs thoroughly and ask targeted clarifying questions", "Experiment independently before checking team conventions", "Wait until someone assigns step-by-step tickets"]),
            _likert(q_set="B", category="situational_judgement", text="A teammate introduces an edge-case regression right before release freeze. What is your immediate move?", options=["Constructively share reproduction steps and pair on a minimal fix", "Document the regression clearly in the release tracker", "Roll back quietly without notifying the author", "Ignore it until the next sprint"]),
            _likert(q_set="B", category="emotional_intelligence", text="During a heated architecture debate, two peers talk over each other. How do you respond?", options=["Summarize both technical positions neutrally and refocus on trade-offs", "Ask clarifying questions to surface shared constraints", "Stay silent until voting begins", "Declare one side wrong immediately"]),
            _likert(q_set="B", category="learning_adaptability", text="Your department adopts a new framework halfway through a project. How do you react?", options=["Build a small proof-of-concept and share takeaways with the team", "Follow official docs steadily during designated hours", "Express hesitation until templates are prepared", "Avoid the updated modules entirely"]),
            _likert(q_set="B", category="team_collaboration", text="How do you ensure remote team members stay equally informed on decisions?", options=opts_collab),
        ],
        "C": [
            _likert(q_set="C", category="personality_work_preferences", text="When managing three overlapping deadlines, how do you structure execution?", options=["Break milestones into measurable deliverables and flag blockers early", "Prioritize highest-impact tasks first with daily checkpoints", "Work strictly chronologically on incoming messages", "Switch tasks ad-hoc whenever pinged"]),
            _likert(q_set="C", category="situational_judgement", text="You spot ambiguous requirements in a compliance specification before sprint kickoff. What do you do?", options=["Draft concrete edge cases and confirm sign-off with the product owner", "Flag the ambiguity during daily standup", "Assume the simplest interpretation and proceed", "Leave the requirement unimplemented until QA flags it"]),
            _likert(q_set="C", category="emotional_intelligence", text="A junior colleague appears overwhelmed after receiving extensive PR feedback. How do you help?", options=["Walk through high-priority items constructively and recognize what worked well", "Offer quick pointers on key improvements asynchronously", "Send links to generic style manuals without context", "Rewrite the entire PR yourself without explaining why"]),
            _likert(q_set="C", category="learning_adaptability", text="After receiving critical coaching on presentation clarity, what is your next step?", options=["Rework slide flow and request a dry-run review with a peer", "Apply key bullet changes before the next meeting", "Stick mostly to your original script", "Stop volunteering for demos"]),
            _likert(q_set="C", category="team_collaboration", text="When a cross-functional handoff stalls between backend and QA, how do you intervene?", options=opts_collab),
        ],
    }


def get_comprehension_default_questions(question_set: str | None = None) -> list[dict[str, Any]]:
    sets = _build_comprehension_sets()
    if question_set:
        norm = normalize_question_set(question_set)
        return list(sets.get(norm, sets["A"]))
    return sets["A"] + sets["B"] + sets["C"]


def get_multi_set_questions(
    assessment_type: str,
    question_set: str = "A",
) -> list[dict[str, Any]]:
    """Returns distinct builtin question pool for `(assessment_type, question_set in A/B/C)`."""
    q_set = normalize_question_set(question_set)
    domain = (assessment_type or "psychometric").lower().strip()

    if domain == "comprehension":
        return get_comprehension_default_questions(q_set)

    if domain == "cognitive":
        cog = _build_cognitive_sets()
        # Combine cognitive pool with matching logical reasoning extras if more questions needed
        base = list(cog.get(q_set, cog["A"]))
        if q_set in {"B", "C"}:
            base.extend(_build_logical_extra_sets()[q_set])
        return base

    if domain in {"programming", "technical", "algorithm"}:
        prog = _build_programming_sets()
        return list(prog.get(q_set, prog["A"]))

    if domain == "logical_reasoning" and q_set in {"B", "C"}:
        extra = _build_logical_extra_sets()[q_set]
        cog = _build_cognitive_sets()[q_set]
        return extra + cog

    if domain == "psychometric" and q_set in {"B", "C"}:
        return _build_psychometric_extra_sets()[q_set]

    return []
