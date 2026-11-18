"""Multi-Set Question Provider (Set A, Set B, Set C) & Comprehension Passages.

Provides at least 3 distinct, non-overlapping question sets (Set A, Set B, Set C)
for ALL 9 assessment categories:
  1. logical_reasoning (25 Qs per set)
  2. english_grammar   (20 Qs per set)
  3. technical         (20 Qs per set)
  4. psychometric      (20 Qs per set)
  5. programming       (20 Qs per set)
  6. cognitive         (25 Qs per set)
  7. composition       (20 Qs per set)
  8. algorithm         (20 Qs per set)
  9. comprehension     (10 Qs + distinct passage per set)

100% deterministic, offline, and zero overlap across Set A, Set B, and Set C.
"""

from __future__ import annotations

from typing import Any

VALID_SETS = ("A", "B", "C")

ALL_ASSESSMENT_CATEGORIES = (
    "logical_reasoning",
    "english_grammar",
    "technical",
    "psychometric",
    "programming",
    "cognitive",
    "composition",
    "algorithm",
    "comprehension",
)


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


def _tag_set(questions: list[dict[str, Any]], q_set: str) -> list[dict[str, Any]]:
    tagged: list[dict[str, Any]] = []
    for item in questions:
        copied = dict(item)
        copied["question_set"] = q_set
        tagged.append(copied)
    return tagged


# ---------------------------------------------------------------------------
# 1. READING COMPREHENSION PASSAGES & 3 SETS (10 Qs each)
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
            _mcq(q_set="A", category="reading_comprehension", difficulty="Easy", passage_text=p_a,
                 text="According to the passage, what primarily triggers duplicate ledger records when retrying requests?",
                 options=["Overly long database TTL indexes", "Missing idempotency keys during network retries", "Blocking synchronous client threads", "Excessive UUID generation overhead"],
                 answer="B", explanation="Retried mutations without idempotency keys create duplicate ledger records."),
            _mcq(q_set="A", category="analytical_deduction", difficulty="Medium", passage_text=p_a,
                 text="How does the API gateway respond to a repeated request arriving inside the configured TTL window?",
                 options=["It rejects the caller with a 503 timeout error", "It deletes the first ledger transaction before running again", "It skips downstream execution and returns the cached canonical response", "It generates a new random UUID token automatically"],
                 answer="C", explanation="The gateway short-circuits downstream execution and replays the stored canonical response."),
            _mcq(q_set="A", category="inference_evidence", difficulty="Medium", passage_text=p_a,
                 text="Why does the author emphasize pairing circuit breakers with idempotency keys?",
                 options=["Because circuit breakers generate UUIDs faster", "Because idempotency prevents duplicate mutations but does not stop retry storms hitting struggling databases", "Because circuit breakers eliminate the need for TTL storage", "Because asynchronous queues cannot operate without HTTP 200 codes"],
                 answer="B", explanation="Idempotency prevents duplicate writes; circuit breakers protect failing downstream databases."),
            _mcq(q_set="A", category="vocabulary_in_context", difficulty="Medium", passage_text=p_a,
                 text="In the context of the passage, 'short-circuits' most nearly means:",
                 options=["Causes an electrical hardware failure", "Bypasses redundant processing steps cleanly", "Terminates active user sessions", "Compresses payload headers before transmission"],
                 answer="B", explanation="Short-circuiting bypasses redundant downstream execution by returning stored output."),
            _mcq(q_set="A", category="analytical_deduction", difficulty="Hard", passage_text=p_a,
                 text="Which condition MUST hold for a client to safely experience exactly-once mutation semantics?",
                 options=["Sending the same deterministic idempotency token within the TTL window", "Changing the UUID token on every HTTP retry", "Disabling circuit breakers until the queue drains", "Routing writes through unauthenticated proxies"],
                 answer="A", explanation="Retries must reuse the same deterministic idempotency token within the TTL window."),
            _mcq(q_set="A", category="reading_comprehension", difficulty="Easy", passage_text=p_a,
                 text="Why do enterprise platforms adopt asynchronous message queues according to paragraph one?",
                 options=["To process high concurrent transaction volume without blocking clients", "To eliminate network packets completely", "To remove all API gateways from architecture", "To delay billing intentionally"],
                 answer="A", explanation="Asynchronous queues allow millions of concurrent transactions without blocking client requests."),
            _mcq(q_set="A", category="inference_evidence", difficulty="Medium", passage_text=p_a,
                 text="When does a circuit breaker trip open as described in the passage?",
                 options=["Whenever a single client retries once", "Once error thresholds surpass configured tolerances", "After every successful cached replay", "Whenever TTL expires cleanly"],
                 answer="B", explanation="Circuit breakers trip open once error thresholds exceed configured tolerances."),
            _mcq(q_set="A", category="vocabulary_in_context", difficulty="Easy", passage_text=p_a,
                 text="What does 'transient' most nearly mean in 'transient packet drops'?",
                 options=["Permanent and irreversible", "Temporary and short-lived", "Encrypted end-to-end", "Manually scheduled"],
                 answer="B", explanation="Transient refers to brief, temporary network glitches."),
            _mcq(q_set="A", category="analytical_deduction", difficulty="Hard", passage_text=p_a,
                 text="What risk arises if a client retries a write request AFTER the gateway's idempotency TTL window has expired?",
                 options=["The gateway may no longer recognize the token and could re-execute the mutation", "The circuit breaker permanently locks the database", "The client automatically receives a 401 unauthorized response", "The message queue deletes historical ledger backups"],
                 answer="A", explanation="Deduplication is guaranteed only within the bounded TTL window."),
            _mcq(q_set="A", category="inference_evidence", difficulty="Medium", passage_text=p_a,
                 text="Which pair of terms best captures the dual resilience model outlined in the passage?",
                 options=["State safety (idempotency) and overload protection (circuit breakers)", "Password hashing and browser caching", "Load balancing and DNS prefetching", "Schema migration and static compilation"],
                 answer="A", explanation="Idempotency ensures safe state mutations; circuit breakers prevent cascading overload."),
        ],
        "B": [
            _mcq(q_set="B", category="reading_comprehension", difficulty="Easy", passage_text=p_b,
                 text="What flaw in traditional perimeter security prompted organizations to adopt Zero-Trust Architecture?",
                 options=["Virtual private networks could not encrypt TLS traffic", "Implicit trust inside the internal network enabled lateral movement once one container was breached", "Session tokens expired too slowly across single-region hosts", "RBAC policies refused all internal calls"],
                 answer="B", explanation="Implicit internal trust enabled lateral movement after one container compromise."),
            _mcq(q_set="B", category="analytical_deduction", difficulty="Medium", passage_text=p_b,
                 text="According to the passage, why might a request with a valid session token still be denied?",
                 options=["Because the caller's lifecycle attributes or department permissions forbid access to that resource", "Because Zero-Trust disables JSON Web Tokens entirely", "Because containers cannot verify region metadata", "Because internal requests bypass authentication altogether"],
                 answer="A", explanation="Authentication proves identity, while RBAC and attribute enforcement govern access."),
            _mcq(q_set="B", category="inference_evidence", difficulty="Medium", passage_text=p_b,
                 text="Which distinction best summarizes the closing sentence of the passage?",
                 options=["Speed vs. availability", "Authentication (who you are) vs. authorization (what you may access)", "Encryption at rest vs. compression in transit", "Multi-region replication vs. manual failover"],
                 answer="B", explanation="Authentication proves who the caller is; policy enforcement determines permitted resources."),
            _mcq(q_set="B", category="vocabulary_in_context", difficulty="Medium", passage_text=p_b,
                 text="What does 'implicitly' mean in the first sentence?",
                 options=["Explicitly logged on disk", "Automatically assumed without continuous verification", "Cryptographically signed with RSA", "Temporarily revoked after login"],
                 answer="B", explanation="Implicit trust is assumed automatically without per-request verification."),
            _mcq(q_set="B", category="analytical_deduction", difficulty="Hard", passage_text=p_b,
                 text="Under Zero-Trust onboarding rules described here, when may a learner read Department B materials?",
                 options=["As soon as they sign in from the corporate VPN", "Never, unless policy attributes explicitly verify membership/approval for Department B", "Whenever their password hash matches", "During off-peak deployment windows"],
                 answer="B", explanation="Attribute checks such as approved department membership enforce strict isolation."),
            _mcq(q_set="B", category="reading_comprehension", difficulty="Easy", passage_text=p_b,
                 text="How does Zero-Trust handle internal service-to-service traffic?",
                 options=["It authenticates and authorizes every request independently", "It allows unrestricted access inside the VPC", "It routes all traffic through public browsers", "It disables role checks for microservices"],
                 answer="A", explanation="Zero-Trust authenticates and authorizes every service-to-service and user-to-resource call."),
            _mcq(q_set="B", category="inference_evidence", difficulty="Medium", passage_text=p_b,
                 text="Which lifecycle attributes are cited alongside RBAC in the onboarding system example?",
                 options=["Approved department membership and verification state", "Monitor resolution and browser language", "CPU core count and IP subnet length", "Employee tenure and office floor"],
                 answer="A", explanation="The passage names approved department membership and verification state."),
            _mcq(q_set="B", category="vocabulary_in_context", difficulty="Easy", passage_text=p_b,
                 text="In cloud security context, 'lateral movement' refers to:",
                 options=["Migrating a website color palette", "An attacker pivoting from one compromised host to other internal systems", "Horizontally scaling stateless frontend pods", "Exporting audit logs to cold storage"],
                 answer="B", explanation="Lateral movement means spreading across internal systems after an initial breach."),
            _mcq(q_set="B", category="analytical_deduction", difficulty="Medium", passage_text=p_b,
                 text="Why did multi-region cloud deployments accelerate the shift away from perimeter-only security?",
                 options=["Traditional network perimeters blurred across regions and hybrid identity providers", "Cloud providers banned HTTPS certificates", "Single-region servers refused container workloads", "VPN software stopped supporting RBAC"],
                 answer="A", explanation="Multi-region and hybrid identity environments rendered implicit network perimeters fragile."),
            _mcq(q_set="B", category="inference_evidence", difficulty="Hard", passage_text=p_b,
                 text="Which practice directly VIOLATES the Zero-Trust model described in the passage?",
                 options=["Allowing any pod on the internal subnet to query payroll tables without authorization tokens", "Enforcing department approval before serving department course files", "Validating caller roles on every API endpoint", "Checking lifecycle state before unlocking onboarding modules"],
                 answer="A", explanation="Trusting internal network location alone violates Zero-Trust principles."),
        ],
        "C": [
            _mcq(q_set="C", category="reading_comprehension", difficulty="Easy", passage_text=p_c,
                 text="What concrete database issue does the passage cite as a possible underlying cause of latency spikes?",
                 options=["Over-compressed JSON log exports", "Unindexed database migration triggering lock contention", "Excessive golden latency alerts", "Frequent blameless retrospective meetings"],
                 answer="B", explanation="An unindexed database migration can trigger lock contention or thread-pool exhaustion."),
            _mcq(q_set="C", category="analytical_deduction", difficulty="Medium", passage_text=p_c,
                 text="Why do blameless retrospectives lead to stronger system reliability than punitive audits?",
                 options=["They remove the need to inspect distributed traces", "Engineers openly share near-misses, enabling teams to build automated guardrails", "Managers resolve database locks manually during meetings", "Teams eliminate all human deployments altogether"],
                 answer="B", explanation="Psychological safety encourages honest disclosure and turns errors into automated checks."),
            _mcq(q_set="C", category="inference_evidence", difficulty="Medium", passage_text=p_c,
                 text="Which trio of telemetry signals does the author connect to rapid root-cause isolation?",
                 options=["Structured logs, distributed trace spans, and latency percentiles", "Manual SSH checks, email threads, and CPU temperature", "Annual surveys, code formatting rules, and billing alerts", "Unit coverage reports, favicon assets, and DNS leases"],
                 answer="A", explanation="Correlating structured JSON logs, trace spans, and golden latency percentiles isolates failures."),
            _mcq(q_set="C", category="vocabulary_in_context", difficulty="Medium", passage_text=p_c,
                 text="As used in paragraph two, 'remediation plans' refers to:",
                 options=["Employee disciplinary contracts", "Actionable corrective measures that prevent recurring failures", "Marketing announcements after downtime", "Hardware deprecation budgets"],
                 answer="B", explanation="Remediation plans convert incident findings into preventative engineering actions."),
            _mcq(q_set="C", category="analytical_deduction", difficulty="Hard", passage_text=p_c,
                 text="What would contradict the passage's recommended engineering practice?",
                 options=["Adding an automated schema lint check in CI after a bad migration", "Penalizing an engineer who reported a staging configuration near-miss", "Tracing slow API latency down to a specific lock-contended SQL statement", "Attaching request correlation IDs across microservice hops"],
                 answer="B", explanation="Penalizing honest disclosure contradicts blameless retrospective culture."),
            _mcq(q_set="C", category="reading_comprehension", difficulty="Easy", passage_text=p_c,
                 text="How does the passage classify latency spikes shown on customer dashboards?",
                 options=["Often surface downstream symptoms rather than the root cause itself", "Always caused by client browser extensions", "Unrelated to database migrations", "Proof of punitive audit policies"],
                 answer="A", explanation="Latency spikes are often downstream indicators of deeper issues like lock contention."),
            _mcq(q_set="C", category="inference_evidence", difficulty="Medium", passage_text=p_c,
                 text="What examples of automated safeguards does the author give at the end of the passage?",
                 options=["Pre-merge migration checks and circuit alerts", "Manual spreadsheet approvals and paper forms", "Removing all JSON logs in production", "Freezing code deployments for six months"],
                 answer="A", explanation="The final sentence highlights pre-merge migration checks and circuit alerts."),
            _mcq(q_set="C", category="vocabulary_in_context", difficulty="Easy", passage_text=p_c,
                 text="In paragraph two, 'near-misses' most closely refers to:",
                 options=["Errors caught before causing full customer-facing outages", "Missed calendar invitations", "Network cables that are slightly too short", "Features delayed to the next quarter"],
                 answer="A", explanation="Near-misses are risky incidents or mistakes caught before escalating into outages."),
            _mcq(q_set="C", category="analytical_deduction", difficulty="Medium", passage_text=p_c,
                 text="Why are structured JSON logs preferable to unstructured guesswork during outages?",
                 options=["They can be systematically correlated with traces and metrics to isolate failing paths rapidly", "They occupy zero bytes on disk", "They eliminate the need for databases", "They hide latency spikes from dashboards"],
                 answer="A", explanation="Structured JSON logs correlate cleanly with trace spans and percentiles."),
            _mcq(q_set="C", category="inference_evidence", difficulty="Hard", passage_text=p_c,
                 text="Which cultural outcome does research across DevOps cohorts link to removing fear of personal reprimand?",
                 options=["Greater transparency and richer preventative engineering outcomes", "Complete elimination of post-incident reviews", "Lower adoption of distributed tracing tools", "Increased reliance on manual audits"],
                 answer="A", explanation="Blameless culture fosters transparency and richer remediation plans."),
        ],
    }


# ---------------------------------------------------------------------------
# 2. COGNITIVE APTITUDE — 3 COMPLETE DISTINCT SETS (25 Qs each)
# ---------------------------------------------------------------------------

def _build_cognitive_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "A": [
            _mcq(q_set="A", category="logical_deduction", difficulty="Easy", text="All cloud architects understand networking. Priya is a cloud architect. Which conclusion must be true?", options=["Priya manages billing only", "Priya understands networking", "No developers understand networking", "Networking requires zero protocols"], answer="B", explanation="Universal affirmative deduction applies directly to Priya."),
            _mcq(q_set="A", category="numerical_reasoning", difficulty="Medium", text="A server processes 240 requests per minute. After a 25% throughput optimization, how many requests can it process in 5 minutes?", options=["1,200", "1,400", "1,500", "1,650"], answer="C", explanation="240 * 1.25 = 300 req/min; over 5 minutes = 1,500."),
            _mcq(q_set="A", category="pattern_analysis", difficulty="Medium", text="Complete the alphanumeric matrix sequence: B2, E5, I9, N14, ?", options=["S19", "T20", "U21", "R18"], answer="B", explanation="Gaps grow +3, +4, +5, +6 -> 14 + 6 = 20 (T20)."),
            _mcq(q_set="A", category="critical_thinking", difficulty="Hard", text="After shifting sprint reviews to Thursday, defect leakage fell by 18%. What assumption would WEAKEN claiming the day change caused the drop?", options=["Automated integration tests were deployed into CI the same week", "Team members preferred Thursday afternoons", "Product owners attended every review", "Story point velocity remained stable"], answer="A", explanation="An automated CI test suite introduces a clear confounding cause."),
            _mcq(q_set="A", category="abstract_reasoning", difficulty="Medium", text="Mirror : Reflection :: Filter : ?", options=["Opacity", "Refinement", "Distortion", "Friction"], answer="B", explanation="A mirror produces a reflection; a filter produces refinement."),
            _mcq(q_set="A", category="logical_deduction", difficulty="Medium", text="Every encrypted backup is stored offsite. Archive X is not stored offsite. What follows necessarily?", options=["Archive X is not an encrypted backup", "Archive X is corrupted", "Archive X is stored on tape", "All offsite files are archives"], answer="A", explanation="Modus tollens: if P -> Q and not Q, then not P."),
            _mcq(q_set="A", category="numerical_reasoning", difficulty="Easy", text="A team spent 18 hours on design and 42 hours on coding. What percentage of total time was spent on design?", options=["25%", "30%", "35%", "40%"], answer="B", explanation="18 / (18 + 42) = 18 / 60 = 30%."),
            _mcq(q_set="A", category="pattern_analysis", difficulty="Medium", text="Identify the next number in the pattern: 6, 11, 21, 36, 56, ?", options=["76", "81", "86", "91"], answer="B", explanation="Differences increase by +5: +5, +10, +15, +20, +25 -> 56 + 25 = 81."),
            _mcq(q_set="A", category="critical_thinking", difficulty="Medium", text="A support team reduced average ticket reply time from 4 hours to 1 hour, yet CSAT dropped. Which factor most logically explains this?", options=["Agents began sending hasty incomplete replies to hit speed targets", "The ticketing portal changed its icon color", "Support shifts started 5 minutes earlier", "Customers received faster accurate solutions"], answer="A", explanation="Optimizing purely for speed can reduce resolution quality."),
            _mcq(q_set="A", category="abstract_reasoning", difficulty="Easy", text="Thermometer : Temperature :: Speedometer : ?", options=["Distance", "Velocity", "Fuel", "Altitude"], answer="B", explanation="A thermometer measures temperature; a speedometer measures velocity."),
            _mcq(q_set="A", category="logical_deduction", difficulty="Hard", text="Only certified engineers can approve production hotfixes. Rohan approved a hotfix. Which statement MUST be true?", options=["Rohan is a certified engineer", "All certified engineers work on hotfixes", "Rohan is the CTO", "No other engineer can review code"], answer="A", explanation="'Only P can Q' means Q -> P; since Rohan did Q, he must be P."),
            _mcq(q_set="A", category="numerical_reasoning", difficulty="Hard", text="Storage usage grows by 20% each month from 500 GB. What is usage after 2 months?", options=["700 GB", "720 GB", "740 GB", "750 GB"], answer="B", explanation="500 * 1.2 = 600; 600 * 1.2 = 720 GB."),
            _mcq(q_set="A", category="pattern_analysis", difficulty="Easy", text="Complete the letter-number sequence: C3, F6, I9, L12, ?", options=["N14", "O15", "P16", "M13"], answer="B", explanation="Each step adds +3 in alphabet and number -> O15."),
            _mcq(q_set="A", category="critical_thinking", difficulty="Medium", text="Before concluding a new UI layout boosted sign-ups by 12%, what must an analyst verify first?", options=["No major marketing campaign launched simultaneously during the test window", "The font size used serif glyphs", "Engineers used dark mode while coding", "The favicon loaded under 20 ms"], answer="A", explanation="Concurrent campaigns confound attribution of conversion gains."),
            _mcq(q_set="A", category="abstract_reasoning", difficulty="Medium", text="Key : Lock :: Token : ?", options=["Session", "Monitor", "Keyboard", "Cable"], answer="A", explanation="A key unlocks a lock; an authentication token grants access to a session."),
            _mcq(q_set="A", category="logical_deduction", difficulty="Medium", text="If Service A crashes, Service B alerts. Service B did NOT alert. What can be deduced?", options=["Service A did not crash", "Service A restarted twice", "Service B is faster than A", "Both services are offline"], answer="A", explanation="Contrapositive of A -> B is not B -> not A."),
            _mcq(q_set="A", category="numerical_reasoning", difficulty="Medium", text="A batch of 45 learners has a 4:5 ratio of frontend to backend tracks. How many are in backend?", options=["20", "25", "27", "30"], answer="B", explanation="5 / (4 + 5) * 45 = 25."),
            _mcq(q_set="A", category="pattern_analysis", difficulty="Hard", text="Find the next term: 1, 3, 7, 15, 31, ?", options=["55", "61", "63", "65"], answer="C", explanation="2^n - 1: 2^6 - 1 = 63."),
            _mcq(q_set="A", category="critical_thinking", difficulty="Hard", text="A study finds teams with more unit tests ship faster. Which statement best cautions against simplistic interpretation?", options=["Strong engineering discipline may independently drive both higher test coverage and faster shipping", "Unit tests never run in CI", "Shipping faster always removes bugs", "Correlation is identical to causation"], answer="A", explanation="A third underlying factor (engineering maturity) can drive both metrics."),
            _mcq(q_set="A", category="abstract_reasoning", difficulty="Medium", text="Sculptor : Marble :: Programmer : ?", options=["Code", "Desk", "Office", "Chair"], answer="A", explanation="A sculptor shapes marble; a programmer shapes code."),
            _mcq(q_set="A", category="logical_deduction", difficulty="Easy", text="Some laptops in the lab run Linux. All Linux machines have Git installed. Which conclusion holds?", options=["Some laptops in the lab have Git installed", "All laptops run Linux", "No laptop runs Windows", "Git only runs on laptops"], answer="A", explanation="The subset of laptops running Linux must have Git installed."),
            _mcq(q_set="A", category="numerical_reasoning", difficulty="Easy", text="An API serves 900 calls in 15 seconds. What is its rate per second?", options=["45", "50", "60", "75"], answer="C", explanation="900 / 15 = 60 calls per second."),
            _mcq(q_set="A", category="pattern_analysis", difficulty="Medium", text="Find the missing value: 120, 60, 30, 15, ?", options=["5", "7.5", "10", "12"], answer="B", explanation="Each term is halved -> 15 / 2 = 7.5."),
            _mcq(q_set="A", category="critical_thinking", difficulty="Easy", text="Which evidence is strongest when prioritizing which bug to fix first?", options=["Production crash telemetry affecting 40% of active users", "A single unverified rumor in chat", "A minor spacing preference on an internal test page", "Personal intuition without logs"], answer="A", explanation="Objective high-impact telemetry provides the strongest prioritization basis."),
            _mcq(q_set="A", category="abstract_reasoning", difficulty="Hard", text="Seed : Forest :: Axiom : ?", options=["Theorem", "Shadow", "Noise", "Friction"], answer="A", explanation="A forest grows from a seed; a system of theorems derives from axioms."),
        ],
        "B": [
            _mcq(q_set="B", category="logical_deduction", difficulty="Easy", text="No staging builds are deployed directly to production without QA sign-off. Release 4.2 reached production. Therefore:", options=["Release 4.2 bypassed staging rules without QA", "If Release 4.2 came from staging, it received QA sign-off", "QA sign-off guarantees zero bugs", "All releases happen weekly"], answer="B", explanation="By contrapositive consistency, staging releases reaching prod had QA sign-off."),
            _mcq(q_set="B", category="numerical_reasoning", difficulty="Medium", text="If 6 engineers complete a migration in 14 hours at equal pace, how many hours will 8 engineers require for an identical migration?", options=["9.5 hours", "10.5 hours", "11.0 hours", "12.0 hours"], answer="B", explanation="6 * 14 = 84 engineer-hours; 84 / 8 = 10.5 hours."),
            _mcq(q_set="B", category="pattern_analysis", difficulty="Medium", text="Identify the next term in the sequence: 4, 9, 19, 39, 79, ?", options=["149", "158", "159", "169"], answer="C", explanation="Double and add 1: 79 * 2 + 1 = 159."),
            _mcq(q_set="B", category="critical_thinking", difficulty="Hard", text="A portal reports 99.9% uptime yet customer complaints spiked. Which metric best explains the discrepancy?", options=["Health check endpoints stayed 200 OK while login checkout endpoints timed out", "CPU temperature remained 48°C", "Database backups ran on Sundays", "Static CSS assets used browser caching"], answer="A", explanation="Synthetic health probes passing do not guarantee user-critical flows work."),
            _mcq(q_set="B", category="abstract_reasoning", difficulty="Medium", text="Compass : Navigation :: Blueprint : ?", options=["Concrete", "Architecture", "Paint", "Excavation"], answer="B", explanation="A compass guides navigation; a blueprint guides architecture."),
            _mcq(q_set="B", category="logical_deduction", difficulty="Medium", text="All database admins have audit access. Meera does not have audit access. What follows?", options=["Meera is not a database admin", "Meera is a frontend lead", "All staff have audit access", "No conclusion follows"], answer="A", explanation="Contrapositive: not audit access -> not database admin."),
            _mcq(q_set="B", category="numerical_reasoning", difficulty="Easy", text="A cloud bill fell from $800 to $640 after rightsizing. What is the percentage savings?", options=["15%", "20%", "25%", "30%"], answer="B", explanation="160 / 800 = 20%."),
            _mcq(q_set="B", category="pattern_analysis", difficulty="Medium", text="Complete the series: 3, 6, 12, 24, 48, ?", options=["72", "84", "96", "108"], answer="C", explanation="Multiply by 2 each step -> 96."),
            _mcq(q_set="B", category="critical_thinking", difficulty="Medium", text="An automated alert triggers 50 false positives daily. What is the primary operational risk?", options=["Alert fatigue causing engineers to miss genuine critical incidents", "Faster incident resolution", "Lower notification volume", "Improved database indexing"], answer="A", explanation="Excessive noisy alerts lead to alert fatigue and missed real failures."),
            _mcq(q_set="B", category="abstract_reasoning", difficulty="Easy", text="Lens : Focus :: Index : ?", options=["Lookup", "Erase", "Encrypt", "Compress"], answer="A", explanation="A lens sharpens focus; a database index accelerates lookup."),
            _mcq(q_set="B", category="logical_deduction", difficulty="Hard", text="If a PR passes CI and has 2 approvals, it merges automatically. PR #91 did not merge automatically. Which MUST be true?", options=["Either CI failed or it lacked 2 approvals", "Both CI failed and it had zero approvals", "GitHub was offline", "PR #91 had syntax errors only"], answer="A", explanation="De Morgan's law on negation of (P and Q) -> (not P or not Q)."),
            _mcq(q_set="B", category="numerical_reasoning", difficulty="Hard", text="Three caches hit at rates 80%, 90%, and 70% on equal traffic splits. What is the overall average hit rate?", options=["78%", "80%", "82%", "85%"], answer="B", explanation="(80 + 90 + 70) / 3 = 80%."),
            _mcq(q_set="B", category="pattern_analysis", difficulty="Easy", text="Complete: D4, H8, L12, P16, ?", options=["S19", "T20", "U21", "R18"], answer="B", explanation="Step of +4 -> T20."),
            _mcq(q_set="B", category="critical_thinking", difficulty="Medium", text="Why is an A/B test biased if mobile users are assigned to Group A and desktop users to Group B?", options=["Device type confounds any observed conversion difference between variants", "Desktop monitors are always brighter", "Mobile users never click buttons", "A/B tests require 10 groups"], answer="A", explanation="Non-random stratification by device introduces severe selection bias."),
            _mcq(q_set="B", category="abstract_reasoning", difficulty="Medium", text="Dam : Flood :: Firewall : ?", options=["Intrusion", "Bandwidth", "Fiber", "Voltage"], answer="A", explanation="A dam blocks floods; a firewall blocks unauthorized intrusions."),
            _mcq(q_set="B", category="logical_deduction", difficulty="Medium", text="Some APIs are GraphQL. All GraphQL APIs use a typed schema. Therefore:", options=["Some APIs use a typed schema", "All APIs use GraphQL", "REST APIs cannot be typed", "No API uses JSON"], answer="A", explanation="The APIs that are GraphQL necessarily use a typed schema."),
            _mcq(q_set="B", category="numerical_reasoning", difficulty="Medium", text="A worker node handles 12 jobs/min. How many worker nodes are needed to handle 300 jobs in 5 minutes?", options=["4", "5", "6", "8"], answer="B", explanation="300 jobs / 5 min = 60 jobs/min; 60 / 12 = 5 nodes."),
            _mcq(q_set="B", category="pattern_analysis", difficulty="Hard", text="Find the missing number: 5, 8, 14, 23, 35, ?", options=["48", "50", "52", "54"], answer="B", explanation="Differences increase by +3: +3, +6, +9, +12, +15 -> 35 + 15 = 50."),
            _mcq(q_set="B", category="critical_thinking", difficulty="Hard", text="A vendor claims 'our tool cut bugs in half for our top 3 clients.' What statistical flaw weakens generalizing this claim?", options=["Cherry-picking / survivorship bias from a tiny non-representative sample", "Using integer percentages", "Measuring bugs over time", "Publishing client names"], answer="A", explanation="Selecting only top performers creates severe selection bias."),
            _mcq(q_set="B", category="abstract_reasoning", difficulty="Medium", text="Conductor : Orchestra :: Orchestrator : ?", options=["Containers", "Cables", "Keyboards", "Printers"], answer="A", explanation="A conductor coordinates an orchestra; a container orchestrator coordinates containers."),
            _mcq(q_set="B", category="logical_deduction", difficulty="Easy", text="Every learner who scores above 80% earns distinction. Dev scored 88%. What follows?", options=["Dev earns distinction", "Dev is the top scorer", "Only Dev earned distinction", "Nobody scored below 80%"], answer="A", explanation="Direct instantiation of universal rule."),
            _mcq(q_set="B", category="numerical_reasoning", difficulty="Easy", text="If 35% of 200 candidates choose Python, how many chose Python?", options=["60", "65", "70", "75"], answer="C", explanation="0.35 * 200 = 70."),
            _mcq(q_set="B", category="pattern_analysis", difficulty="Medium", text="Complete: 81, 27, 9, 3, ?", options=["0", "1", "2", "1/3"], answer="B", explanation="Divide by 3 each step -> 3 / 3 = 1."),
            _mcq(q_set="B", category="critical_thinking", difficulty="Easy", text="What is the first rational step when a service fails right after a configuration change?", options=["Compare and roll back the recent configuration diff safely while capturing logs", "Rewrite the entire application from scratch", "Ignore monitoring dashboards", "Delete production databases"], answer="A", explanation="Isolating and rolling back the most recent change restores service fastest."),
            _mcq(q_set="B", category="abstract_reasoning", difficulty="Hard", text="Catalyst : Reaction :: Cache : ?", options=["Retrieval", "Deletion", "Corruption", "Latency"], answer="A", explanation="A catalyst accelerates a reaction; a cache accelerates data retrieval."),
        ],
        "C": [
            _mcq(q_set="C", category="logical_deduction", difficulty="Easy", text="Either the webhook failed OR the subscriber queue was full. Monitoring confirms the queue had 80% free capacity. What must be true?", options=["The queue dropped the packet randomly", "The webhook failed", "Both guarantees succeeded", "Traffic exceeded disk limits"], answer="B", explanation="Disjunctive syllogism: A or B, not B => A."),
            _mcq(q_set="C", category="numerical_reasoning", difficulty="Medium", text="An API response drops from 320 ms to 200 ms after query indexing. What is the percentage reduction in latency?", options=["32.5%", "37.5%", "40.0%", "60.0%"], answer="B", explanation="120 / 320 = 37.5%."),
            _mcq(q_set="C", category="pattern_analysis", difficulty="Medium", text="Find the missing value: 11, 13, 17, 25, 41, ?", options=["65", "69", "73", "77"], answer="C", explanation="Differences double: +2, +4, +8, +16, +32 -> 41 + 32 = 73."),
            _mcq(q_set="C", category="critical_thinking", difficulty="Hard", text="A training cohort scored 15% higher after adding pair programming. What control check best isolates the effect of pair programming?", options=["Comparing against a parallel cohort covering the same syllabus individually", "Changing assessment difficulty for the second group", "Measuring typing speed in words per minute", "Deploying a new office theme"], answer="A", explanation="An equivalent control cohort isolates the instructional intervention."),
            _mcq(q_set="C", category="abstract_reasoning", difficulty="Medium", text="Anchor : Stability :: Beacon : ?", options=["Darkness", "Guidance", "Harbor", "Tide"], answer="B", explanation="An anchor provides stability; a beacon provides guidance."),
            _mcq(q_set="C", category="logical_deduction", difficulty="Medium", text="All production secrets live in Vault. Token T is stored in a plaintext .env file only. What follows?", options=["Token T violates the production secrets policy", "Vault is offline", "All .env files are encrypted", "Token T is an admin secret"], answer="A", explanation="Storing a secret outside Vault contradicts the policy."),
            _mcq(q_set="C", category="numerical_reasoning", difficulty="Easy", text="A pipeline runs 4 stages taking 30s, 45s, 75s, and 90s sequentially. What is total duration in minutes?", options=["3.5 minutes", "4.0 minutes", "4.5 minutes", "5.0 minutes"], answer="B", explanation="30+45+75+90 = 240 seconds = 4.0 minutes."),
            _mcq(q_set="C", category="pattern_analysis", difficulty="Medium", text="Find next term: 10, 14, 22, 34, 50, ?", options=["66", "68", "70", "74"], answer="C", explanation="Differences grow by +4: +4, +8, +12, +16, +20 -> 50 + 20 = 70."),
            _mcq(q_set="C", category="critical_thinking", difficulty="Medium", text="Why is average latency alone often misleading for SLA monitoring?", options=["A few extreme tail outliers (p99) can ruin user experience while keeping the mean low", "Averages cannot be calculated on milliseconds", "Means are always higher than maximums", "Latency never fluctuates"], answer="A", explanation="Tail percentiles (p95/p99) reveal pain hidden by arithmetic averages."),
            _mcq(q_set="C", category="abstract_reasoning", difficulty="Easy", text="Rudder : Ship :: Router : ?", options=["Packets", "Batteries", "Screens", "Chairs"], answer="A", explanation="A rudder steers a ship; a router steers network packets."),
            _mcq(q_set="C", category="logical_deduction", difficulty="Hard", text="If load exceeds 85%, autoscaling adds a replica. No replica was added at 14:00. Therefore:", options=["Either load stayed <= 85% or the autoscaler malfunctioned", "Traffic was zero", "CPU usage hit 100%", "Autoscaling deleted a replica"], answer="A", explanation="Under normal rules, no scale-out implies threshold was not breached or scaler failed."),
            _mcq(q_set="C", category="numerical_reasoning", difficulty="Hard", text="A cluster serves 1,500 req/s with 3 nodes. If 1 node fails and traffic rises 20%, what load must each surviving node handle?", options=["750 req/s", "850 req/s", "900 req/s", "1,000 req/s"], answer="C", explanation="New load = 1,500 * 1.2 = 1,800 req/s across 2 nodes = 900 req/s each."),
            _mcq(q_set="C", category="pattern_analysis", difficulty="Easy", text="Complete: A1, D4, G7, J10, ?", options=["L12", "M13", "N14", "K11"], answer="B", explanation="Step of +3 -> M13."),
            _mcq(q_set="C", category="critical_thinking", difficulty="Medium", text="Two engineers disagree on caching TTL (1 min vs 1 hour). Which criterion settles the trade-off objectively?", options=["Business tolerance for stale reads vs. database load under peak traffic", "Whoever talks loudest in standup", "Alphabetical order of their names", "Color of the dashboard chart"], answer="A", explanation="Freshness requirements vs. read load define optimal TTL."),
            _mcq(q_set="C", category="abstract_reasoning", difficulty="Medium", text="Scaffold : Construction :: Mock : ?", options=["Testing", "Shipping", "Billing", "Hosting"], answer="A", explanation="Scaffolding supports construction; mocks support isolated testing."),
            _mcq(q_set="C", category="logical_deduction", difficulty="Medium", text="No unverified account can join a live class. Ananya joined a live class. What must be true?", options=["Ananya's account is verified", "Ananya is an instructor", "All verified users joined", "Live classes are public"], answer="A", explanation="Only verified accounts can join; Ananya joined -> verified."),
            _mcq(q_set="C", category="numerical_reasoning", difficulty="Medium", text="An exam has 40 questions worth 2.5 marks each. If a learner answers 32 correctly, what is their score?", options=["75", "80", "82.5", "85"], answer="B", explanation="32 * 2.5 = 80 marks."),
            _mcq(q_set="C", category="pattern_analysis", difficulty="Hard", text="Find the next number: 2, 6, 15, 31, 56, ?", options=["85", "90", "92", "96"], answer="C", explanation="Differences are squares: +4 (+2^2), +9 (+3^2), +16 (+4^2), +25 (+5^2), +36 (+6^2) -> 56 + 36 = 92."),
            _mcq(q_set="C", category="critical_thinking", difficulty="Hard", text="A team removed code reviews to ship 20% faster this week. What long-term effect is most probable?", options=["Accumulated defects and rework will likely slow future sprints", "Technical debt disappears permanently", "Security vulnerabilities cannot occur", "Onboarding becomes unnecessary"], answer="A", explanation="Skipping quality gates trades short-term speed for compounding rework."),
            _mcq(q_set="C", category="abstract_reasoning", difficulty="Medium", text="Atlas : Geography :: Schema : ?", options=["Database", "Weather", "Music", "Travel"], answer="A", explanation="An atlas maps geography; a schema maps database structure."),
            _mcq(q_set="C", category="logical_deduction", difficulty="Easy", text="All SQL joins combine rows using related columns. LEFT JOIN is a SQL join. Therefore:", options=["LEFT JOIN combines rows using related columns", "LEFT JOIN deletes null rows", "SQL has only one join", "No join uses keys"], answer="A", explanation="Direct deductive application of the premise."),
            _mcq(q_set="C", category="numerical_reasoning", difficulty="Easy", text="If a 120 GB disk is 65% full, how many GB remain free?", options=["36 GB", "42 GB", "48 GB", "55 GB"], answer="B", explanation="35% of 120 = 42 GB."),
            _mcq(q_set="C", category="pattern_analysis", difficulty="Medium", text="Complete: 7, 10, 16, 28, 52, ?", options=["96", "100", "104", "108"], answer="B", explanation="Differences double: +3, +6, +12, +24, +48 -> 52 + 48 = 100."),
            _mcq(q_set="C", category="critical_thinking", difficulty="Easy", text="When evaluating a third-party library for enterprise use, what is the strongest red flag?", options=["Unmaintained for 4 years with unresolved critical CVEs", "Clear API documentation", "Active semantic versioning", "Comprehensive unit test suite"], answer="A", explanation="Unpatched critical security vulnerabilities in abandoned packages pose high risk."),
            _mcq(q_set="C", category="abstract_reasoning", difficulty="Hard", text="Prism : Spectrum :: Profiler : ?", options=["Bottlenecks", "Passwords", "Fonts", "Domains"], answer="A", explanation="A prism reveals hidden spectrum bands; a profiler reveals hidden performance bottlenecks."),
        ],
    }


# ---------------------------------------------------------------------------
# 3. PROGRAMMING & LOGIC — 3 COMPLETE DISTINCT SETS (20 Qs each)
# ---------------------------------------------------------------------------

def _build_programming_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "A": [
            _mcq(q_set="A", category="time_complexity", difficulty="Easy", text="What is the worst-case time complexity of binary search on a sorted array of n elements?", options=["O(1)", "O(log n)", "O(n)", "O(n log n)"], answer="B", explanation="Each step halves the search interval."),
            _mcq(q_set="A", category="code_output", difficulty="Medium", text="What is the output of Python: nums = [1, 2, 3]; print([x * x for x in nums if x % 2 == 1])?", options=["[1, 4, 9]", "[1, 9]", "[4]", "[1, 3]"], answer="B", explanation="Odd elements 1 and 3 are squared -> [1, 9]."),
            _mcq(q_set="A", category="data_structures", difficulty="Medium", text="Which data structure provides O(1) average lookup AND preserves insertion order in Python 3.7+?", options=["set", "dict", "heapq", "tuple"], answer="B", explanation="Python dicts provide O(1) hash lookup and preserve insertion order."),
            _mcq(q_set="A", category="debugging", difficulty="Medium", text="In FastAPI/SQLAlchemy, what causes stale reads or 'DetachedInstanceError' after closing a DB session?", options=["Using async routes without uvicorn", "Accessing unloaded lazy relationships after the Session closes", "Missing CORS middleware headers", "Returning Pydantic dicts instead of tuples"], answer="B", explanation="Lazy attributes require an open session unless eagerly loaded."),
            _mcq(q_set="A", category="databases_sql", difficulty="Hard", text="Which SQL clause filters groups AFTER aggregation (`COUNT`, `AVG`) has been computed?", options=["WHERE", "HAVING", "DISTINCT", "ORDER BY"], answer="B", explanation="HAVING filters aggregated groups after GROUP BY."),
            _mcq(q_set="A", category="programming_logic", difficulty="Easy", text="What does the expression `bool([])` evaluate to in Python?", options=["True", "False", "None", "Raises ValueError"], answer="B", explanation="Empty collections are falsy in Python."),
            _mcq(q_set="A", category="code_output", difficulty="Easy", text="In JavaScript, what is the output of `console.log(2 + '3')`?", options=["5", "'23'", "NaN", "TypeError"], answer="B", explanation="The + operator coerces 2 to string when paired with '3'."),
            _mcq(q_set="A", category="problem_solving", difficulty="Medium", text="Which approach best removes duplicates from a list while preserving original element order in Python?", options=["list(dict.fromkeys(items))", "items.sort()", "items.reverse()", "tuple(items)"], answer="A", explanation="dict.fromkeys preserves insertion order while deduplicating in O(n)."),
            _mcq(q_set="A", category="algorithm_understanding", difficulty="Medium", text="What property must an array satisfy BEFORE applying binary search?", options=["All values must be positive", "Elements must be sorted in monotonic order", "Length must be a power of 2", "Values must be unique strings"], answer="B", explanation="Binary search requires sorted order to discard half the space."),
            _mcq(q_set="A", category="debugging", difficulty="Easy", text="Which HTTP status code best represents a request failing input validation rules?", options=["200 OK", "422 Unprocessable Entity", "301 Moved Permanently", "502 Bad Gateway"], answer="B", explanation="422 indicates syntactically valid payload with semantic validation errors."),
            _mcq(q_set="A", category="programming_logic", difficulty="Medium", text="In TypeScript, what is the difference between `interface` and `unknown`?", options=["`unknown` forces type narrowing before use, whereas `any` disables checking", "`unknown` is identical to `string`", "`interface` only works at runtime", "`unknown` cannot hold numbers"], answer="A", explanation="`unknown` is the type-safe counterpart to `any`."),
            _mcq(q_set="A", category="code_output", difficulty="Medium", text="What does `'abcdef'[1:4]` return in Python?", options=["'abc'", "'bcd'", "'bcde'", "'cde'"], answer="B", explanation="Slice start=1 inclusive, stop=4 exclusive -> 'bcd'."),
            _mcq(q_set="A", category="data_structures", difficulty="Easy", text="Which collection prevents duplicate elements automatically?", options=["List", "Set", "Queue", "Linked List"], answer="B", explanation="A Set stores only unique elements."),
            _mcq(q_set="A", category="time_complexity", difficulty="Medium", text="What is the time complexity of inserting an element at index 0 of a standard dynamic array (Python list)?", options=["O(1)", "O(log n)", "O(n)", "O(n^2)"], answer="C", explanation="All n existing elements must shift right by one position."),
            _mcq(q_set="A", category="problem_solving", difficulty="Hard", text="How do you find two numbers in an unsorted array summing to target K in O(n) average time?", options=["Nested loops over all pairs", "Store visited complements in a HashMap/Set during a single pass", "Bubble sort first then scan linearly", "Compute factorial of each number"], answer="B", explanation="Hash lookup of `target - num` solves Two Sum in O(n) time."),
            _mcq(q_set="A", category="debugging", difficulty="Medium", text="Why should floating-point currency values be avoided in financial calculations?", options=["Binary floats introduce rounding inaccuracies (e.g., 0.1 + 0.2 != 0.3)", "Floats cannot be negative", "CPUs cannot add decimals", "JSON forbids numbers"], answer="A", explanation="Use fixed-precision Decimal or integer cents for exact money math."),
            _mcq(q_set="A", category="algorithm_understanding", difficulty="Medium", text="Which sorting algorithm is guaranteed to be stable and run in O(n log n) worst-case time?", options=["Quick Sort", "Merge Sort", "Selection Sort", "Heap Sort"], answer="B", explanation="Merge Sort is stable with guaranteed O(n log n) worst-case complexity."),
            _mcq(q_set="A", category="programming_logic", difficulty="Easy", text="What is the purpose of a `finally` block in exception handling?", options=["Runs only when an error happens", "Executes cleanup logic whether an exception occurred or not", "Suppresses all runtime exceptions silently", "Replaces `if` statements"], answer="B", explanation="`finally` always executes to close resources cleanly."),
            _mcq(q_set="A", category="code_output", difficulty="Hard", text="In JavaScript, what does `[10, 2, 1].sort()` return without a comparator?", options=["[1, 2, 10]", "[1, 10, 2]", "[10, 2, 1]", "[2, 1, 10]"], answer="B", explanation="Default JS `.sort()` converts elements to strings lexicographically."),
            _mcq(q_set="A", category="data_structures", difficulty="Hard", text="Which structure gives O(1) push/pop at BOTH front and back ends?", options=["Singly Linked List without tail", "Double-Ended Queue (Deque)", "Binary Search Tree", "Min-Heap"], answer="B", explanation="A deque supports O(1) insertions and deletions at both ends."),
        ],
        "B": [
            _mcq(q_set="B", category="time_complexity", difficulty="Medium", text="What is the average-case time complexity of Merge Sort on an unsorted array of size n?", options=["O(n)", "O(log n)", "O(n log n)", "O(n^2)"], answer="C", explanation="Merge Sort divides in log n levels with O(n) merging per level."),
            _mcq(q_set="B", category="code_output", difficulty="Medium", text="In JavaScript/TypeScript, what does `typeof null` evaluate to?", options=["'null'", "'undefined'", "'object'", "'boolean'"], answer="C", explanation="For legacy JS compatibility, `typeof null` returns `'object'`."),
            _mcq(q_set="B", category="data_structures", difficulty="Easy", text="Which traversal visits nodes level by level using a FIFO queue?", options=["Depth-First Search (DFS)", "Breadth-First Search (BFS)", "Post-order Traversal", "Topological Backtracking"], answer="B", explanation="BFS explores neighbors layer-by-layer using a FIFO queue."),
            _mcq(q_set="B", category="debugging", difficulty="Medium", text="Why does `SELECT * FROM users WHERE email = NULL` fail to match NULL rows in standard SQL?", options=["NULL requires `IS NULL` because any equality check `= NULL` evaluates to UNKNOWN", "VARCHAR columns cannot store NULL", "Indexes block NULL comparisons", "SQL turns NULL into empty string automatically"], answer="A", explanation="Always test NULL using `IS NULL` or `IS NOT NULL`."),
            _mcq(q_set="B", category="algorithms", difficulty="Hard", text="Which algorithm finds shortest weighted paths in a graph with only non-negative edge weights?", options=["Dijkstra's Algorithm", "Kruskal's MST", "QuickSelect", "Rabin-Karp"], answer="A", explanation="Dijkstra efficiently finds shortest paths for non-negative edge weights."),
            _mcq(q_set="B", category="programming_logic", difficulty="Easy", text="What does short-circuit evaluation in `A && B` mean?", options=["B is skipped if A is falsy", "Both A and B always execute", "A is evaluated after B", "It throws an error on boolean inputs"], answer="A", explanation="Logical AND stops as soon as the left operand is falsy."),
            _mcq(q_set="B", category="code_output", difficulty="Easy", text="What does Python `len({'a': 1, 'b': 2, 'a': 3})` return?", options=["1", "2", "3", "KeyError"], answer="B", explanation="Duplicate key `'a'` overwrites the earlier entry -> 2 unique keys."),
            _mcq(q_set="B", category="problem_solving", difficulty="Medium", text="Which technique efficiently checks if a string is a palindrome in O(1) extra space?", options=["Two pointers moving inward from start and end", "Sorting all characters first", "Hashing every substring", "Building a binary tree"], answer="A", explanation="Comparing left and right pointers runs in O(n) time and O(1) space."),
            _mcq(q_set="B", category="algorithm_understanding", difficulty="Medium", text="In a min-heap of size n, what is the time complexity to read (peek) the minimum element?", options=["O(1)", "O(log n)", "O(n)", "O(n log n)"], answer="A", explanation="The minimum is always located at the root index 0."),
            _mcq(q_set="B", category="debugging", difficulty="Easy", text="What does an `IndexError` in Python indicate?", options=["Accessing a sequence index outside its valid range", "Dividing a number by zero", "Importing a missing module", "Calling a non-existent dictionary key"], answer="A", explanation="IndexError happens when indexing past the bounds of a list/tuple."),
            _mcq(q_set="B", category="programming_logic", difficulty="Medium", text="What is the primary benefit of immutability in frontend state management (e.g., Angular Signals / Redux)?", options=["Predictable change detection via reference equality checks", "Eliminates all CSS styles", "Forces full page reloads on every click", "Prevents async API requests"], answer="A", explanation="Immutable updates allow O(1) reference comparisons to detect changes."),
            _mcq(q_set="B", category="code_output", difficulty="Medium", text="What is the value of `0 == false` vs `0 === false` in JavaScript?", options=["true and false", "false and true", "true and true", "false and false"], answer="A", explanation="Loose equality coerces types (`true`), strict equality checks type + value (`false`)."),
            _mcq(q_set="B", category="data_structures", difficulty="Easy", text="Which traversal of a Binary Search Tree yields keys in ascending sorted order?", options=["Pre-order", "In-order", "Post-order", "Level-order"], answer="B", explanation="In-order traversal (Left, Root, Right) visits BST elements in sorted order."),
            _mcq(q_set="B", category="time_complexity", difficulty="Medium", text="What is the worst-case time complexity of Quick Sort when the pivot is always the smallest element?", options=["O(n)", "O(n log n)", "O(n^2)", "O(log n)"], answer="C", explanation="Unbalanced partitions degrade Quick Sort to O(n^2)."),
            _mcq(q_set="B", category="problem_solving", difficulty="Hard", text="Which pattern solves 'longest substring without repeating characters' in O(n) time?", options=["Sliding window with a character-index map", "Brute force checking all O(n^3) substrings", "Depth-first graph search", "Binary search on ASCII values"], answer="A", explanation="Sliding window adjusts the left boundary in O(1) per character."),
            _mcq(q_set="B", category="debugging", difficulty="Medium", text="What causes a race condition in concurrent asynchronous code?", options=["Outcome depends unpredictably on the timing/interleaving of shared state updates", "Using `const` variables in TypeScript", "Writing pure functions without side effects", "Adding database primary keys"], answer="A", explanation="Unsynchronized concurrent writes to shared state create race conditions."),
            _mcq(q_set="B", category="algorithm_understanding", difficulty="Medium", text="What is memoization?", options=["Caching function results by input arguments to avoid redundant recomputation", "Deleting unused memory pages", "Encrypting strings before transmission", "Splitting arrays into equal chunks"], answer="A", explanation="Memoization stores computed subproblem outputs for reuse."),
            _mcq(q_set="B", category="programming_logic", difficulty="Easy", text="In REST APIs, which HTTP method is defined as safe and idempotent for reading resources?", options=["POST", "GET", "PATCH", "CONNECT"], answer="B", explanation="GET retrieves data without mutating server state."),
            _mcq(q_set="B", category="code_output", difficulty="Hard", text="What does Python `a = [1, 2]; b = a; b.append(3); print(len(a))` output?", options=["2", "3", "1", "Raises TypeError"], answer="B", explanation="`b` references the same list object as `a`, so `len(a)` becomes 3."),
            _mcq(q_set="B", category="data_structures", difficulty="Hard", text="Which data structure is ideal for implementing autocomplete prefix lookups?", options=["Trie (Prefix Tree)", "Stack", "Singly Linked List", "Circular Queue"], answer="A", explanation="Tries organize strings by shared prefixes for fast prefix search."),
        ],
        "C": [
            _mcq(q_set="C", category="time_complexity", difficulty="Medium", text="What is the space complexity of recursive Depth-First Search on a balanced binary tree of n nodes?", options=["O(1)", "O(log n)", "O(n^2)", "O(2^n)"], answer="B", explanation="Recursion stack depth equals balanced tree height O(log n)."),
            _mcq(q_set="C", category="code_output", difficulty="Medium", text="In Python, what happens when a function uses a mutable default argument `def add(item, bucket=[]):`?", options=["A fresh list is allocated per call", "The single list instance is shared across successive calls omitting `bucket`", "Python raises TypeError at definition time", "Lists become immutable tuples automatically"], answer="B", explanation="Default arguments are evaluated once at function definition time."),
            _mcq(q_set="C", category="data_structures", difficulty="Medium", text="Which structure best implements an Undo history stack where the most recent action reverses first?", options=["LIFO Stack", "Min-Heap", "Circular Ring Buffer only", "Adjacency Matrix"], answer="A", explanation="Undo operations follow Last-In-First-Out (LIFO) ordering."),
            _mcq(q_set="C", category="debugging", difficulty="Hard", text="What is an N+1 query problem in ORM-backed REST APIs?", options=["Deploying one extra database replica in staging", "Executing 1 query for parent rows plus N separate lazy queries for each child record", "Sorting results by descending primary keys", "Returning HTTP 201 instead of 200"], answer="B", explanation="Resolve N+1 queries with eager loading (`joinedload`/`selectinload`)."),
            _mcq(q_set="C", category="problem_solving", difficulty="Medium", text="How can you detect a cycle in a singly linked list in O(1) extra memory?", options=["Store every visited node pointer in a HashSet", "Use Floyd's slow (1 step) and fast (2 steps) pointers", "Sort node values in place", "Reverse the entire list twice"], answer="B", explanation="Floyd's tortoise-and-hare pointers detect cycles in O(1) space."),
            _mcq(q_set="C", category="programming_logic", difficulty="Easy", text="What is a pure function?", options=["A function whose output depends solely on its inputs with zero side effects", "A function containing at least one global variable", "A function that only returns booleans", "A function without parameters"], answer="A", explanation="Pure functions are deterministic and side-effect free."),
            _mcq(q_set="C", category="code_output", difficulty="Easy", text="What does `'hello'.toUpperCase().slice(0, 2)` return in JavaScript?", options=["'HE'", "'he'", "'HEL'", "'LO'"], answer="A", explanation="Uppercase 'HELLO' sliced [0, 2) -> 'HE'."),
            _mcq(q_set="C", category="problem_solving", difficulty="Medium", text="How can you check whether two strings are anagrams in O(n) time?", options=["Compare character frequency counts using a hash map / array", "Check if their first letters match", "Concatenate both strings", "Compare string lengths only"], answer="A", explanation="Matching character frequency histograms verifies anagrams in O(n)."),
            _mcq(q_set="C", category="algorithm_understanding", difficulty="Medium", text="What does a Hash Collision occur when?", options=["Two distinct keys map to the same hash bucket index", "A dictionary runs out of string keys", "An array is sorted in reverse order", "A loop iterates zero times"], answer="A", explanation="Collisions happen when different keys produce the same bucket index."),
            _mcq(q_set="C", category="debugging", difficulty="Easy", text="What is the primary purpose of setting a breakpoint in a debugger?", options=["Pause execution at a specific line to inspect variables and call stack", "Delete compiled build artifacts", "Encrypt source code files", "Restart the operating system"], answer="A", explanation="Breakpoints let developers step through state interactively."),
            _mcq(q_set="C", category="programming_logic", difficulty="Medium", text="Why is parameterized SQL (bound parameters) preferred over string concatenation?", options=["Prevents SQL injection and improves query plan caching", "Makes queries slower intentionally", "Disables database indexes", "Converts SQL into HTML"], answer="A", explanation="Bound parameters separate query structure from user data."),
            _mcq(q_set="C", category="code_output", difficulty="Medium", text="What does Python `list(range(1, 10, 3))` produce?", options=["[1, 4, 7]", "[1, 4, 7, 10]", "[1, 3, 6, 9]", "[0, 3, 6, 9]"], answer="A", explanation="Starts at 1, steps by 3, stops before 10 -> [1, 4, 7]."),
            _mcq(q_set="C", category="data_structures", difficulty="Easy", text="Which structure enforces First-In-First-Out (FIFO) ordering?", options=["Stack", "Queue", "Binary Heap", "Hash Table"], answer="B", explanation="Queues process items in FIFO order."),
            _mcq(q_set="C", category="time_complexity", difficulty="Medium", text="What is the time complexity of looking up an element by index `arr[i]` in a contiguous array?", options=["O(1)", "O(log n)", "O(n)", "O(n log n)"], answer="A", explanation="Direct pointer offset math accesses `arr[i]` in constant O(1) time."),
            _mcq(q_set="C", category="problem_solving", difficulty="Hard", text="Which data structure validates balanced parentheses `({[]})` in a single pass?", options=["Stack", "Max-Heap", "Adjacency List", "Bloom Filter"], answer="A", explanation="Push opening brackets onto a stack and match on closing brackets."),
            _mcq(q_set="C", category="debugging", difficulty="Medium", text="What is a memory leak in a long-running Single Page Application?", options=["Retaining references to detached DOM nodes or unsubscribed observables so GC cannot reclaim them", "Refreshing the browser tab", "Using CSS variables", "Minifying JavaScript bundles"], answer="A", explanation="Forgotten subscriptions/timers retain references and prevent garbage collection."),
            _mcq(q_set="C", category="algorithm_understanding", difficulty="Medium", text="When is Insertion Sort actually faster than Merge Sort in practice?", options=["On very small or nearly sorted arrays due to low constant overhead", "On random arrays of 10 million integers", "On reverse-sorted million-row tables", "Never under any input"], answer="A", explanation="Insertion Sort runs in O(n) on nearly sorted inputs with minimal overhead."),
            _mcq(q_set="C", category="programming_logic", difficulty="Easy", text="What does `async`/`await` syntactic sugar simplify in JavaScript and Python?", options=["Writing asynchronous non-blocking code in a readable sequential style", "Compiling C++ binaries", "Creating SQL tables automatically", "Blocking the main UI thread"], answer="A", explanation="async/await streamlines Promise/coroutine composition cleanly."),
            _mcq(q_set="C", category="code_output", difficulty="Hard", text="In Python, what is the output of `print({1, 2, 3} & {2, 3, 4})`?", options=["{1, 2, 3, 4}", "{2, 3}", "{1, 4}", "{}"], answer="B", explanation="The `&` operator computes set intersection -> {2, 3}."),
            _mcq(q_set="C", category="data_structures", difficulty="Hard", text="Which data structure combines a HashMap with a Doubly Linked List to build an O(1) LRU Cache?", options=["HashMap + Doubly Linked List", "Stack + Binary Tree", "Array + Min-Heap", "Trie + Set"], answer="A", explanation="HashMap gives O(1) key lookup; Doubly Linked List gives O(1) eviction/promotion."),
        ],
    }


# ---------------------------------------------------------------------------
# 4. LOGICAL REASONING — SET B & SET C (25 DISTINCT Qs EACH; Set A = baseline 25)
# ---------------------------------------------------------------------------

def _build_logical_extra_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "B": [
            _mcq(q_set="B", category="number_series", difficulty="Easy", text="Find the next number: 7, 14, 28, 56, ?", options=["98", "112", "114", "126"], answer="B", explanation="Multiply by 2 each step -> 112."),
            _mcq(q_set="B", category="number_series", difficulty="Medium", text="Find the missing term: 1, 4, 9, 16, 25, ?, 49", options=["32", "35", "36", "40"], answer="C", explanation="Perfect squares: 6^2 = 36."),
            _mcq(q_set="B", category="number_series", difficulty="Medium", text="Complete the series: 10, 15, 25, 40, 60, ?", options=["80", "85", "90", "95"], answer="B", explanation="Differences +5, +10, +15, +20, +25 -> 85."),
            _mcq(q_set="B", category="number_series", difficulty="Hard", text="Find the next number: 2, 12, 36, 80, 150, ?", options=["242", "252", "260", "275"], answer="B", explanation="n^3 + n^2: 6^3 + 6^2 = 216 + 36 = 252."),
            _mcq(q_set="B", category="alphabet_series", difficulty="Medium", text="Complete the pattern: ACE, FHJ, KMO, ?", options=["PRT", "PQS", "OQS", "QSU"], answer="A", explanation="Each letter shifts +5 from the prior group -> PRT."),
            _mcq(q_set="B", category="alphabet_series", difficulty="Easy", text="Find the next letter: B, D, G, K, P, ?", options=["U", "V", "W", "X"], answer="B", explanation="Gaps +2, +3, +4, +5, +6 -> P(16)+6 = V(22)."),
            _mcq(q_set="B", category="alphabet_series", difficulty="Hard", text="Complete: AZ, CX, EV, GT, ?", options=["IR", "IQ", "HS", "JR"], answer="A", explanation="First letter +2 (I), second letter -2 (R) -> IR."),
            _mcq(q_set="B", category="coding_decoding", difficulty="Medium", text="If CODE is written as DPEF (+1 shift), how is LOGIC written?", options=["MPHJD", "MPHJE", "NQIKF", "KNFHB"], answer="A", explanation="Shift L-O-G-I-C by +1 -> M-P-H-J-D."),
            _mcq(q_set="B", category="coding_decoding", difficulty="Easy", text="If CAT = 24 (3+1+20), what is DOG equal to?", options=["24", "26", "28", "30"], answer="B", explanation="D(4) + O(15) + G(7) = 26."),
            _mcq(q_set="B", category="coding_decoding", difficulty="Hard", text="If TRAIN is coded as GIZRM (reverse alphabet A<->Z), how is NODE coded?", options=["MLWV", "MLWU", "NKWV", "MMWV"], answer="A", explanation="N->M, O->L, D->W, E->V -> MLWV."),
            _mcq(q_set="B", category="blood_relations", difficulty="Medium", text="Ananya is the sister of Vikram. Vikram is the father of Riya. How is Ananya related to Riya?", options=["Mother", "Cousin", "Aunt", "Grandmother"], answer="C", explanation="Father's sister is aunt."),
            _mcq(q_set="B", category="blood_relations", difficulty="Easy", text="Rohit's mother is the only daughter of Suresh. How is Suresh related to Rohit?", options=["Uncle", "Maternal Grandfather", "Brother", "Father"], answer="B", explanation="Mother's father is maternal grandfather."),
            _mcq(q_set="B", category="blood_relations", difficulty="Hard", text="A is B's brother, C is A's mother, D is C's father, E is B's son. How is E related to D?", options=["Grandson", "Great-grandson", "Nephew", "Son"], answer="B", explanation="D -> C -> B -> E spans three generations (great-grandson)."),
            _mcq(q_set="B", category="direction_distance", difficulty="Medium", text="Karan walks 6 km North, then turns East and walks 8 km. What is his shortest distance from the start?", options=["10 km", "12 km", "14 km", "9 km"], answer="A", explanation="sqrt(6^2 + 8^2) = 10 km."),
            _mcq(q_set="B", category="direction_distance", difficulty="Easy", text="Facing East, Priya turns 90 degrees left and walks 5 m. Which direction is she facing?", options=["North", "South", "West", "East"], answer="A", explanation="90° left from East is North."),
            _mcq(q_set="B", category="direction_distance", difficulty="Hard", text="Amit walks 5 km South, turns right 3 km, turns right 5 km, then left 4 km. How far is he from start?", options=["5 km", "7 km", "8 km", "9 km"], answer="B", explanation="North/South cancels (5-5=0); Westward total = 3 + 4 = 7 km."),
            _mcq(q_set="B", category="pattern_recognition", difficulty="Medium", text="Find next number: 100, 95, 85, 70, 50, ?", options=["30", "25", "20", "35"], answer="B", explanation="Subtract -5, -10, -15, -20, -25 -> 25."),
            _mcq(q_set="B", category="pattern_recognition", difficulty="Easy", text="Complete the alternating pattern: 5, 20, 10, 40, 20, ?", options=["60", "70", "80", "90"], answer="C", explanation="Odd positions double (5,10,20); even positions double (20,40,80)."),
            _mcq(q_set="B", category="pattern_recognition", difficulty="Hard", text="Find the missing value in the triad: (3, 9, 27), (4, 16, 64), (5, 25, ?)", options=["100", "125", "150", "225"], answer="B", explanation="(n, n^2, n^3) -> 5^3 = 125."),
            _mcq(q_set="B", category="logical_statements", difficulty="Hard", text="Some engineers are designers. All designers are creative. Which conclusion MUST follow?", options=["All engineers are creative", "Some engineers are creative", "No designer is an engineer", "Only designers are creative"], answer="B", explanation="The engineers who are designers must be creative."),
            _mcq(q_set="B", category="logical_statements", difficulty="Medium", text="All servers are machines. No machine is organic. What necessarily follows?", options=["No server is organic", "Some servers are organic", "All machines are servers", "No conclusion follows"], answer="A", explanation="Servers are a subset of machines, none of which are organic."),
            _mcq(q_set="B", category="odd_one_out", difficulty="Easy", text="Select the odd one out: Python, Java, FastAPI, C++", options=["Python", "Java", "FastAPI", "C++"], answer="C", explanation="FastAPI is a web framework; the others are programming languages."),
            _mcq(q_set="B", category="odd_one_out", difficulty="Medium", text="Select the odd number out: 17, 23, 29, 33", options=["17", "23", "29", "33"], answer="D", explanation="33 is composite (3*11); the others are prime numbers."),
            _mcq(q_set="B", category="analogy", difficulty="Easy", text="Compiler : Executable :: Blueprint : ?", options=["Building", "Hammer", "Inspector", "Permit"], answer="A", explanation="A compiler produces an executable; a blueprint guides constructing a building."),
            _mcq(q_set="B", category="analogy", difficulty="Medium", text="Kilobyte : Megabyte :: Second : ?", options=["Millisecond", "Minute", "Clock", "Calendar"], answer="B", explanation="Larger unit of measurement relationship."),
        ],
        "C": [
            _mcq(q_set="C", category="number_series", difficulty="Easy", text="Find the next number: 3, 9, 27, 81, ?", options=["162", "216", "243", "324"], answer="C", explanation="Powers of 3 -> 81 * 3 = 243."),
            _mcq(q_set="C", category="number_series", difficulty="Medium", text="Complete: 8, 12, 18, 26, 36, ?", options=["44", "46", "48", "52"], answer="C", explanation="Differences increase by +2: +4, +6, +8, +10, +12 -> 48."),
            _mcq(q_set="C", category="number_series", difficulty="Medium", text="Find the next term: 1, 2, 6, 24, 120, ?", options=["600", "720", "840", "960"], answer="B", explanation="Factorials: 6! = 720."),
            _mcq(q_set="C", category="number_series", difficulty="Hard", text="Find the missing term: 4, 10, 22, 46, 94, ?", options=["186", "188", "190", "192"], answer="C", explanation="Multiply by 2 and add 2: 94 * 2 + 2 = 190."),
            _mcq(q_set="C", category="alphabet_series", difficulty="Medium", text="Complete the sequence: Z, X, U, Q, L, ?", options=["G", "F", "E", "H"], answer="B", explanation="Backward gaps: -2, -3, -4, -5, -6 -> L(12)-6 = F(6)."),
            _mcq(q_set="C", category="alphabet_series", difficulty="Easy", text="Find next pair: AB, DE, GH, JK, ?", options=["LM", "MN", "NO", "KL"], answer="B", explanation="Skip one letter between pairs -> MN."),
            _mcq(q_set="C", category="alphabet_series", difficulty="Hard", text="Complete the pattern: BDF, GIK, LNP, ?", options=["QSU", "QST", "PRT", "RSU"], answer="A", explanation="Each letter shifts +5 -> QSU."),
            _mcq(q_set="C", category="coding_decoding", difficulty="Medium", text="If TEST is coded as 20-5-19-20, what is API coded as?", options=["1-16-9", "2-15-9", "1-15-8", "3-16-10"], answer="A", explanation="A=1, P=16, I=9."),
            _mcq(q_set="C", category="coding_decoding", difficulty="Easy", text="If DATA is reversed to ATAD, how is CLOUD coded?", options=["DUOLC", "DUCOL", "DOLUC", "DOULC"], answer="A", explanation="Exact character reversal -> DUOLC."),
            _mcq(q_set="C", category="coding_decoding", difficulty="Hard", text="If every letter moves -2 so CODE -> AMBC, how is SYNC coded?", options=["QWLA", "QWKZ", "RXMB", "QVLA"], answer="A", explanation="S-2=Q, Y-2=W, N-2=L, C-2=A -> QWLA."),
            _mcq(q_set="C", category="blood_relations", difficulty="Medium", text="Meera points to a photo and says, 'He is the only son of my mother's father.' Who is in the photo?", options=["Meera's cousin", "Meera's maternal uncle", "Meera's brother", "Meera's nephew"], answer="B", explanation="Mother's father's only son is maternal uncle."),
            _mcq(q_set="C", category="blood_relations", difficulty="Easy", text="P is Q's daughter. R is Q's sister. How is R related to P?", options=["Aunt", "Mother", "Sister", "Niece"], answer="A", explanation="Parent's sister is aunt."),
            _mcq(q_set="C", category="blood_relations", difficulty="Hard", text="X is the husband of Y. W is the daughter of X. Z is the husband of W. How is Z related to Y?", options=["Son", "Son-in-law", "Brother-in-law", "Nephew"], answer="B", explanation="Daughter's husband is son-in-law."),
            _mcq(q_set="C", category="direction_distance", difficulty="Medium", text="Sneha faces South, turns 90° clockwise, then turns 180°. Which direction does she face now?", options=["North", "East", "West", "South"], answer="B", explanation="South -> clockwise 90° = West -> +180° = East."),
            _mcq(q_set="C", category="direction_distance", difficulty="Easy", text="A drone flies 9 km East and 12 km North. What is the straight-line distance from origin?", options=["14 km", "15 km", "18 km", "21 km"], answer="B", explanation="sqrt(9^2 + 12^2) = sqrt(225) = 15 km."),
            _mcq(q_set="C", category="direction_distance", difficulty="Hard", text="If North-East becomes South, what does North-West become under the same rotation?", options=["East", "West", "South-West", "North"], answer="A", explanation="135° clockwise rotation maps NW to East."),
            _mcq(q_set="C", category="pattern_recognition", difficulty="Medium", text="Complete: 2, 5, 11, 23, 47, ?", options=["91", "93", "95", "99"], answer="C", explanation="Multiply by 2 and add 1 -> 95."),
            _mcq(q_set="C", category="pattern_recognition", difficulty="Easy", text="Find the next value: 1, 1, 2, 3, 5, 8, 13, ?", options=["18", "20", "21", "23"], answer="C", explanation="Fibonacci sequence: 8 + 13 = 21."),
            _mcq(q_set="C", category="pattern_recognition", difficulty="Hard", text="Find the missing number: 3, 4, 8, 17, 33, ?", options=["54", "58", "60", "64"], answer="B", explanation="Add squares: +1, +4, +9, +16, +25 -> 33 + 25 = 58."),
            _mcq(q_set="C", category="logical_statements", difficulty="Hard", text="No outdated APIs are secure. Some REST endpoints are outdated APIs. What follows?", options=["All REST endpoints are insecure", "Some REST endpoints are not secure", "All secure APIs are REST", "No conclusion possible"], answer="B", explanation="Those outdated REST endpoints cannot be secure."),
            _mcq(q_set="C", category="logical_statements", difficulty="Medium", text="All testers write bug reports. Some interns are testers. Therefore:", options=["Some interns write bug reports", "All interns are testers", "No tester is an intern", "Bug reports are written only by interns"], answer="A", explanation="The interns who are testers must write bug reports."),
            _mcq(q_set="C", category="odd_one_out", difficulty="Easy", text="Choose the odd one out: PostgreSQL, SQLite, Angular, MSSQL", options=["PostgreSQL", "SQLite", "Angular", "MSSQL"], answer="C", explanation="Angular is a frontend UI framework; the others are relational databases."),
            _mcq(q_set="C", category="odd_one_out", difficulty="Medium", text="Select the odd one out: HTTP, TCP, DNS, JSON", options=["HTTP", "TCP", "DNS", "JSON"], answer="D", explanation="JSON is a data interchange format; the others are network protocols."),
            _mcq(q_set="C", category="analogy", difficulty="Easy", text="Latency : Speed :: Memory Leak : ?", options=["Bandwidth", "Stability", "Throughput", "Encryption"], answer="B", explanation="Latency degrades speed; memory leaks degrade stability."),
            _mcq(q_set="C", category="analogy", difficulty="Medium", text="Git : Version Control :: Docker : ?", options=["Containerization", "Typography", "Spreadsheet", "Audio"], answer="A", explanation="Git handles version control; Docker handles containerization."),
        ],
    }


# ---------------------------------------------------------------------------
# 5. ENGLISH GRAMMAR — SET B & SET C (20 DISTINCT Qs EACH; Set A = baseline 20)
# ---------------------------------------------------------------------------

def _build_english_grammar_extra_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "B": [
            _mcq(q_set="B", category="subject_verb_agreement", difficulty="Easy", text="Every single member of the QA guild _____ responsible for regression verification.", options=["are", "is", "were", "have"], answer="B", explanation="'Every single member' is singular and takes 'is'."),
            _mcq(q_set="B", category="subject_verb_agreement", difficulty="Medium", text="A list of deprecated endpoints _____ published in the migration handbook.", options=["were", "have been", "has been", "are"], answer="C", explanation="The singular head noun 'list' requires singular 'has been'."),
            _mcq(q_set="B", category="subject_verb_agreement", difficulty="Hard", text="Not only the lead architect but also two senior engineers _____ reviewing the RFC.", options=["is", "was", "are", "has been"], answer="C", explanation="With 'not only... but also', the verb agrees with the nearer subject 'engineers'."),
            _mcq(q_set="B", category="tenses_and_aspects", difficulty="Easy", text="She _____ three microservices before joining our platform division last year.", options=["builds", "had built", "will build", "is building"], answer="B", explanation="Past perfect describes an action completed prior to another past event."),
            _mcq(q_set="B", category="tenses_and_aspects", difficulty="Medium", text="By December, the cohort _____ all twelve onboarding modules.", options=["will have completed", "completes", "completed", "has completing"], answer="A", explanation="Future perfect expresses completion prior to a future point."),
            _mcq(q_set="B", category="tenses_and_aspects", difficulty="Hard", text="Hardly _____ the deployment finished when the monitoring dashboard turned green.", options=["did", "had", "has", "was"], answer="B", explanation="Negative inversion with 'Hardly' pairs with past perfect ('Hardly had... when')."),
            _mcq(q_set="B", category="articles", difficulty="Easy", text="Our instructor delivered _____ insightful overview of distributed caching.", options=["a", "an", "the", "no article"], answer="B", explanation="'Insightful' begins with a vowel sound and takes 'an'."),
            _mcq(q_set="B", category="articles", difficulty="Medium", text="Please review _____ architecture diagram attached to ticket #402.", options=["a", "an", "the", "no article"], answer="C", explanation="A specific referenced diagram takes the definite article 'the'."),
            _mcq(q_set="B", category="prepositions", difficulty="Easy", text="The security team is accountable _____ auditing every third-party integration.", options=["for", "to", "at", "with"], answer="A", explanation="Standard collocation: 'accountable for' an action."),
            _mcq(q_set="B", category="prepositions", difficulty="Medium", text="The new release complies fully _____ enterprise accessibility standards.", options=["to", "with", "on", "for"], answer="B", explanation="Standard collocation: 'comply with'."),
            _mcq(q_set="B", category="conjunctions", difficulty="Easy", text="_____ the staging server was restarted, the background worker resumed automatically.", options=["Although", "Because", "Unless", "Despite"], answer="B", explanation="'Because' correctly expresses cause and effect here."),
            _mcq(q_set="B", category="conjunctions", difficulty="Medium", text="The rollout succeeded smoothly _____ minor latency during peak traffic.", options=["despite", "although", "even though", "whereas"], answer="A", explanation="'Despite' precedes a noun phrase without a finite verb."),
            _mcq(q_set="B", category="voice_and_speech", difficulty="Medium", text="Convert to passive voice: 'The DevOps team automated the nightly backup.'", options=["The nightly backup was automated by the DevOps team.", "The nightly backup is automating by the DevOps team.", "The DevOps team was automated by the nightly backup.", "The nightly backup had automate by the DevOps team."], answer="A", explanation="Simple past active converts to 'was + past participle'."),
            _mcq(q_set="B", category="voice_and_speech", difficulty="Hard", text="Choose the correct indirect speech: He said, 'We will ship the patch tomorrow.'", options=["He said that they would ship the patch the next day.", "He said that we will ship the patch tomorrow.", "He told that they ship the patch yesterday.", "He said they are shipping the patch now."], answer="A", explanation="'will' backshifts to 'would' and 'tomorrow' shifts to 'the next day'."),
            _mcq(q_set="B", category="sentence_correction", difficulty="Medium", text="Choose the grammatically concise and correct sentence:", options=["Each developer should submit their own individual report by themselves.", "Each developer should submit their report by Friday.", "Each developers should submit report by Friday.", "Every developer submitting their report by Friday."], answer="B", explanation="Option B eliminates redundancy and uses valid syntax."),
            _mcq(q_set="B", category="sentence_correction", difficulty="Hard", text="Identify the sentence with parallel structure:", options=["The platform enables tracking progress, grading quizzes, and to schedule classes.", "The platform enables tracking progress, grading quizzes, and scheduling classes.", "The platform enables to track progress, grading quizzes, and schedule classes.", "The platform enables tracked progress, grades quizzes, and scheduling classes."], answer="B", explanation="All three items consistently use gerund phrases."),
            _mcq(q_set="B", category="vocabulary", difficulty="Easy", text="Choose the closest synonym for 'concise' in technical documentation:", options=["Verbose", "Succinct", "Ambiguous", "Fragmented"], answer="B", explanation="'Succinct' means brief and clearly expressed."),
            _mcq(q_set="B", category="vocabulary", difficulty="Medium", text="Choose the antonym of 'mitigate':", options=["Alleviate", "Exacerbate", "Reduce", "Moderate"], answer="B", explanation="'Exacerbate' means to worsen, the opposite of 'mitigate'."),
            _mcq(q_set="B", category="idioms_collocations", difficulty="Medium", text="What does 'get the ball rolling' mean in a project kickoff meeting?", options=["Delay deliverables indefinitely", "Initiate action and start momentum", "Cancel the sprint plan", "Archive completed code"], answer="B", explanation="Means to get a process or initiative started."),
            _mcq(q_set="B", category="error_detection", difficulty="Hard", text="Identify the grammatical error in: 'Between you and I, the API contract needs stricter validation.'", options=["'Between' should be 'Among'", "'I' should be 'me'", "'needs' should be 'need'", "'stricter' should be 'more strictness'"], answer="B", explanation="Preposition 'between' takes the objective pronoun 'me'."),
        ],
        "C": [
            _mcq(q_set="C", category="subject_verb_agreement", difficulty="Easy", text="The series of workshops on cloud security _____ every Tuesday morning.", options=["run", "runs", "are running", "were run"], answer="B", explanation="Singular 'series' takes singular verb 'runs'."),
            _mcq(q_set="C", category="subject_verb_agreement", difficulty="Medium", text="Neither of the proposed database schemas _____ backward compatibility.", options=["break", "breaks", "are breaking", "were breaking"], answer="B", explanation="'Neither' is grammatically singular in formal English ('breaks')."),
            _mcq(q_set="C", category="subject_verb_agreement", difficulty="Hard", text="More than one candidate _____ achieved a perfect score on the assessment.", options=["have", "has", "were", "are"], answer="B", explanation="'More than one + singular noun' takes a singular verb ('has')."),
            _mcq(q_set="C", category="tenses_and_aspects", difficulty="Easy", text="Our engineering team _____ daily standups at 9:30 AM sharp.", options=["holds", "is held", "holding", "was hold"], answer="A", explanation="Simple present expresses habitual routines."),
            _mcq(q_set="C", category="tenses_and_aspects", difficulty="Medium", text="If I _____ about the schema freeze earlier, I would have merged the migration yesterday.", options=["knew", "had known", "know", "would know"], answer="B", explanation="Third conditional uses past perfect in the if-clause."),
            _mcq(q_set="C", category="tenses_and_aspects", difficulty="Hard", text="It is essential that every reviewer _____ the checklist before approving.", options=["completes", "complete", "completed", "completing"], answer="B", explanation="Mandative subjunctive uses the bare infinitive ('complete')."),
            _mcq(q_set="C", category="articles", difficulty="Easy", text="He earned _____ MBA before transitioning into enterprise product management.", options=["a", "an", "the", "no article"], answer="B", explanation="'MBA' starts with the vowel sound 'em', requiring 'an'."),
            _mcq(q_set="C", category="articles", difficulty="Medium", text="Writing clean tests requires _____ patience and discipline.", options=["a", "an", "no article", "the"], answer="C", explanation="Uncountable abstract nouns used generally take zero article."),
            _mcq(q_set="C", category="prepositions", difficulty="Easy", text="Please refrain _____ committing credentials to shared repositories.", options=["from", "of", "to", "with"], answer="A", explanation="Standard collocation: 'refrain from'."),
            _mcq(q_set="C", category="prepositions", difficulty="Medium", text="The updated onboarding flow is consistent _____ ISO quality guidelines.", options=["with", "at", "upon", "into"], answer="A", explanation="Standard collocation: 'consistent with'."),
            _mcq(q_set="C", category="conjunctions", difficulty="Easy", text="You cannot access production logs _____ your role has been verified.", options=["unless", "because", "so", "while"], answer="A", explanation="'Unless' introduces the necessary negative condition."),
            _mcq(q_set="C", category="conjunctions", difficulty="Medium", text="_____ the test suite passed locally, it failed in CI due to a missing env variable.", options=["Although", "Because", "Therefore", "Since"], answer="A", explanation="'Although' introduces a contrasting clause."),
            _mcq(q_set="C", category="voice_and_speech", difficulty="Medium", text="Convert to active voice: 'The compliance report was audited by an external panel.'", options=["An external panel audited the compliance report.", "An external panel audits the compliance report.", "The compliance report audited an external panel.", "An external panel is auditing the compliance report."], answer="A", explanation="Simple past passive converts to simple past active."),
            _mcq(q_set="C", category="voice_and_speech", difficulty="Hard", text="Choose correct reported speech: The mentor asked, 'Have you tested the edge cases?'", options=["The mentor asked whether I had tested the edge cases.", "The mentor asked that have I tested the edge cases.", "The mentor asked did I test the edge cases.", "The mentor told whether I test the edge cases."], answer="A", explanation="Yes/no questions use 'whether/if' with backshifted statement word order."),
            _mcq(q_set="C", category="sentence_correction", difficulty="Medium", text="Select the sentence free of dangling modifiers:", options=["Running the unit tests, a hidden bug was discovered.", "Running the unit tests, the engineer discovered a hidden bug.", "A hidden bug, running the unit tests, was discovered.", "Discovered running the unit tests was a hidden bug."], answer="B", explanation="The subject 'the engineer' directly performs 'running the unit tests'."),
            _mcq(q_set="C", category="sentence_correction", difficulty="Hard", text="Choose the correctly punctuated sentence:", options=["The latency dropped significantly; however, memory usage remained elevated.", "The latency dropped significantly, however memory usage remained elevated.", "The latency dropped significantly; however memory usage remained elevated.", "The latency dropped significantly however, memory usage remained elevated."], answer="A", explanation="Conjunctive adverb 'however' takes a semicolon before and comma after."),
            _mcq(q_set="C", category="vocabulary", difficulty="Easy", text="Choose the best synonym for 'robust' in software architecture:", options=["Fragile", "Resilient", "Obsolete", "Trivial"], answer="B", explanation="'Resilient' matches the meaning of 'robust'."),
            _mcq(q_set="C", category="vocabulary", difficulty="Medium", text="Choose the closest antonym for 'ambiguous':", options=["Vague", "Explicit", "Cryptic", "Uncertain"], answer="B", explanation="'Explicit' is clear and unambiguous."),
            _mcq(q_set="C", category="idioms_collocations", difficulty="Medium", text="What does 'on the same page' signify in cross-functional teams?", options=["Sharing a common understanding of goals and expectations", "Reading the same browser tab simultaneously", "Printing documentation on single sheets", "Working only in the same room"], answer="A", explanation="Means aligned in understanding and expectations."),
            _mcq(q_set="C", category="error_detection", difficulty="Hard", text="Find the error: 'Less than ten engineers attended the optional architecture clinic.'", options=["'Less' should be 'Fewer'", "'attended' should be 'attends'", "'optional' should be 'optionally'", "No error exists"], answer="A", explanation="Countable plural nouns ('engineers') take 'Fewer', not 'Less'."),
        ],
    }


# ---------------------------------------------------------------------------
# 6. TECHNICAL SKILLS — SET B & SET C (20 DISTINCT Qs EACH; Set A = baseline 20)
# ---------------------------------------------------------------------------

def _build_technical_extra_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "B": [
            _mcq(q_set="B", category="data_structures", difficulty="Easy", text="Which data structure is best suited for priority-based task scheduling?", options=["Binary Heap (Priority Queue)", "Singly Linked List", "Static String", "Fixed Boolean Array"], answer="A", explanation="A priority queue extracts highest/lowest priority tasks in O(log n)."),
            _mcq(q_set="B", category="data_structures", difficulty="Medium", text="What is the primary advantage of a Doubly Linked List over a Singly Linked List?", options=["O(1) deletion of a known node without traversing from head", "Zero pointer memory overhead", "O(1) random index lookup", "Automatic sorting on insert"], answer="A", explanation="Having `prev` pointers enables O(1) removal given a node reference."),
            _mcq(q_set="B", category="algorithms", difficulty="Medium", text="Which algorithm efficiently finds the Minimum Spanning Tree by sorting edges by weight?", options=["Kruskal's Algorithm", "Binary Search", "Floyd-Warshall", "KMP String Matching"], answer="A", explanation="Kruskal greedily picks lightest non-cycle edges using Union-Find."),
            _mcq(q_set="B", category="algorithms", difficulty="Hard", text="What is the worst-case time complexity of Heap Sort?", options=["O(n)", "O(n log n)", "O(n^2)", "O(log n)"], answer="B", explanation="Building the heap is O(n) and extracting n elements is O(n log n)."),
            _mcq(q_set="B", category="python_programming", difficulty="Easy", text="What does a Python generator using `yield` provide compared to returning a full list?", options=["Lazy item-by-item evaluation with O(1) memory overhead", "Automatic GPU execution", "Compile-time static typing", "Multi-machine networking"], answer="A", explanation="Generators produce values lazily without materializing the full sequence."),
            _mcq(q_set="B", category="python_programming", difficulty="Medium", text="What is the purpose of Python's `with` statement (context manager)?", options=["Guarantees deterministic resource acquisition and cleanup via `__enter__`/`__exit__`", "Declares a global variable", "Creates a background thread", "Disables garbage collection"], answer="A", explanation="Context managers ensure files, locks, and sessions close cleanly."),
            _mcq(q_set="B", category="python_programming", difficulty="Hard", text="Why are tuples hashable (when containing hashable items) whereas lists are not?", options=["Tuples are immutable, ensuring a stable hash value over their lifetime", "Tuples store only integers", "Lists cannot be indexed", "Tuples always have length 2"], answer="A", explanation="Hash table keys must be immutable so their hash never changes."),
            _mcq(q_set="B", category="javascript_web", difficulty="Easy", text="Which HTTP header instructs browsers which origins may read cross-origin API responses?", options=["Access-Control-Allow-Origin", "Content-Disposition", "Cache-Control", "User-Agent"], answer="A", explanation="CORS relies on `Access-Control-Allow-Origin`."),
            _mcq(q_set="B", category="javascript_web", difficulty="Medium", text="In Angular, what is the role of an HTTP Interceptor?", options=["Centrally inspect/modify outgoing HTTP requests and incoming responses (e.g., attach Bearer JWT)", "Render SVG charts", "Compile SCSS files", "Manage SQLite migrations"], answer="A", explanation="Interceptors handle cross-cutting HTTP concerns like auth tokens and logging."),
            _mcq(q_set="B", category="javascript_web", difficulty="Hard", text="What is the purpose of `debounceTime` on a live search input?", options=["Wait for a brief typing pause before firing an API call to avoid flooding the backend", "Encrypt keystrokes with AES", "Force synchronous blocking loops", "Disable keyboard navigation"], answer="A", explanation="Debouncing reduces redundant network calls while the user types."),
            _mcq(q_set="B", category="databases_sql", difficulty="Easy", text="Which SQL constraint guarantees that every value in a foreign key column matches an existing primary key?", options=["FOREIGN KEY (Referential Integrity)", "DEFAULT", "CHECK", "ORDER BY"], answer="A", explanation="Foreign keys enforce referential integrity across related tables."),
            _mcq(q_set="B", category="databases_sql", difficulty="Medium", text="What does the 'A' in ACID database transactions stand for?", options=["Atomicity — all operations in a transaction succeed together or roll back completely", "Availability — every node responds even offline", "Asynchrony — writes skip disk", "Aggregation — summing columns"], answer="A", explanation="Atomicity ensures all-or-nothing transaction execution."),
            _mcq(q_set="B", category="databases_sql", difficulty="Hard", text="When can adding too many indexes on a high-write table degrade performance?", options=["Every INSERT/UPDATE/DELETE must maintain each index B-tree, increasing write latency", "Indexes delete rows automatically", "SELECT queries stop working", "Indexes disable primary keys"], answer="A", explanation="Indexes accelerate reads at the cost of write amplification and storage."),
            _mcq(q_set="B", category="system_design", difficulty="Medium", text="What is the role of a Reverse Proxy (e.g., NGINX) in front of backend APIs?", options=["TLS termination, load balancing, rate limiting, and routing requests to upstream servers", "Compiling Python bytecode into Java", "Replacing relational database storage", "Rendering native Android views"], answer="A", explanation="Reverse proxies centralize routing, SSL termination, and load distribution."),
            _mcq(q_set="B", category="system_design", difficulty="Hard", text="What is horizontal scaling (scaling out)?", options=["Adding more application server instances behind a load balancer", "Upgrading RAM on one single machine", "Decreasing network bandwidth", "Removing stateless sessions"], answer="A", explanation="Horizontal scaling distributes load across additional nodes."),
            _mcq(q_set="B", category="git_devops", difficulty="Easy", text="Which Git command downloads remote commits WITHOUT automatically merging them into your working branch?", options=["git fetch", "git push", "git commit", "git init"], answer="A", explanation="`git fetch` updates remote-tracking refs safely without modifying local work."),
            _mcq(q_set="B", category="git_devops", difficulty="Medium", text="What is the primary goal of a CI (Continuous Integration) pipeline?", options=["Automatically build, lint, and test every commit/PR to catch regressions early", "Manually copy files over FTP once a year", "Disable version control branches", "Bypass unit tests in production"], answer="A", explanation="CI provides automated quality verification on every integration."),
            _mcq(q_set="B", category="networking", difficulty="Easy", text="Which protocol provides reliable, ordered, connection-oriented byte streams?", options=["TCP", "UDP", "ICMP", "ARP"], answer="A", explanation="TCP guarantees ordered, acknowledged delivery."),
            _mcq(q_set="B", category="networking", difficulty="Medium", text="What does DNS translate?", options=["Human-readable domain names into IP addresses", "SQL statements into JSON", "JWT tokens into passwords", "HTML into CSS"], answer="A", explanation="Domain Name System resolves hostnames to IP addresses."),
            _mcq(q_set="B", category="operating_systems", difficulty="Medium", text="What is the primary difference between a process and a thread?", options=["Threads within the same process share memory space, while processes have isolated address spaces", "Processes cannot execute CPU instructions", "Threads cannot share heap memory", "Operating systems support only one thread total"], answer="A", explanation="Threads share process address space and resources with lighter context switches."),
        ],
        "C": [
            _mcq(q_set="C", category="data_structures", difficulty="Easy", text="Which tree data structure self-balances to maintain O(log n) search, insert, and delete?", options=["AVL / Red-Black Tree", "Unbalanced Linked List", "Static Queue", "Flat Array"], answer="A", explanation="Self-balancing BSTs keep height logarithmic."),
            _mcq(q_set="C", category="data_structures", difficulty="Medium", text="What is a Graph Adjacency List preferred for over an Adjacency Matrix?", options=["Sparse graphs where edges E << V^2, saving substantial memory", "Checking edge existence in O(1) for dense graphs", "Storing fixed 2D images", "Sorting integers in O(1)"], answer="A", explanation="Adjacency lists take O(V + E) space vs. O(V^2) for matrices."),
            _mcq(q_set="C", category="algorithms", difficulty="Medium", text="Which algorithmic paradigm builds solutions from overlapping subproblems with optimal substructure?", options=["Dynamic Programming", "Linear Probing", "Random Walk", "Bubble Swapping"], answer="A", explanation="DP solves overlapping subproblems systematically."),
            _mcq(q_set="C", category="algorithms", difficulty="Hard", text="Which algorithm detects cycles and produces a valid build order in a Directed Acyclic Graph (DAG)?", options=["Topological Sort (Kahn's / DFS)", "Binary Search", "Prim's MST", "QuickSort"], answer="A", explanation="Topological sorting orders dependencies in a DAG."),
            _mcq(q_set="C", category="python_programming", difficulty="Easy", text="What is the purpose of a Python virtual environment (`venv`)?", options=["Isolate project-specific package dependencies from the global Python interpreter", "Compile Python to x86 assembly", "Replace operating system kernels", "Host PostgreSQL databases"], answer="A", explanation="Virtual environments prevent version conflicts across projects."),
            _mcq(q_set="C", category="python_programming", difficulty="Medium", text="In FastAPI, what library validates request/response schemas using Python type hints?", options=["Pydantic", "Matplotlib", "Tkinter", "PyGame"], answer="A", explanation="FastAPI leverages Pydantic models for runtime validation and serialization."),
            _mcq(q_set="C", category="python_programming", difficulty="Hard", text="What does `@lru_cache` from Python's `functools` module do?", options=["Memoizes recent function call results using a Least-Recently-Used cache", "Encrypts function arguments", "Executes code in parallel processes", "Automatically writes unit tests"], answer="A", explanation="Decorating pure functions with `@lru_cache` caches return values."),
            _mcq(q_set="C", category="javascript_web", difficulty="Easy", text="Which HTTP status code indicates a newly created resource after a successful POST?", options=["201 Created", "204 No Content", "403 Forbidden", "404 Not Found"], answer="A", explanation="201 Created signifies successful resource creation."),
            _mcq(q_set="C", category="javascript_web", difficulty="Medium", text="Why should JWT access tokens be stored carefully and protected against XSS?", options=["Injected malicious scripts can read tokens exposed to JavaScript and impersonate users", "JWTs cannot contain JSON payloads", "Browsers reject HTTPS headers", "XSS only affects backend SQLite files"], answer="A", explanation="Strict sanitization, CSP, and secure token handling mitigate XSS theft."),
            _mcq(q_set="C", category="javascript_web", difficulty="Hard", text="What does Angular's zoneless change detection rely on for fine-grained UI updates?", options=["Reactive Signals and explicit change notifications rather than Zone.js monkey-patching", "Full browser reloads on each click", "Global `setInterval` polling every 1ms", "Server-side PHP templates"], answer="A", explanation="Angular Signals notify views precisely when reactive state changes."),
            _mcq(q_set="C", category="databases_sql", difficulty="Easy", text="What is the difference between `INNER JOIN` and `LEFT JOIN`?", options=["LEFT JOIN retains all rows from the left table even when no matching right row exists", "INNER JOIN deletes rows permanently", "LEFT JOIN sorts alphabetically", "There is no difference"], answer="A", explanation="LEFT JOIN preserves unmatched left rows with NULLs on the right."),
            _mcq(q_set="C", category="databases_sql", difficulty="Medium", text="What is database normalization primarily designed to minimize?", options=["Data redundancy and update anomalies", "Primary key columns", "Index lookup speed", "SQL syntax readability"], answer="A", explanation="Normalization organizes schemas to avoid duplicate inconsistent data."),
            _mcq(q_set="C", category="databases_sql", difficulty="Hard", text="What does a composite index on `(department_id, created_at)` accelerate best?", options=["Queries filtering by `department_id` or both `department_id` and `created_at`", "Queries filtering only by `description LIKE '%foo%'`", "Dropping tables faster", "Disabling foreign keys"], answer="A", explanation="B-tree composite indexes leverage the leftmost prefix rule."),
            _mcq(q_set="C", category="system_design", difficulty="Medium", text="What is the purpose of a Rate Limiter on public API endpoints?", options=["Protect services from abuse, brute-force attacks, and traffic spikes", "Increase response latency for fun", "Disable HTTPS encryption", "Merge separate databases"], answer="A", explanation="Rate limiting enforces fair usage and prevents denial-of-service overload."),
            _mcq(q_set="C", category="system_design", difficulty="Hard", text="Why do distributed systems use Message Brokers (e.g., RabbitMQ / Kafka) between services?", options=["Decouple producers from consumers and absorb burst traffic asynchronously", "Force synchronous blocking RPCs", "Eliminate all JSON serialization", "Replace TLS certificates"], answer="A", explanation="Message queues provide temporal decoupling and resilient buffering."),
            _mcq(q_set="C", category="git_devops", difficulty="Easy", text="What does `git stash` do?", options=["Temporarily shelves uncommitted working tree edits so you can switch context cleanly", "Permanently deletes the entire repository", "Pushes code to GitHub automatically", "Creates a Docker container"], answer="A", explanation="`git stash` saves dirty changes cleanly off the working tree."),
            _mcq(q_set="C", category="git_devops", difficulty="Medium", text="What is the core benefit of Docker containers in engineering teams?", options=["Package app code and dependencies together for consistent behavior across dev, CI, and prod", "Replace all unit tests", "Double hardware CPU clock speed", "Eliminate the need for Git"], answer="A", explanation="Containers eliminate 'works on my machine' environment drift."),
            _mcq(q_set="C", category="networking", difficulty="Easy", text="What does TLS/HTTPS guarantee between client and server?", options=["Encryption in transit, data integrity, and server authentication", "Zero database bugs", "Automatic frontend styling", "Infinite server RAM"], answer="A", explanation="TLS protects confidentiality, integrity, and authenticity over the wire."),
            _mcq(q_set="C", category="networking", difficulty="Medium", text="What distinguishes HTTP 401 Unauthorized from HTTP 403 Forbidden?", options=["401 means missing/invalid authentication; 403 means authenticated but lacking permission", "401 means server crash; 403 means success", "They are identical", "403 means DNS timeout"], answer="A", explanation="401 = unauthenticated; 403 = authenticated yet unauthorized for the resource."),
            _mcq(q_set="C", category="operating_systems", difficulty="Medium", text="What is a Deadlock in multithreaded systems?", options=["Two or more threads wait indefinitely for locks held by each other", "A thread finishing execution cleanly", "Caching read-only files in RAM", "Allocating stack memory on startup"], answer="A", explanation="Circular lock waiting freezes progress until broken."),
        ],
    }


# ---------------------------------------------------------------------------
# 7. PSYCHOMETRIC & EQ — SET B & SET C (20 DISTINCT Qs EACH; Set A = baseline 20)
# ---------------------------------------------------------------------------

def _build_psychometric_extra_sets() -> dict[str, list[dict[str, Any]]]:
    opts_collab = [
        "Collaborate closely with stakeholders and align priorities transparently.",
        "Balance independent execution with scheduled peer check-ins.",
        "Complete drafts solo first and share near final delivery.",
        "Defer alignment until formal escalation.",
    ]
    opts_adapt = [
        "Proactively experiment, document learnings, and share insights with the team.",
        "Study documentation steadily and adopt the change smoothly.",
        "Wait for detailed step-by-step walkthroughs before engaging.",
        "Resist the transition until previous tools are deprecated.",
    ]
    opts_eq = [
        "Listen empathetically, clarify perspectives neutrally, and guide constructive resolution.",
        "Offer calm factual observations and suggest a focused follow-up.",
        "Stay quiet during tension and discuss only if directly asked.",
        "Dismiss opposing viewpoints quickly to move on.",
    ]
    opts_sj = [
        "Escalate transparently with concrete root-cause context and a proposed remediation plan.",
        "Flag the risk promptly during standup and request review.",
        "Attempt an undocumented workaround quietly without informing peers.",
        "Postpone reporting the issue until someone else discovers it.",
    ]
    opts_work = [
        "Break work into measurable milestones, clarify acceptance criteria, and track blockers early.",
        "Follow sprint tickets systematically with regular progress updates.",
        "Focus on one preferred task at a time without checking dependencies.",
        "React only to urgent pings as they arrive.",
    ]
    return {
        "B": [
            _likert(q_set="B", category="personality_work_preferences", text="When onboarding onto an unfamiliar codebase, how do you ramp up fastest?", options=["Pair with mentors and document architecture notes systematically", "Read specs thoroughly and ask targeted clarifying questions", "Experiment independently before checking team conventions", "Wait until someone assigns step-by-step tickets"]),
            _likert(q_set="B", category="personality_work_preferences", text="How do you prefer to handle ambiguous acceptance criteria on a new feature ticket?", options=opts_work),
            _likert(q_set="B", category="personality_work_preferences", text="When juggling documentation and feature coding in a tight sprint, what is your habit?", options=opts_work),
            _likert(q_set="B", category="personality_work_preferences", text="How do you structure your daily focus blocks during a complex engineering milestone?", options=opts_work),
            _likert(q_set="B", category="situational_judgement", text="A teammate introduces an edge-case regression right before release freeze. What is your immediate move?", options=["Constructively share reproduction steps and pair on a minimal fix", "Document the regression clearly in the release tracker", "Roll back quietly without notifying the author", "Ignore it until the next sprint"]),
            _likert(q_set="B", category="situational_judgement", text="You discover a third-party API dependency has an undocumented rate limit mid-sprint. How do you respond?", options=opts_sj),
            _likert(q_set="B", category="situational_judgement", text="A stakeholder requests an out-of-scope UI change two hours before a demo. What is your best step?", options=opts_sj),
            _likert(q_set="B", category="situational_judgement", text="You realize your own estimate for a database migration was overly optimistic by two days. What do you do?", options=opts_sj),
            _likert(q_set="B", category="emotional_intelligence", text="During a heated architecture debate, two peers talk over each other. How do you respond?", options=["Summarize both technical positions neutrally and refocus on trade-offs", "Ask clarifying questions to surface shared constraints", "Stay silent until voting begins", "Declare one side wrong immediately"]),
            _likert(q_set="B", category="emotional_intelligence", text="A new joinee seems hesitant to ask questions during team standups. How do you support them?", options=opts_eq),
            _likert(q_set="B", category="emotional_intelligence", text="Your design proposal receives tough critique in front of senior leadership. How do you react?", options=opts_eq),
            _likert(q_set="B", category="emotional_intelligence", text="A colleague from QA sounds frustrated after encountering repeated environment failures. What is your response?", options=opts_eq),
            _likert(q_set="B", category="learning_adaptability", text="Your department adopts a new framework halfway through a project. How do you react?", options=["Build a small proof-of-concept and share takeaways with the team", "Follow official docs steadily during designated hours", "Express hesitation until templates are prepared", "Avoid the updated modules entirely"]),
            _likert(q_set="B", category="learning_adaptability", text="When your preferred debugging workflow is replaced by centralized telemetry dashboards, how do you adjust?", options=opts_adapt),
            _likert(q_set="B", category="learning_adaptability", text="After a post-incident review highlights a gap in your SQL tuning skills, what action do you take?", options=opts_adapt),
            _likert(q_set="B", category="learning_adaptability", text="How do you stay effective when reassigned from a frontend task to assist on a backend API integration?", options=opts_adapt),
            _likert(q_set="B", category="team_collaboration", text="How do you ensure remote team members stay equally informed on decisions?", options=opts_collab),
            _likert(q_set="B", category="team_collaboration", text="When reviewing a peer's pull request with multiple architectural choices, how do you give feedback?", options=opts_collab),
            _likert(q_set="B", category="team_collaboration", text="How do you coordinate API contract updates between backend and frontend engineers?", options=opts_collab),
            _likert(q_set="B", category="team_collaboration", text="When finishing your sprint stories ahead of schedule, how do you support the cohort?", options=opts_collab),
        ],
        "C": [
            _likert(q_set="C", category="personality_work_preferences", text="When managing three overlapping deadlines, how do you structure execution?", options=["Break milestones into measurable deliverables and flag blockers early", "Prioritize highest-impact tasks first with daily checkpoints", "Work strictly chronologically on incoming messages", "Switch tasks ad-hoc whenever pinged"]),
            _likert(q_set="C", category="personality_work_preferences", text="How do you prefer to prepare before leading a technical walkthrough for peers?", options=opts_work),
            _likert(q_set="C", category="personality_work_preferences", text="What motivates your best craftsmanship on repetitive maintenance tasks?", options=opts_work),
            _likert(q_set="C", category="personality_work_preferences", text="How do you approach self-reviewing your code before opening a pull request?", options=opts_work),
            _likert(q_set="C", category="situational_judgement", text="You spot ambiguous requirements in a compliance specification before sprint kickoff. What do you do?", options=["Draft concrete edge cases and confirm sign-off with the product owner", "Flag the ambiguity during daily standup", "Assume the simplest interpretation and proceed", "Leave the requirement unimplemented until QA flags it"]),
            _likert(q_set="C", category="situational_judgement", text="An automated alert fires in staging showing elevated error rates while the service owner is away. What do you do?", options=opts_sj),
            _likert(q_set="C", category="situational_judgement", text="You notice an accessible alternative improves keyboard usability for learners with minimal effort. How do you proceed?", options=opts_sj),
            _likert(q_set="C", category="situational_judgement", text="A vendor SDK upgrade breaks two unit tests right before a release window. What is your next step?", options=opts_sj),
            _likert(q_set="C", category="emotional_intelligence", text="A junior colleague appears overwhelmed after receiving extensive PR feedback. How do you help?", options=["Walk through high-priority items constructively and recognize what worked well", "Offer quick pointers on key improvements asynchronously", "Send links to generic style manuals without context", "Rewrite the entire PR yourself without explaining why"]),
            _likert(q_set="C", category="emotional_intelligence", text="During a tight incident bridge call, stress levels rise sharply. How do you communicate?", options=opts_eq),
            _likert(q_set="C", category="emotional_intelligence", text="When a teammate receives credit for an idea you co-authored, how do you handle it?", options=opts_eq),
            _likert(q_set="C", category="emotional_intelligence", text="You sense a quiet misalignment between product expectations and engineering scope. What is your move?", options=opts_eq),
            _likert(q_set="C", category="learning_adaptability", text="After receiving critical coaching on presentation clarity, what is your next step?", options=["Rework slide flow and request a dry-run review with a peer", "Apply key bullet changes before the next meeting", "Stick mostly to your original script", "Stop volunteering for demos"]),
            _likert(q_set="C", category="learning_adaptability", text="Your organization introduces stricter automated linting and type-safety rules. How do you respond?", options=opts_adapt),
            _likert(q_set="C", category="learning_adaptability", text="When tackling a domain you have never worked in before (e.g., psychometric scoring), how do you learn?", options=opts_adapt),
            _likert(q_set="C", category="learning_adaptability", text="How do you incorporate retrospective action items into your personal engineering workflow?", options=opts_adapt),
            _likert(q_set="C", category="team_collaboration", text="When a cross-functional handoff stalls between backend and QA, how do you intervene?", options=opts_collab),
            _likert(q_set="C", category="team_collaboration", text="How do you ensure design decisions made in ad-hoc calls remain transparent to the whole team?", options=opts_collab),
            _likert(q_set="C", category="team_collaboration", text="When pairing with a teammate who works at a different pace than you, how do you collaborate?", options=opts_collab),
            _likert(q_set="C", category="team_collaboration", text="How do you contribute to healthy onboarding culture for incoming cohorts?", options=opts_collab),
        ],
    }


# ---------------------------------------------------------------------------
# 8. WRITTEN COMPOSITION — 3 COMPLETE DISTINCT SETS (20 Qs each)
# ---------------------------------------------------------------------------

def _build_composition_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "A": [
            _mcq(q_set="A", category="executive_writing", difficulty="Easy", text="Which opening line is most effective for an executive status email?", options=["Hi, just wanted to randomly share some thoughts from today.", "Release 2.4 completed on schedule with zero P1 regressions; key metrics follow below.", "There were lots of things we worked on and some went well.", "Please read all 14 pages before asking questions."], answer="B", explanation="Executive writing leads with the bottom line up front (BLUF)."),
            _mcq(q_set="A", category="clarity_coherence", difficulty="Easy", text="Which sentence communicates the action item most clearly?", options=["Something should probably be looked at regarding the login timeout.", "Rohan will increase the JWT refresh grace window to 60 seconds by Thursday 5 PM.", "Login timeouts are occasionally discussed in meetings.", "Maybe someone could check timeouts next week."], answer="B", explanation="Clear action items specify owner, concrete action, and deadline."),
            _mcq(q_set="A", category="grammar_precision", difficulty="Medium", text="Choose the most concise revision of 'At this point in time, we are in the process of evaluating options.'", options=["Currently, we are evaluating options.", "At this current point in time, options are being evaluated by us.", "Right now at this time we evaluate all of the options.", "We are presently in the process of conducting an evaluation."], answer="A", explanation="Eliminates wordy filler phrases while preserving full meaning."),
            _mcq(q_set="A", category="scenario_response", difficulty="Medium", text="How should you frame a client incident update during an active outage?", options=["State confirmed impact, active mitigation steps, and next update timestamp transparently.", "Blame a junior engineer publicly.", "Stay silent until the issue resolves hours later.", "Promise it will never happen again without investigating root cause."], answer="A", explanation="Professional incident comms provide impact, mitigation, and cadence."),
            _mcq(q_set="A", category="executive_writing", difficulty="Medium", text="What is the primary purpose of using descriptive section headings in a technical RFC?", options=["Enable busy stakeholders to scan architecture trade-offs and decisions rapidly", "Increase page count artificially", "Hide risks at the bottom of the document", "Replace code reviews"], answer="A", explanation="Structured headings dramatically improve scannability and decision speed."),
            _mcq(q_set="A", category="clarity_coherence", difficulty="Medium", text="Which transition best links a problem statement to its proposed technical fix?", options=["Consequently, we recommend introducing an idempotency key layer.", "Meanwhile, coffee is served in the pantry.", "Regardless, we ignored the issue.", "Similarly, the logo uses indigo."], answer="A", explanation="'Consequently' establishes a direct logical bridge from cause to solution."),
            _mcq(q_set="A", category="grammar_precision", difficulty="Easy", text="Which revision eliminates passive ambiguity in 'Mistakes were made during the migration'?", options=["The migration script omitted the composite index on `session_id`.", "Mistakes had been made in migration.", "It was seen that errors happened.", "Things went wrong somehow."], answer="A", explanation="Active, specific phrasing identifies the exact technical cause."),
            _mcq(q_set="A", category="scenario_response", difficulty="Hard", text="A stakeholder insists on skipping QA testing to ship Friday. Which written response is most professional?", options=["Outline the specific production risks of skipping QA and propose a scoped Friday release covering tested features only.", "Reply 'No, that is a terrible idea.'", "Agree silently and hope nothing breaks.", "Ignore the message until Monday."], answer="A", explanation="Constructive pushback presents risks paired with a viable option."),
            _mcq(q_set="A", category="executive_writing", difficulty="Easy", text="When summarizing 3 risks for leadership, which formatting choice works best?", options=["Bulleted list pairing each risk with severity and concrete mitigation", "A single 400-word dense paragraph without punctuation", "All-caps bold sentences throughout", "Unlabeled raw terminal dumps"], answer="A", explanation="Structured bullets with severity and mitigation enable rapid decisions."),
            _mcq(q_set="A", category="clarity_coherence", difficulty="Hard", text="Which sentence avoids vague pronoun reference?", options=["When the gateway called the billing service, it timed out.", "When the gateway called the billing service, the billing service timed out after 5 seconds.", "They told them that it failed.", "This broke that before it finished."], answer="B", explanation="Naming 'the billing service' removes pronoun ambiguity."),
            _mcq(q_set="A", category="grammar_precision", difficulty="Medium", text="Choose the best word to replace 'utilize' in plain technical prose:", options=["use", "operationalize", "leverage-execute", "deploy-consume"], answer="A", explanation="Plain precise verbs ('use') improve readability over jargon."),
            _mcq(q_set="A", category="scenario_response", difficulty="Medium", text="What tone is most effective in an asynchronous code review comment?", options=["Objective, specific to the code behavior, and offering a clear suggestion", "Sarcastic about coding style", "Vague ('looks weird, fix it')", "Focused on personal criticism"], answer="A", explanation="Constructive reviews critique code objectively with actionable advice."),
            _mcq(q_set="A", category="executive_writing", difficulty="Hard", text="What belongs in the 'Non-Goals' section of a design document?", options=["Explicit boundaries stating what the current milestone will NOT attempt to solve", "List of bugs ignored in production", "Personal career aspirations", "Deleted unit tests"], answer="A", explanation="Explicit non-goals prevent scope creep and align stakeholder expectations."),
            _mcq(q_set="A", category="clarity_coherence", difficulty="Easy", text="Which subject line is best for an urgent deployment approval request?", options=["[Action Required] Sign-off for Auth Service v3.1 Release by 4:00 PM IST", "Quick question", "Hello team!!!", "FYI stuff"], answer="A", explanation="Clear tag, exact scope, and deadline maximize response speed."),
            _mcq(q_set="A", category="grammar_precision", difficulty="Medium", text="Which sentence uses active voice cleanly?", options=["The automated suite validates 140 endpoints before merge.", "140 endpoints are being validated by the automated suite before merge.", "Validation of 140 endpoints is performed prior to merging.", "Prior to merge, 140 endpoints undergo validation."], answer="A", explanation="Direct subject-verb-object structure reads strongest."),
            _mcq(q_set="A", category="scenario_response", difficulty="Easy", text="When handing off an open bug before going on leave, what should your handoff note include?", options=["Reproduction steps, current hypothesis, linked logs/PR, and next owner", "Just 'good luck, check Slack'", "Only the ticket number without context", "Nothing until you return"], answer="A", explanation="Complete handoff notes preserve momentum without duplicate investigation."),
            _mcq(q_set="A", category="executive_writing", difficulty="Medium", text="Why should metrics in reports include baseline comparisons (e.g., '380ms -> 210ms')?", options=["Provides immediate context showing magnitude and direction of improvement", "Makes numbers harder to read", "Hides absolute performance", "Replaces monitoring tools"], answer="A", explanation="Baselines make raw numbers meaningful to readers."),
            _mcq(q_set="A", category="clarity_coherence", difficulty="Medium", text="Which sentence keeps paragraph unity intact in a post-mortem summary?", options=["Each paragraph focuses on one phase: timeline, root cause, or remediation.", "Mixing lunch preferences into the root-cause paragraph.", "Repeating the title four times inside the body.", "Listing unrelated sprint demos inside outage metrics."], answer="A", explanation="One clear theme per paragraph maintains logical coherence."),
            _mcq(q_set="A", category="grammar_precision", difficulty="Hard", text="Fix the misplaced modifier: 'We only need to migrate two tables this sprint.'", options=["We need to migrate only two tables this sprint.", "Only we need to migrate two tables this sprint.", "We need only to migrate two tables this sprint.", "We need to only migrate two tables this sprint."], answer="A", explanation="Placing 'only' directly before 'two tables' clarifies scope precisely."),
            _mcq(q_set="A", category="scenario_response", difficulty="Medium", text="How should you close a written proposal requesting cross-team alignment?", options=["State the specific decision needed, options under consideration, and target feedback date.", "End abruptly mid-paragraph.", "Ask everyone to guess what approval is required.", "Avoid mentioning timelines."], answer="A", explanation="Explicit calls to action prevent stalled proposals."),
        ],
        "B": [
            _mcq(q_set="B", category="executive_writing", difficulty="Easy", text="What does the 'inverted pyramid' principle mean in business writing?", options=["Place the most critical conclusion first, followed by supporting details and background", "Hide the recommendation on the final slide", "Start every memo with historical trivia", "Write sentences from shortest to longest"], answer="A", explanation="Leading with key conclusions respects reader time."),
            _mcq(q_set="B", category="clarity_coherence", difficulty="Easy", text="Which sentence is easiest for a non-technical stakeholder to understand?", options=["Caching reduced dashboard load time from 4 seconds to under 1 second.", "L2 Redis serialization lowered TCP round-trip overhead across pods.", "Memory allocation heaps converged asymptotically.", "Buffer flushes optimized syscall contention."], answer="A", explanation="Audience-aware writing translates tech work into business impact."),
            _mcq(q_set="B", category="grammar_precision", difficulty="Medium", text="Replace the nominalization 'conduct an investigation of' with stronger prose:", options=["investigate", "perform an inquiry into", "execute an analysis upon", "undertake research regarding"], answer="A", explanation="Strong verbs beat clunky noun-verb phrases."),
            _mcq(q_set="B", category="scenario_response", difficulty="Medium", text="You missed a minor internal deadline by half a day. What is the best proactive communication?", options=["Notify the lead early with the revised ETA and confirm zero downstream blockers.", "Wait until asked two days later.", "Blame unrelated departments.", "Mark the task complete while unfinished."], answer="A", explanation="Early transparent ETA updates build trust."),
            _mcq(q_set="B", category="executive_writing", difficulty="Medium", text="When comparing two vendor architectures in a memo, what visual format clarifies trade-offs fastest?", options=["A structured comparison matrix across cost, latency, security, and maintainability", "Two separate unformatted chat paragraphs", "Random screenshots without captions", "An email with zero formatting"], answer="A", explanation="Comparison tables expose trade-offs side by side."),
            _mcq(q_set="B", category="clarity_coherence", difficulty="Medium", text="Which connector signals a contrast between two findings?", options=["However", "Furthermore", "Additionally", "Moreover"], answer="A", explanation="'However' introduces contrasting evidence."),
            _mcq(q_set="B", category="grammar_precision", difficulty="Easy", text="Choose the correct capitalization for a formal report heading:", options=["Quarterly Assessment Telemetry Summary", "quarterly assessment telemetry summary", "QUARTERLY aSSESSMENT tELEMETRY sUMMARY", "Quarterly assessment Telemetry summary"], answer="A", explanation="Consistent title case looks clean and professional."),
            _mcq(q_set="B", category="scenario_response", difficulty="Hard", text="A customer submits an angry escalation email over a UI bug. How should your first reply open?", options=["Acknowledge the disruption empathetically, confirm reproduction, and share the fix timeline.", "Argue that they clicked the wrong button.", "Copy-paste a generic terms-of-service disclaimer.", "Close the ticket without explanation."], answer="A", explanation="Empathy paired with concrete ownership de-escalates tension."),
            _mcq(q_set="B", category="executive_writing", difficulty="Easy", text="What makes a release changelog genuinely useful to teammates?", options=["Grouping changes into Features, Fixes, and Breaking Changes with migration notes", "Listing raw commit hashes only", "Writing 'misc updates' for 40 files", "Omitting breaking API changes"], answer="A", explanation="Categorized changelogs let consumers adopt updates safely."),
            _mcq(q_set="B", category="clarity_coherence", difficulty="Hard", text="Which edit removes redundancy from 'final end result' and 'past history'?", options=["'result' and 'history'", "'very final end result'", "'historical past history'", "'completed final end result'"], answer="A", explanation="Trim tautologies to tighten prose."),
            _mcq(q_set="B", category="grammar_precision", difficulty="Medium", text="Choose the correct usage of 'affect' vs 'effect':", options=["The schema change will affect response latency; its effect is measurable immediately.", "The schema change will effect response latency; its affect is measurable immediately.", "Both affect and effect are always verbs only.", "Neither word fits technical writing."], answer="A", explanation="'Affect' is typically the verb (influence); 'effect' is the noun (result)."),
            _mcq(q_set="B", category="scenario_response", difficulty="Medium", text="When documenting an API endpoint for onboarding engineers, what is most essential?", options=["Auth requirements, request/response JSON examples, and common error codes", "Only the internal variable names", "Only the author's favorite IDE", "No example payloads"], answer="A", explanation="Concrete examples and error contracts accelerate integration."),
            _mcq(q_set="B", category="executive_writing", difficulty="Hard", text="Why should risk statements avoid vague labels like 'high risk' without quantification?", options=["Specifying likelihood and concrete impact enables objective prioritization", "Vague labels are always preferred by auditors", "Quantification is forbidden in engineering docs", "Risks should never be documented"], answer="A", explanation="Concrete likelihood + impact drives sound engineering decisions."),
            _mcq(q_set="B", category="clarity_coherence", difficulty="Easy", text="Which sentence flows best in a user-facing error banner?", options=["Unable to save changes because your session expired. Please sign in again.", "Error 0x800F4 NullPointerException at token.ts:412.", "Failure occurred.", "Bad input happened somewhere."], answer="A", explanation="Actionable plain language helps users recover immediately."),
            _mcq(q_set="B", category="grammar_precision", difficulty="Medium", text="Select the sentence with consistent tense:", options=["The service validates the token, queries the database, and returns a JSON payload.", "The service validates the token, queried the database, and will returning JSON.", "The service validated the token, queries the database, and return JSON.", "The service validating the token and returns JSON."], answer="A", explanation="Consistent present simple tense describes system behavior cleanly."),
            _mcq(q_set="B", category="scenario_response", difficulty="Easy", text="What should a concise meeting recap email contain?", options=["Key decisions reached, assigned action items with due dates, and open questions", "A word-for-word transcript of small talk", "No owner names on follow-up tasks", "Only the meeting start time"], answer="A", explanation="Decision + action + owner recaps keep teams accountable."),
            _mcq(q_set="B", category="executive_writing", difficulty="Medium", text="When writing for global distributed teams, which style improves comprehension?", options=["Clear, idiom-free plain English with explicit ISO dates and time zones", "Regional slang and ambiguous dates like 04/05", "Unexplained internal acronyms", "Dense walls of text"], answer="A", explanation="Explicit time zones and plain phrasing prevent cross-region misreading."),
            _mcq(q_set="B", category="clarity_coherence", difficulty="Medium", text="Which ordering creates the clearest troubleshooting runbook?", options=["Symptom -> Verification check -> Remediation steps -> Escalation contact", "Escalation -> Random logs -> Symptom", "Conclusion only", "Alphabetical order of sentences"], answer="A", explanation="Logical diagnostic progression minimizes mean time to recovery."),
            _mcq(q_set="B", category="grammar_precision", difficulty="Hard", text="Choose the correct sentence using 'its' vs 'it's':", options=["The service restored its cache because it's configured for auto-recovery.", "The service restored it's cache because its configured for auto-recovery.", "The service restored its' cache.", "Its' configured for auto-recovery."], answer="A", explanation="'its' = possessive; 'it's' = contraction of 'it is'."),
            _mcq(q_set="B", category="scenario_response", difficulty="Medium", text="How should you document a temporary workaround in code or a ticket?", options=["Explain why it is needed, link the tracking issue for proper cleanup, and state expiry conditions.", "Add it silently with no comment.", "Claim it is permanent architecture.", "Delete related tests so CI passes."], answer="A", explanation="Documented context prevents temporary hacks from becoming permanent debt."),
        ],
        "C": [
            _mcq(q_set="C", category="executive_writing", difficulty="Easy", text="What is the hallmark of persuasive technical writing?", options=["Supporting recommendations with objective benchmarks, trade-offs, and clear reasoning", "Using exaggerated marketing adjectives", "Ignoring drawbacks of the preferred option", "Writing overly complex sentences"], answer="A", explanation="Evidence and balanced trade-offs build engineering credibility."),
            _mcq(q_set="C", category="clarity_coherence", difficulty="Easy", text="Which sentence best trims unnecessary throat-clearing?", options=["Deployments pause Friday at 6 PM IST for database maintenance.", "I am writing this email today in order to inform everyone that deployments will pause...", "It is worth noting that perhaps deployments may pause...", "As you may or may not already be aware, deployments pause..."], answer="A", explanation="Cutting filler phrases surfaces the core message immediately."),
            _mcq(q_set="C", category="grammar_precision", difficulty="Medium", text="Choose the most precise replacement for 'due to the fact that':", options=["because", "in light of the circumstance whereby", "owing to the reality in which", "for the reason of being"], answer="A", explanation="'because' conveys the identical causal relation in one word."),
            _mcq(q_set="C", category="scenario_response", difficulty="Medium", text="How should you announce a breaking API change to consuming teams?", options=["Provide advance notice, deprecation timeline, before/after migration snippets, and support contact.", "Deploy the breaking change unannounced at midnight.", "Mention it casually in a closed chat.", "Remove the documentation page."], answer="A", explanation="Clear deprecation timelines and migration examples ensure smooth adoption."),
            _mcq(q_set="C", category="executive_writing", difficulty="Medium", text="What makes a KPI dashboard summary insightful rather than merely descriptive?", options=["Explaining WHY the metric moved and what action is recommended next", "Repeating numbers already visible in the chart without commentary", "Hiding downward trends", "Using five different fonts"], answer="A", explanation="Insight connects metric movement to drivers and next steps."),
            _mcq(q_set="C", category="clarity_coherence", difficulty="Medium", text="Which transition best introduces a concrete example?", options=["For instance", "Conversely", "Nevertheless", "Otherwise"], answer="A", explanation="'For instance' cleanly signals an illustrative example."),
            _mcq(q_set="C", category="grammar_precision", difficulty="Easy", text="Which sentence correctly uses 'ensure' vs 'insure'?", options=["Automated regression tests ensure backward compatibility.", "Automated regression tests insure backward compatibility.", "Automated regression tests assure backward compatibility policy.", "Tests insures compatibility."], answer="A", explanation="'Ensure' means to guarantee an outcome; 'insure' relates to financial insurance."),
            _mcq(q_set="C", category="scenario_response", difficulty="Hard", text="Two teams disagree over ownership of a shared microservice. What should your alignment memo do first?", options=["Clarify current pain points, define explicit service boundaries, and propose clear SLA ownership options.", "Assign blame for past outages.", "Refuse to document responsibilities.", "Escalate without consulting either team."], answer="A", explanation="Clear boundaries and objective SLA options resolve ownership disputes."),
            _mcq(q_set="C", category="executive_writing", difficulty="Easy", text="Why should abbreviations like 'RBAC' or 'TTL' be spelled out on first mention in cross-team docs?", options=["Ensures new joinees and non-specialist readers share exact terminology", "Increases word count artificially", "Required only in academic essays", "Prevents PDF export"], answer="A", explanation="Defining acronyms on first use eliminates onboarding friction."),
            _mcq(q_set="C", category="clarity_coherence", difficulty="Hard", text="Which revision fixes a run-on comma splice?", options=["The build succeeded; however, the smoke test failed.", "The build succeeded, the smoke test failed.", "The build succeeded the smoke test failed.", "The build succeeded, however the smoke test failed."], answer="A", explanation="Semicolon + conjunctive adverb properly joins two independent clauses."),
            _mcq(q_set="C", category="grammar_precision", difficulty="Medium", text="Choose the correct usage of 'fewer' vs 'less':", options=["The refactored service makes fewer queries and consumes less memory.", "The refactored service makes less queries and consumes fewer memory.", "The refactored service makes fewer memory and less queries.", "Both words are interchangeable."], answer="A", explanation="'Fewer' modifies countable nouns (queries); 'less' modifies uncountable nouns (memory)."),
            _mcq(q_set="C", category="scenario_response", difficulty="Medium", text="When requesting feedback on a long architecture doc, how do you get faster high-value reviews?", options=["Highlight the 2–3 open decisions you specifically want reviewers to weigh in on.", "Drop a link with 'thoughts?' and zero context.", "Ask for approval within 2 minutes.", "Disable document comments."], answer="A", explanation="Directing reviewers to specific decisions yields sharper feedback."),
            _mcq(q_set="C", category="executive_writing", difficulty="Hard", text="What belongs in the Executive Summary of a quarterly engineering review?", options=["Top business outcomes, key delivery milestones, headline metrics, and strategic priorities for next quarter", "Every individual git commit message", "Raw server stack traces", "Unedited meeting transcripts"], answer="A", explanation="Executive summaries synthesize outcomes, metrics, and forward priorities."),
            _mcq(q_set="C", category="clarity_coherence", difficulty="Easy", text="Which UI button label is clearest for a destructive action?", options=["Delete Batch Permanently", "OK", "Submit", "Continue"], answer="A", explanation="Explicit verb + object labels prevent accidental destructive clicks."),
            _mcq(q_set="C", category="grammar_precision", difficulty="Medium", text="Choose the sentence with proper subject-pronoun agreement:", options=["Every team must update its escalation roster before the holiday.", "Every team must update their rosters individually of itself.", "Every teams must update its roster.", "Each team updating its roster."], answer="A", explanation="Singular 'Every team' agrees cleanly with 'its'."),
            _mcq(q_set="C", category="scenario_response", difficulty="Easy", text="What is the best structure for a high-signal bug report?", options=["Environment, exact reproduction steps, expected behavior, actual behavior, and logs/screenshot", "Only 'it is broken'", "A vague screenshot with no steps", "Speculating about unrelated modules"], answer="A", explanation="Reproducible context cuts triage time dramatically."),
            _mcq(q_set="C", category="executive_writing", difficulty="Medium", text="How do you keep a technical onboarding guide maintainable over time?", options=["Keep steps modular, link to canonical sources of truth, and review during each cohort kickoff", "Duplicate static screenshots in 10 separate docs", "Never update docs after launch", "Embed expired tokens in examples"], answer="A", explanation="Single-source-of-truth modular docs prevent staleness."),
            _mcq(q_set="C", category="clarity_coherence", difficulty="Medium", text="Which phrasing is most direct and professional?", options=["Please confirm the schema freeze by Wednesday 3 PM IST.", "Would it maybe be at all possible if someone could potentially check this sometime?", "Confirm this now!!", "Just pinging again..."], answer="A", explanation="Polite, direct phrasing with a clear deadline works best."),
            _mcq(q_set="C", category="grammar_precision", difficulty="Hard", text="Select the sentence that uses 'compliment' vs 'complement' accurately:", options=["Automated telemetry complements unit testing by surfacing production anomalies.", "Automated telemetry compliments unit testing by surfacing anomalies.", "Telemetry is a nice complement of praise.", "Unit tests complimentary telemetry."], answer="A", explanation="'Complement' means to complete or enhance together; 'compliment' means praise."),
            _mcq(q_set="C", category="scenario_response", difficulty="Medium", text="When summarizing a completed sprint for stakeholders, what builds maximum confidence?", options=["Demo-ready outcomes tied to user goals, honest callout of carry-overs, and next sprint focus", "Hiding incomplete stories", "Listing only story point totals without deliverables", "Using unexplained internal ticket IDs only"], answer="A", explanation="Outcome-focused transparency builds lasting stakeholder trust."),
        ],
    }


# ---------------------------------------------------------------------------
# 9. ALGORITHMS & COMPLEXITY — 3 COMPLETE DISTINCT SETS (20 Qs each)
# ---------------------------------------------------------------------------

def _build_algorithm_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "A": [
            _mcq(q_set="A", category="time_space_complexity", difficulty="Easy", text="What is the Big-O time complexity of nested loops where both run from 1 to n?", options=["O(n)", "O(n log n)", "O(n^2)", "O(2^n)"], answer="C", explanation="n * n iterations yield O(n^2)."),
            _mcq(q_set="A", category="time_space_complexity", difficulty="Medium", text="What is the time complexity of `T(n) = 2T(n/2) + O(n)` by the Master Theorem?", options=["O(n)", "O(n log n)", "O(n^2)", "O(log n)"], answer="B", explanation="Case 2 of Master Theorem (a=2, b=2, f(n)=n) gives O(n log n)."),
            _mcq(q_set="A", category="time_space_complexity", difficulty="Hard", text="What is the amortized time complexity of appending to a dynamic array that doubles capacity on overflow?", options=["O(1)", "O(log n)", "O(n)", "O(n log n)"], answer="A", explanation="Geometric resizing yields O(1) amortized append cost."),
            _mcq(q_set="A", category="time_space_complexity", difficulty="Medium", text="Which growth rate grows FASTEST as n approaches infinity?", options=["O(n^3)", "O(2^n)", "O(n log n)", "O(n^2)"], answer="B", explanation="Exponential O(2^n) asymptotically dominates all polynomials."),
            _mcq(q_set="A", category="time_space_complexity", difficulty="Easy", text="What is the auxiliary space complexity of an in-place iterative array reversal?", options=["O(1)", "O(log n)", "O(n)", "O(n^2)"], answer="A", explanation="Swapping symmetric indices uses constant extra pointers."),
            _mcq(q_set="A", category="algorithm_design", difficulty="Easy", text="Which paradigm chooses the locally optimal choice at each step hoping for a global optimum?", options=["Greedy Algorithm", "Backtracking", "Brute Force", "Randomized Walk"], answer="A", explanation="Greedy algorithms make locally optimal choices at each stage."),
            _mcq(q_set="A", category="algorithm_design", difficulty="Medium", text="What problem does Kadane's algorithm solve in O(n) time?", options=["Maximum sum contiguous subarray", "Shortest path with negative edges", "Matrix inversion", "Prime factorization"], answer="A", explanation="Kadane's tracks best subarray ending at each index in O(n)."),
            _mcq(q_set="A", category="algorithm_design", difficulty="Medium", text="Which technique reduces checking subarray sums from O(n) per query to O(1) per query?", options=["Prefix Sum Array", "Bubble Sort", "Depth-First Search", "Binary Heap"], answer="A", explanation="rangeSum(l, r) = prefix[r+1] - prefix[l] in O(1)."),
            _mcq(q_set="A", category="algorithm_design", difficulty="Hard", text="How does QuickSelect find the k-th smallest element in O(n) average time?", options=["Partitions like QuickSort but recurses only into the side containing index k", "Sorts the entire array twice", "Uses BFS on a heap", "Computes all permutations"], answer="A", explanation="Recursing into only one partition gives n + n/2 + n/4... = O(n) average."),
            _mcq(q_set="A", category="algorithm_design", difficulty="Medium", text="When is Counting Sort able to sort n integers in O(n + k) linear time?", options=["When integer keys lie in a small bounded range [0..k]", "When inputs are arbitrary floating-point numbers", "Only when k > n^3", "Never"], answer="A", explanation="Non-comparison counting beats O(n log n) when range k is small."),
            _mcq(q_set="A", category="recursion_dp", difficulty="Easy", text="What happens if a recursive function lacks a reachable base case?", options=["Stack Overflow / RecursionError", "O(1) instant return", "Automatic conversion to iteration", "Garbage collection speeds up"], answer="A", explanation="Unbounded recursion exhausts the call stack."),
            _mcq(q_set="A", category="recursion_dp", difficulty="Medium", text="What are the two essential properties for Dynamic Programming applicability?", options=["Optimal substructure and overlapping subproblems", "Random inputs and unsorted keys", "Negative cycles and disconnected graphs", "Constant array length only"], answer="A", explanation="DP caches solutions to overlapping subproblems with optimal substructure."),
            _mcq(q_set="A", category="recursion_dp", difficulty="Medium", text="What is the time complexity of naive recursive Fibonacci `fib(n) = fib(n-1) + fib(n-2)` without memoization?", options=["O(n)", "O(n log n)", "O(2^n)", "O(log n)"], answer="C", explanation="Without memoization, overlapping calls explode exponentially (~1.618^n / O(2^n))."),
            _mcq(q_set="A", category="recursion_dp", difficulty="Hard", text="In the 0/1 Knapsack DP problem with N items and capacity W, what is the standard time complexity?", options=["O(N * W)", "O(N + W)", "O(N log W)", "O(W^2)"], answer="A", explanation="Filling the N x W state table runs in O(N * W) pseudo-polynomial time."),
            _mcq(q_set="A", category="recursion_dp", difficulty="Medium", text="What distinguishes bottom-up tabulation from top-down memoization?", options=["Tabulation fills DP states iteratively in dependency order without recursion stack overhead", "Tabulation cannot solve 2D DP", "Memoization is always iterative", "Tabulation requires random pivots"], answer="A", explanation="Tabulation builds base cases upward iteratively."),
            _mcq(q_set="A", category="graphs_trees", difficulty="Easy", text="What is the maximum number of nodes at depth d (root at d=0) in a binary tree?", options=["2^d", "d^2", "2d", "d!"], answer="A", explanation="Each level doubles capacity: 1, 2, 4, 8... = 2^d."),
            _mcq(q_set="A", category="graphs_trees", difficulty="Medium", text="Which graph algorithm handles negative edge weights and detects negative cycles?", options=["Bellman-Ford Algorithm", "Dijkstra's Algorithm", "BFS", "Prim's Algorithm"], answer="A", explanation="Bellman-Ford relaxes all edges V-1 times and detects negative cycles on pass V."),
            _mcq(q_set="A", category="graphs_trees", difficulty="Medium", text="What is the time complexity of Breadth-First Search on a graph with V vertices and E edges using an adjacency list?", options=["O(V + E)", "O(V * E)", "O(V^2)", "O(E log V)"], answer="A", explanation="Each vertex and edge is visited at most once -> O(V + E)."),
            _mcq(q_set="A", category="graphs_trees", difficulty="Hard", text="Which data structure supports near-O(1) amortized `union` and `find` for connected components?", options=["Disjoint Set Union (Union-Find) with path compression & union by rank", "Singly Linked List", "Stack", "Binary Search on unsorted array"], answer="A", explanation="Path compression + union by rank achieves O(alpha(n)) amortized time."),
            _mcq(q_set="A", category="graphs_trees", difficulty="Medium", text="In an unweighted graph, which traversal guarantees finding the shortest path (fewest edges) from source s?", options=["Breadth-First Search (BFS)", "Depth-First Search (DFS)", "Post-order DFS", "Random Walk"], answer="A", explanation="BFS explores vertices in increasing order of hop distance."),
        ],
        "B": [
            _mcq(q_set="B", category="time_space_complexity", difficulty="Easy", text="What is the time complexity of a loop that divides `n` by 2 on every iteration?", options=["O(1)", "O(log n)", "O(n)", "O(n log n)"], answer="B", explanation="Halving n repeatedly completes in log2(n) steps."),
            _mcq(q_set="B", category="time_space_complexity", difficulty="Medium", text="What is the worst-case time complexity of building a binary heap from an unsorted array of n elements using Floyd's heapify?", options=["O(n)", "O(n log n)", "O(n^2)", "O(log n)"], answer="A", explanation="Bottom-up sift-down heap construction sums to O(n) linear time."),
            _mcq(q_set="B", category="time_space_complexity", difficulty="Hard", text="What is the space complexity of Merge Sort on an array of size n?", options=["O(1)", "O(log n)", "O(n)", "O(n^2)"], answer="C", explanation="Standard array Merge Sort allocates an O(n) auxiliary merge buffer."),
            _mcq(q_set="B", category="time_space_complexity", difficulty="Medium", text="What is the lower bound for comparison-based sorting algorithms in the worst case?", options=["Omega(n)", "Omega(n log n)", "Omega(n^2)", "Omega(log n)"], answer="B", explanation="Decision tree height for n! permutations is Omega(n log n)."),
            _mcq(q_set="B", category="time_space_complexity", difficulty="Easy", text="If an algorithm executes 5n + 100 operations, what is its tight Big-O bound?", options=["O(1)", "O(n)", "O(100n)", "O(n^2)"], answer="B", explanation="Constant factors and lower-order terms drop in Big-O -> O(n)."),
            _mcq(q_set="B", category="algorithm_design", difficulty="Easy", text="Which classic problem is solved optimally by a greedy strategy sorting activities by earliest finish time?", options=["Activity / Interval Scheduling Maximization", "0/1 Knapsack", "Traveling Salesperson", "Subset Sum"], answer="A", explanation="Picking earliest finishing non-overlapping intervals maximizes count."),
            _mcq(q_set="B", category="algorithm_design", difficulty="Medium", text="What technique solves 'merge overlapping intervals' cleanly in O(n log n) time?", options=["Sort intervals by start time, then scan and merge overlapping endpoints", "Run Bellman-Ford", "Build a Trie", "Use nested O(n^3) loops"], answer="A", explanation="Sorting by start time allows single-pass linear merging."),
            _mcq(q_set="B", category="algorithm_design", difficulty="Medium", text="How does Boyer-Moore Voting Algorithm find a strict majority element (> n/2 occurrences) in O(n) time and O(1) space?", options=["Maintains a candidate and counter, incrementing on match and decrementing on mismatch", "Sorts the array first", "Builds a frequency HashMap of size n", "Uses binary search"], answer="A", explanation="Pairing distinct elements cancels non-majority values cleanly."),
            _mcq(q_set="B", category="algorithm_design", difficulty="Hard", text="What is Binary Search on the Answer (parametric search)?", options=["Applying binary search over a monotonic feasible solution range (e.g., minimum capacity to ship in D days)", "Searching only binary strings of 0s and 1s", "Sorting boolean arrays", "Hashing midpoint indices"], answer="A", explanation="Whenever feasibility is monotonic, binary search finds the optimal threshold in O(log R)."),
            _mcq(q_set="B", category="algorithm_design", difficulty="Medium", text="Which technique finds the next greater element for every array item in O(n) time?", options=["Monotonic Stack", "Selection Sort", "BFS", "Trie"], answer="A", explanation="A monotonic stack pops smaller elements in O(n) total operations."),
            _mcq(q_set="B", category="recursion_dp", difficulty="Easy", text="In 'Climbing Stairs' (1 or 2 steps at a time), `ways(n)` equals:", options=["ways(n-1) + ways(n-2)", "ways(n-1) * 2", "n^2", "n / 2"], answer="A", explanation="You reach step n from either n-1 or n-2."),
            _mcq(q_set="B", category="recursion_dp", difficulty="Medium", text="What is the standard DP time complexity for Longest Common Subsequence (LCS) of strings of lengths m and n?", options=["O(m + n)", "O(m * n)", "O(m log n)", "O(2^m)"], answer="B", explanation="2D table of size (m+1) x (n+1) computes LCS in O(m * n)."),
            _mcq(q_set="B", category="recursion_dp", difficulty="Medium", text="How can 1D/2D DP space complexity often be reduced when row `i` only depends on row `i-1`?", options=["Rolling array keeping only the previous and current rows", "Increasing recursion depth", "Switching to unsorted sets", "Doubling the matrix size"], answer="A", explanation="Rolling two rows cuts O(m * n) space down to O(n)."),
            _mcq(q_set="B", category="recursion_dp", difficulty="Hard", text="What is the time complexity of finding Longest Increasing Subsequence (LIS) using patience sorting / binary search?", options=["O(n)", "O(n log n)", "O(n^2)", "O(2^n)"], answer="B", explanation="Maintaining minimal tail values with binary search solves LIS in O(n log n)."),
            _mcq(q_set="B", category="recursion_dp", difficulty="Medium", text="Which technique systematically explores and prunes invalid states in N-Queens or Sudoku?", options=["Backtracking", "Prefix Sums", "Counting Sort", "Linear Hashing"], answer="A", explanation="Backtracking abandons partial candidates as soon as constraints fail."),
            _mcq(q_set="B", category="graphs_trees", difficulty="Easy", text="A connected undirected graph with V vertices and NO cycles has exactly how many edges?", options=["V - 1", "V", "V + 1", "2V"], answer="A", explanation="A tree on V vertices always has V - 1 edges."),
            _mcq(q_set="B", category="graphs_trees", difficulty="Medium", text="Which algorithm computes all-pairs shortest paths in O(V^3) time?", options=["Floyd-Warshall Algorithm", "Kruskal's Algorithm", "Binary Search", "Kadane's Algorithm"], answer="A", explanation="Floyd-Warshall uses 3 nested loops over intermediate vertices k."),
            _mcq(q_set="B", category="graphs_trees", difficulty="Medium", text="What is the time complexity of Dijkstra's algorithm using a binary min-heap on an adjacency list?", options=["O((V + E) log V)", "O(V^3)", "O(1)", "O(2^V)"], answer="A", explanation="Each edge relaxation and vertex pop takes O(log V)."),
            _mcq(q_set="B", category="graphs_trees", difficulty="Hard", text="How does Kahn's algorithm detect a cycle in a directed graph during topological sort?", options=["Fewer than V nodes are popped because remaining nodes keep in-degree > 0", "All nodes have in-degree 0 initially", "Edge weights become negative", "BFS queue overflows memory"], answer="A", explanation="Cyclic vertices never reach in-degree 0, leaving processed count < V."),
            _mcq(q_set="B", category="graphs_trees", difficulty="Medium", text="What defines a Bipartite Graph?", options=["Vertices can be 2-colored such that no adjacent vertices share the same color (equivalently, no odd cycles)", "Every vertex has degree 2", "The graph has exactly 2 edges", "All edges are directed"], answer="A", explanation="BFS/DFS 2-coloring checks bipartiteness in O(V + E)."),
        ],
        "C": [
            _mcq(q_set="C", category="time_space_complexity", difficulty="Easy", text="What is the time complexity of finding the minimum value in an unsorted array of n elements?", options=["O(1)", "O(log n)", "O(n)", "O(n log n)"], answer="C", explanation="Every element must be inspected at least once -> O(n)."),
            _mcq(q_set="C", category="time_space_complexity", difficulty="Medium", text="What is the time complexity of `T(n) = T(n/2) + O(1)`?", options=["O(1)", "O(log n)", "O(n)", "O(n log n)"], answer="B", explanation="Matches binary search recurrence -> O(log n)."),
            _mcq(q_set="C", category="time_space_complexity", difficulty="Hard", text="What is the time complexity of generating all subsets (power set) of a set of size n?", options=["O(n^2)", "O(n * 2^n)", "O(n log n)", "O(n^3)"], answer="B", explanation="There are 2^n subsets, each taking up to O(n) to copy -> O(n * 2^n)."),
            _mcq(q_set="C", category="time_space_complexity", difficulty="Medium", text="Which notation denotes an asymptotic LOWER bound?", options=["Big-O", "Big-Omega (Ω)", "Small-o", "Constant c"], answer="B", explanation="Big-Omega describes asymptotic lower bounds."),
            _mcq(q_set="C", category="time_space_complexity", difficulty="Easy", text="What is the space complexity of storing an adjacency matrix for V vertices?", options=["O(V)", "O(V + E)", "O(V^2)", "O(log V)"], answer="C", explanation="A V x V boolean/weight matrix consumes O(V^2) space."),
            _mcq(q_set="C", category="algorithm_design", difficulty="Easy", text="Which paradigm splits a problem into independent subproblems, solves them recursively, and combines results?", options=["Divide and Conquer", "Linear Scan", "Greedy Only", "Brute Force"], answer="A", explanation="Merge Sort and QuickSort are classic Divide and Conquer algorithms."),
            _mcq(q_set="C", category="algorithm_design", difficulty="Medium", text="Which technique maintains a dynamic window `[left, right]` to find minimum-length subarrays meeting a sum target?", options=["Variable-Size Sliding Window", "Matrix Multiplication", "Prim's Algorithm", "Topological Sort"], answer="A", explanation="Expanding right and shrinking left finds the minimum window in O(n)."),
            _mcq(q_set="C", category="algorithm_design", difficulty="Medium", text="Which algorithm constructs optimal variable-length prefix codes for lossless compression?", options=["Huffman Coding", "Dijkstra's Algorithm", "Selection Sort", "Floyd's Cycle Detection"], answer="A", explanation="Huffman greedily merges the two lowest-frequency nodes via a min-heap."),
            _mcq(q_set="C", category="algorithm_design", difficulty="Hard", text="Which string-matching algorithm uses a prefix-function (LPS) array to search a pattern in O(n + m) worst-case time?", options=["Knuth-Morris-Pratt (KMP)", "Naive double-loop scan", "QuickSort", "Kruskal's MST"], answer="A", explanation="KMP avoids re-checking matched characters via the LPS table."),
            _mcq(q_set="C", category="algorithm_design", difficulty="Medium", text="How do you merge k sorted linked lists of N total nodes in O(N log k) time?", options=["Maintain a min-heap of size k holding the current head of each list", "Concatenate all lists and run Bubble Sort", "Run DFS k times", "Use a stack of size N"], answer="A", explanation="Extracting min and pushing next takes O(log k) per node -> O(N log k)."),
            _mcq(q_set="C", category="recursion_dp", difficulty="Easy", text="In Coin Change (minimum coins to make amount A), why does a greedy choice sometimes fail on arbitrary coin systems (e.g., coins [1, 3, 4], amount 6)?", options=["Greedy picks 4+1+1 (3 coins) instead of optimal 3+3 (2 coins)", "Greedy cannot add integers", "DP cannot handle coin value 1", "Amount 6 is impossible"], answer="A", explanation="Non-canonical coin sets require DP to guarantee global optimality."),
            _mcq(q_set="C", category="recursion_dp", difficulty="Medium", text="What does Edit Distance (Levenshtein Distance) DP compute?", options=["Minimum insertions, deletions, and substitutions to transform string A into string B", "Maximum common prefix length", "Alphabetical order of strings", "Hash collision rate"], answer="A", explanation="Levenshtein DP quantifies minimum single-character edit operations."),
            _mcq(q_set="C", category="recursion_dp", difficulty="Medium", text="What is tail recursion?", options=["A recursive call that is the final action performed before returning, enabling stack-frame reuse", "Recursion that never terminates", "Calling two functions in parallel", "Using a loop inside a try block"], answer="A", explanation="Tail-call optimization reuses the current stack frame when supported."),
            _mcq(q_set="C", category="recursion_dp", difficulty="Hard", text="In House Robber DP (cannot rob adjacent houses), what is the recurrence for `dp[i]`?", options=["max(dp[i-1], dp[i-2] + nums[i])", "dp[i-1] + nums[i]", "min(dp[i-1], dp[i-2])", "nums[i] * i"], answer="A", explanation="Either skip house i (`dp[i-1]`) or rob it plus best up to `i-2`."),
            _mcq(q_set="C", category="recursion_dp", difficulty="Medium", text="What is the state space size for computing unique paths in an m x n grid moving only right or down?", options=["O(m * n) states (optimizable to O(min(m, n)) space)", "O(2^(m+n)) states", "O(1) states only", "O(m^3) states"], answer="A", explanation="Each grid cell `(r, c)` sums paths from top and left."),
            _mcq(q_set="C", category="graphs_trees", difficulty="Easy", text="What is the Lowest Common Ancestor (LCA) of two nodes u and v in a rooted tree?", options=["The deepest node that has both u and v as descendants", "The root node always", "The leaf with smallest value", "The sibling of u"], answer="A", explanation="LCA is the lowest/deepest shared ancestor of u and v."),
            _mcq(q_set="C", category="graphs_trees", difficulty="Medium", text="Which MST algorithm grows a single tree starting from an arbitrary vertex by picking the cheapest outgoing edge?", options=["Prim's Algorithm", "Bellman-Ford", "KMP", "QuickSelect"], answer="A", explanation="Prim's expands the connected MST frontier via a min-heap."),
            _mcq(q_set="C", category="graphs_trees", difficulty="Medium", text="How do you serialize/check if a binary tree is height-balanced in O(n) single pass?", options=["Return subtree height bottom-up and propagate -1 immediately if |left - right| > 1", "Recompute height from every node in O(n^2)", "Sort node values", "Count only leaf nodes"], answer="A", explanation="Bottom-up DFS checks balance and height simultaneously in O(n)."),
            _mcq(q_set="C", category="graphs_trees", difficulty="Hard", text="Which algorithm finds Strongly Connected Components (SCCs) of a directed graph in O(V + E) time?", options=["Tarjan's / Kosaraju's Algorithm", "Binary Search", "Merge Sort", "Floyd-Warshall"], answer="A", explanation="Both Tarjan's and Kosaraju's compute SCCs in linear O(V + E) time."),
            _mcq(q_set="C", category="graphs_trees", difficulty="Medium", text="In a Segment Tree over an array of length n, what is the time complexity of a range sum query and point update?", options=["O(log n) for both", "O(n) for both", "O(1) query and O(n^2) update", "O(n log n) for both"], answer="A", explanation="Segment trees perform point updates and range queries in O(log n)."),
        ],
    }


def get_comprehension_default_questions(question_set: str | None = None) -> list[dict[str, Any]]:
    sets = _build_comprehension_sets()
    if question_set:
        norm = normalize_question_set(question_set)
        return list(sets.get(norm, sets["A"]))
    return sets["A"] + sets["B"] + sets["C"]


def _get_baseline_set_a(domain: str) -> list[dict[str, Any]]:
    """Loads existing baseline Set A pools lazily to avoid circular imports."""
    if domain == "logical_reasoning":
        from services.training.app.services.assessment_logical_reasoning import (
            get_default_logical_reasoning_questions,
        )
        return _tag_set(get_default_logical_reasoning_questions(), "A")

    if domain == "english_grammar":
        from services.training.app.services.assessment_grammar_technical import (
            get_default_english_grammar_questions,
        )
        return _tag_set(get_default_english_grammar_questions(), "A")

    if domain == "technical":
        from services.training.app.services.assessment_grammar_technical import (
            get_default_technical_questions,
        )
        return _tag_set(get_default_technical_questions(), "A")

    if domain == "psychometric":
        from services.training.app.services.assessment_mock import (
            generate_mock_questions,
        )
        return _tag_set(generate_mock_questions(), "A")

    return []


def get_multi_set_questions(
    assessment_type: str,
    question_set: str = "A",
) -> list[dict[str, Any]]:
    """Returns distinct builtin question pool for `(assessment_type, question_set in A/B/C)`.

    Every one of the 9 assessment categories is guaranteed to return a non-empty,
    non-overlapping question set for Set A, Set B, and Set C.
    """
    q_set = normalize_question_set(question_set)
    domain = (assessment_type or "psychometric").lower().strip()

    if domain == "comprehension":
        return get_comprehension_default_questions(q_set)

    if domain == "cognitive":
        cog = _build_cognitive_sets()
        return list(cog.get(q_set, cog["A"]))

    if domain == "programming":
        prog = _build_programming_sets()
        return list(prog.get(q_set, prog["A"]))

    if domain == "algorithm":
        alg = _build_algorithm_sets()
        return list(alg.get(q_set, alg["A"]))

    if domain == "composition":
        comp = _build_composition_sets()
        return list(comp.get(q_set, comp["A"]))

    if domain == "logical_reasoning":
        if q_set == "A":
            return _get_baseline_set_a("logical_reasoning")
        return list(_build_logical_extra_sets()[q_set])

    if domain == "english_grammar":
        if q_set == "A":
            return _get_baseline_set_a("english_grammar")
        return list(_build_english_grammar_extra_sets()[q_set])

    if domain == "technical":
        if q_set == "A":
            return _get_baseline_set_a("technical")
        return list(_build_technical_extra_sets()[q_set])

    # Default / psychometric
    if q_set == "A":
        return _get_baseline_set_a("psychometric")
    return list(_build_psychometric_extra_sets()[q_set])


def get_all_sets_questions(assessment_type: str) -> list[dict[str, Any]]:
    """Returns all 3 sets (Set A + Set B + Set C) combined for bank population."""
    combined: list[dict[str, Any]] = []
    for q_set in VALID_SETS:
        combined.extend(get_multi_set_questions(assessment_type, q_set))
    return combined
