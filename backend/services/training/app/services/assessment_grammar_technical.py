"""Default built-in question banks for English Grammar and Technical Assessments.

Ensures that English Grammar and Technical assessments can always start instantly
with 20 rich, diverse, enterprise-standard MCQs even before manual questions
are added by faculty/administrators.
"""

# ==============================================================================
# 1. ENGLISH GRAMMAR ASSESSMENT (20 Questions)
# ==============================================================================

ENGLISH_GRAMMAR_QUESTIONS = [
    # Category: Subject-Verb Agreement (3 questions)
    {
        "id_num": 1,
        "category": "subject_verb_agreement",
        "difficulty": "Easy",
        "question_text": "Choose the sentence with correct subject-verb agreement:",
        "options": [
            {"id": "A", "text": "Each of the new employees have completed their safety briefing."},
            {"id": "B", "text": "Each of the new employees has completed their safety briefing."},
            {"id": "C", "text": "Each of the new employees were completed their safety briefing."},
            {"id": "D", "text": "Each of the new employees are completed their safety briefing."},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 2,
        "category": "subject_verb_agreement",
        "difficulty": "Medium",
        "question_text": "Neither the project manager nor the team leads _____ available for the status call.",
        "options": [
            {"id": "A", "text": "was"},
            {"id": "B", "text": "is"},
            {"id": "C", "text": "are"},
            {"id": "D", "text": "be"},
        ],
        "correct_answer": "C",
        "max_score": 1.0,
    },
    {
        "id_num": 3,
        "category": "subject_verb_agreement",
        "difficulty": "Hard",
        "question_text": "The committee, along with several external auditors, _____ presented its final audit report.",
        "options": [
            {"id": "A", "text": "have"},
            {"id": "B", "text": "has"},
            {"id": "C", "text": "are"},
            {"id": "D", "text": "were"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },

    # Category: Tenses & Aspects (3 questions)
    {
        "id_num": 4,
        "category": "tenses_and_aspects",
        "difficulty": "Easy",
        "question_text": "By the time the client arrived, the engineering team _____ the release deployment.",
        "options": [
            {"id": "A", "text": "already finished"},
            {"id": "B", "text": "had already finished"},
            {"id": "C", "text": "has already finished"},
            {"id": "D", "text": "was already finished"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 5,
        "category": "tenses_and_aspects",
        "difficulty": "Medium",
        "question_text": "Next quarter, our development team _____ on this microservices platform for three years.",
        "options": [
            {"id": "A", "text": "will have been working"},
            {"id": "B", "text": "will be worked"},
            {"id": "C", "text": "has been working"},
            {"id": "D", "text": "had worked"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },
    {
        "id_num": 6,
        "category": "tenses_and_aspects",
        "difficulty": "Medium",
        "question_text": "If our server bandwidth _____ increased earlier, the outage would have been avoided.",
        "options": [
            {"id": "A", "text": "was"},
            {"id": "B", "text": "had been"},
            {"id": "C", "text": "has been"},
            {"id": "D", "text": "would have been"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },

    # Category: Prepositions & Phrasal Verbs (3 questions)
    {
        "id_num": 7,
        "category": "prepositions",
        "difficulty": "Easy",
        "question_text": "The company decided to comply _____ the newly updated European data privacy regulations.",
        "options": [
            {"id": "A", "text": "to"},
            {"id": "B", "text": "with"},
            {"id": "C", "text": "by"},
            {"id": "D", "text": "at"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 8,
        "category": "prepositions",
        "difficulty": "Medium",
        "question_text": "The security team was tasked with looking _____ the root cause of the firewall breach.",
        "options": [
            {"id": "A", "text": "over"},
            {"id": "B", "text": "into"},
            {"id": "C", "text": "after"},
            {"id": "D", "text": "around"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 9,
        "category": "prepositions",
        "difficulty": "Hard",
        "question_text": "His persistent refusal to compromise was incompatible _____ effective collaborative teamwork.",
        "options": [
            {"id": "A", "text": "with"},
            {"id": "B", "text": "to"},
            {"id": "C", "text": "from"},
            {"id": "D", "text": "against"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },

    # Category: Sentence Correction & Syntax (3 questions)
    {
        "id_num": 10,
        "category": "sentence_correction",
        "difficulty": "Easy",
        "question_text": "Identify the grammatically correct sentence:",
        "options": [
            {"id": "A", "text": "He suggested me to read the API documentation thoroughly."},
            {"id": "B", "text": "He suggested that I read the API documentation thoroughly."},
            {"id": "C", "text": "He suggested to me for reading the API documentation thoroughly."},
            {"id": "D", "text": "He suggested that I must to read the API documentation thoroughly."},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 11,
        "category": "sentence_correction",
        "difficulty": "Medium",
        "question_text": "Choose the sentence that does NOT contain a misplaced modifier:",
        "options": [
            {"id": "A", "text": "Running quickly to catch the shuttle, the badge slipped out of my pocket."},
            {"id": "B", "text": "While running quickly to catch the shuttle, my badge slipped out of my pocket."},
            {"id": "C", "text": "As I was running quickly to catch the shuttle, my badge slipped out of my pocket."},
            {"id": "D", "text": "Running quickly to catch the shuttle, my pocket lost its badge."},
        ],
        "correct_answer": "C",
        "max_score": 1.0,
    },
    {
        "id_num": 12,
        "category": "sentence_correction",
        "difficulty": "Hard",
        "question_text": "Identify the option with proper parallel grammatical structure:",
        "options": [
            {"id": "A", "text": "The lead engineer is responsible for designing architectures, writing clean code, and to review PRs."},
            {"id": "B", "text": "The lead engineer is responsible for designing architectures, writing clean code, and reviewing PRs."},
            {"id": "C", "text": "The lead engineer is responsible to design architectures, writing clean code, and reviewing PRs."},
            {"id": "D", "text": "The lead engineer is responsible for design architectures, to write clean code, and reviewing PRs."},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },

    # Category: Corporate Vocabulary & Usage (3 questions)
    {
        "id_num": 13,
        "category": "vocabulary",
        "difficulty": "Easy",
        "question_text": "Choose the most appropriate synonym for 'MITIGATE' in an enterprise risk context:",
        "options": [
            {"id": "A", "text": "Amplify"},
            {"id": "B", "text": "Alleviate / Reduce"},
            {"id": "C", "text": "Ignore"},
            {"id": "D", "text": "Complicate"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 14,
        "category": "vocabulary",
        "difficulty": "Medium",
        "question_text": "The CFO praised the finance division for their _____ management of capital expenditure during the downturn.",
        "options": [
            {"id": "A", "text": "judicious"},
            {"id": "B", "text": "reckless"},
            {"id": "C", "text": "arbitrary"},
            {"id": "D", "text": "negligent"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },
    {
        "id_num": 15,
        "category": "vocabulary",
        "difficulty": "Hard",
        "question_text": "What is the antonym of 'AMBIGUOUS'?",
        "options": [
            {"id": "A", "text": "Equivocal"},
            {"id": "B", "text": "Lucid / Explicit"},
            {"id": "C", "text": "Obscure"},
            {"id": "D", "text": "Enigmatic"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },

    # Category: Active/Passive Voice & Direct/Indirect (3 questions)
    {
        "id_num": 16,
        "category": "voice_and_speech",
        "difficulty": "Easy",
        "question_text": "Convert to passive voice: 'The senior architect reviewed the pull request.'",
        "options": [
            {"id": "A", "text": "The pull request was reviewed by the senior architect."},
            {"id": "B", "text": "The pull request has been reviewed by the senior architect."},
            {"id": "C", "text": "The pull request had reviewed by the senior architect."},
            {"id": "D", "text": "The pull request is reviewed by the senior architect."},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },
    {
        "id_num": 17,
        "category": "voice_and_speech",
        "difficulty": "Medium",
        "question_text": "She said, 'I have sent the deployment credentials.' Choose the correct indirect speech:",
        "options": [
            {"id": "A", "text": "She said that she has sent the deployment credentials."},
            {"id": "B", "text": "She said that she had sent the deployment credentials."},
            {"id": "C", "text": "She said that she will send the deployment credentials."},
            {"id": "D", "text": "She said that she was sent the deployment credentials."},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 18,
        "category": "voice_and_speech",
        "difficulty": "Hard",
        "question_text": "Identify the passive form: 'They are constructing a new cloud datacenter in Frankfurt.'",
        "options": [
            {"id": "A", "text": "A new cloud datacenter was constructed in Frankfurt."},
            {"id": "B", "text": "A new cloud datacenter is being constructed in Frankfurt."},
            {"id": "C", "text": "A new cloud datacenter has been constructing in Frankfurt."},
            {"id": "D", "text": "A new cloud datacenter will be constructed in Frankfurt."},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },

    # Category: Idioms & Professional Collocations (2 questions)
    {
        "id_num": 19,
        "category": "idioms_collocations",
        "difficulty": "Medium",
        "question_text": "In corporate communication, 'to touch base' means:",
        "options": [
            {"id": "A", "text": "To terminate an active agreement"},
            {"id": "B", "text": "To briefly make contact or confer on a topic"},
            {"id": "C", "text": "To hit the physical server baseline"},
            {"id": "D", "text": "To resign from a position"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 20,
        "category": "idioms_collocations",
        "difficulty": "Medium",
        "question_text": "The product launch went smoothly, and we managed to stay ahead of the _____.",
        "options": [
            {"id": "A", "text": "line"},
            {"id": "B", "text": "curve"},
            {"id": "C", "text": "track"},
            {"id": "D", "text": "loop"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
]


# ==============================================================================
# 2. TECHNICAL ASSESSMENT (20 Questions)
# ==============================================================================

TECHNICAL_QUESTIONS = [
    # Category: Data Structures & Algorithms (4 questions)
    {
        "id_num": 1,
        "category": "data_structures",
        "difficulty": "Easy",
        "question_text": "What is the average time complexity of looking up a key in a standard Hash Table?",
        "options": [
            {"id": "A", "text": "O(1)"},
            {"id": "B", "text": "O(log n)"},
            {"id": "C", "text": "O(n)"},
            {"id": "D", "text": "O(n log n)"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },
    {
        "id_num": 2,
        "category": "data_structures",
        "difficulty": "Medium",
        "question_text": "Which data structure follows the Last-In-First-Out (LIFO) operational principle?",
        "options": [
            {"id": "A", "text": "Queue"},
            {"id": "B", "text": "Stack"},
            {"id": "C", "text": "Binary Heap"},
            {"id": "D", "text": "Linked List"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 3,
        "category": "algorithms",
        "difficulty": "Medium",
        "question_text": "Which sorting algorithm guarantees O(n log n) worst-case time complexity?",
        "options": [
            {"id": "A", "text": "Quicksort"},
            {"id": "B", "text": "Merge Sort"},
            {"id": "C", "text": "Bubble Sort"},
            {"id": "D", "text": "Insertion Sort"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 4,
        "category": "algorithms",
        "difficulty": "Hard",
        "question_text": "In a balanced Binary Search Tree (AVL or Red-Black), what is the time complexity of searching an element?",
        "options": [
            {"id": "A", "text": "O(1)"},
            {"id": "B", "text": "O(log n)"},
            {"id": "C", "text": "O(n)"},
            {"id": "D", "text": "O(n^2)"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },

    # Category: Python Programming (4 questions)
    {
        "id_num": 5,
        "category": "python_programming",
        "difficulty": "Easy",
        "question_text": "In Python, which of the following data types is IMMUTABLE?",
        "options": [
            {"id": "A", "text": "list"},
            {"id": "B", "text": "dict"},
            {"id": "C", "text": "tuple"},
            {"id": "D", "text": "set"},
        ],
        "correct_answer": "C",
        "max_score": 1.0,
    },
    {
        "id_num": 6,
        "category": "python_programming",
        "difficulty": "Medium",
        "question_text": "What is the output of `bool([]) or bool([0])` in Python?",
        "options": [
            {"id": "A", "text": "False"},
            {"id": "B", "text": "True"},
            {"id": "C", "text": "None"},
            {"id": "D", "text": "ValueError"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 7,
        "category": "python_programming",
        "difficulty": "Medium",
        "question_text": "What keyword is used in Python to define a generator function?",
        "options": [
            {"id": "A", "text": "generate"},
            {"id": "B", "text": "yield"},
            {"id": "C", "text": "return"},
            {"id": "D", "text": "async"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 8,
        "category": "python_programming",
        "difficulty": "Hard",
        "question_text": "What does GIL stand for in CPython, and what is its primary effect?",
        "options": [
            {"id": "A", "text": "Global Interpreter Lock; restricts execution to one native thread at a time per interpreter"},
            {"id": "B", "text": "General Interface Library; manages OS level networking calls"},
            {"id": "C", "text": "Garbage Isolation Layer; cleans memory every 5 seconds"},
            {"id": "D", "text": "Global Index Lookup; accelerates dictionary keys"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },

    # Category: JavaScript & Modern Web (3 questions)
    {
        "id_num": 9,
        "category": "javascript_web",
        "difficulty": "Easy",
        "question_text": "Which JavaScript keyword declares a block-scoped variable that CANNOT be reassigned?",
        "options": [
            {"id": "A", "text": "var"},
            {"id": "B", "text": "let"},
            {"id": "C", "text": "const"},
            {"id": "D", "text": "static"},
        ],
        "correct_answer": "C",
        "max_score": 1.0,
    },
    {
        "id_num": 10,
        "category": "javascript_web",
        "difficulty": "Medium",
        "question_text": "What does `Promise.all([p1, p2, p3])` do if `p2` rejects?",
        "options": [
            {"id": "A", "text": "It waits for p1 and p3 before returning p2 error"},
            {"id": "B", "text": "It immediately rejects with the reason of p2 (fast-fail)"},
            {"id": "C", "text": "It ignores p2 and returns results of p1 and p3"},
            {"id": "D", "text": "It retries p2 three times"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 11,
        "category": "javascript_web",
        "difficulty": "Hard",
        "question_text": "In Angular, what is the primary benefit of Zoneless change detection?",
        "options": [
            {"id": "A", "text": "Eliminates zone.js monkey-patching overhead and enables fine-grained signal-driven DOM updates"},
            {"id": "B", "text": "Automatically compiles TypeScript into WebAssembly"},
            {"id": "C", "text": "Disables HTTP request error handling"},
            {"id": "D", "text": "Bypasses browser CORS policy"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },

    # Category: Databases & SQL (3 questions)
    {
        "id_num": 12,
        "category": "databases_sql",
        "difficulty": "Easy",
        "question_text": "Which SQL clause is used to filter records aggregated by a GROUP BY statement?",
        "options": [
            {"id": "A", "text": "WHERE"},
            {"id": "B", "text": "HAVING"},
            {"id": "C", "text": "ORDER BY"},
            {"id": "D", "text": "LIMIT"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 13,
        "category": "databases_sql",
        "difficulty": "Medium",
        "question_text": "In relational databases, what does the 'I' in the ACID transaction model stand for?",
        "options": [
            {"id": "A", "text": "Integrity"},
            {"id": "B", "text": "Isolation"},
            {"id": "C", "text": "Idempotency"},
            {"id": "D", "text": "Indexing"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 14,
        "category": "databases_sql",
        "difficulty": "Hard",
        "question_text": "What type of database index is typically used for range queries (e.g. BETWEEN or > / <)?",
        "options": [
            {"id": "A", "text": "Hash Index"},
            {"id": "B", "text": "B-Tree Index"},
            {"id": "C", "text": "Bitmap Index"},
            {"id": "D", "text": "Bloom Filter"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },

    # Category: System Design & Cloud Architecture (3 questions)
    {
        "id_num": 15,
        "category": "system_design",
        "difficulty": "Easy",
        "question_text": "What is the primary role of a Reverse Proxy (e.g. NGINX) in modern web architectures?",
        "options": [
            {"id": "A", "text": "Compiling backend source code"},
            {"id": "B", "text": "Load balancing, SSL termination, and routing client traffic to backend servers"},
            {"id": "C", "text": "Replacing database migrations"},
            {"id": "D", "text": "Encrypting disk volumes at rest"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 16,
        "category": "system_design",
        "difficulty": "Medium",
        "question_text": "Which architectural pattern decouples producers and consumers using asynchronous message brokers?",
        "options": [
            {"id": "A", "text": "Event-Driven Architecture (Pub/Sub)"},
            {"id": "B", "text": "Monolithic Shared Memory"},
            {"id": "C", "text": "Synchronous RPC"},
            {"id": "D", "text": "Client-Server Polling"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },
    {
        "id_num": 17,
        "category": "system_design",
        "difficulty": "Hard",
        "question_text": "According to the CAP Theorem, in the event of a network partition (P), a distributed system must choose between:",
        "options": [
            {"id": "A", "text": "Consistency (C) and Availability (A)"},
            {"id": "B", "text": "Performance and Security"},
            {"id": "C", "text": "Throughput and Latency"},
            {"id": "D", "text": "Storage and Compute"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },

    # Category: Git & Version Control (3 questions)
    {
        "id_num": 18,
        "category": "git_devops",
        "difficulty": "Easy",
        "question_text": "Which Git command switches to an existing branch named `feature/auth`?",
        "options": [
            {"id": "A", "text": "git switch feature/auth"},
            {"id": "B", "text": "git branch -d feature/auth"},
            {"id": "C", "text": "git merge feature/auth"},
            {"id": "D", "text": "git tag feature/auth"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },
    {
        "id_num": 19,
        "category": "git_devops",
        "difficulty": "Medium",
        "question_text": "What does `git cherry-pick <commit-hash>` do?",
        "options": [
            {"id": "A", "text": "Deletes the specified commit from branch history"},
            {"id": "B", "text": "Applies the changes from an existing commit onto the current working branch"},
            {"id": "C", "text": "Creates a new lightweight Git tag"},
            {"id": "D", "text": "Pushes only modified images to remote storage"},
        ],
        "correct_answer": "B",
        "max_score": 1.0,
    },
    {
        "id_num": 20,
        "category": "git_devops",
        "difficulty": "Hard",
        "question_text": "What is the difference between `git rebase` and `git merge`?",
        "options": [
            {"id": "A", "text": "Rebase re-applies commits on top of another base branch for a linear history, whereas merge joins histories with a merge commit"},
            {"id": "B", "text": "Rebase deletes uncommitted files, while merge saves them"},
            {"id": "C", "text": "Rebase works only with remote tags"},
            {"id": "D", "text": "Merge converts Git branches into Subversion commits"},
        ],
        "correct_answer": "A",
        "max_score": 1.0,
    },
]


def get_default_english_grammar_questions() -> list[dict]:
    """Return 20 formatted questions for English Grammar assessment."""
    formatted = []
    for q in ENGLISH_GRAMMAR_QUESTIONS:
        correct_id = q["correct_answer"]
        scoring_key = {
            opt["id"]: (q["max_score"] if opt["id"] == correct_id else 0.0)
            for opt in q["options"]
        }
        formatted.append({
            "category": q["category"],
            "difficulty": q["difficulty"],
            "question_type": "multiple_choice",
            "question_text": q["question_text"],
            "options": q["options"],
            "scoring_key": scoring_key,
            "max_score": q["max_score"],
        })
    return formatted


def get_default_technical_questions() -> list[dict]:
    """Return 20 formatted questions for Technical assessment."""
    formatted = []
    for q in TECHNICAL_QUESTIONS:
        correct_id = q["correct_answer"]
        scoring_key = {
            opt["id"]: (q["max_score"] if opt["id"] == correct_id else 0.0)
            for opt in q["options"]
        }
        formatted.append({
            "category": q["category"],
            "difficulty": q["difficulty"],
            "question_type": "multiple_choice",
            "question_text": q["question_text"],
            "options": q["options"],
            "scoring_key": scoring_key,
            "max_score": q["max_score"],
        })
    return formatted
