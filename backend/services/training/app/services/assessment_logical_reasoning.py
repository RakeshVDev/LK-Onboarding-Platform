"""Logical Reasoning Assessment - Fixed 25-Question Configuration.

Topic Distribution:
- Number Series: 4
- Alphabet Series: 3
- Coding-Decoding: 3
- Blood Relations: 3
- Direction and Distance: 3
- Pattern Recognition: 3
- Logical Statements: 2
- Odd One Out: 2
- Analogy: 2
Total: 25

Difficulty Distribution:
- Easy: 8 questions
- Medium: 12 questions
- Hard: 5 questions

Total Duration: 30 Minutes
Total Marks: 25 (1 mark per question, 0 negative marking)
"""

LOGICAL_REASONING_CATEGORIES = {
    "number_series": "Number Series",
    "alphabet_series": "Alphabet Series",
    "coding_decoding": "Coding-Decoding",
    "blood_relations": "Blood Relations",
    "direction_distance": "Direction and Distance",
    "pattern_recognition": "Pattern Recognition",
    "logical_statements": "Logical Statements",
    "odd_one_out": "Odd One Out",
    "analogy": "Analogy",
}

LOGICAL_REASONING_QUESTIONS = [
    # ----------------------------------------------------
    # 1. Number Series (4 Questions: 1 Easy, 2 Medium, 1 Hard)
    # ----------------------------------------------------
    {
        "id_num": 1,
        "category": "number_series",
        "difficulty": "Easy",
        "question_text": "Find the next number in the given series: 5, 10, 20, 40, ?",
        "options": [
            {"id": "A", "text": "60"},
            {"id": "B", "text": "70"},
            {"id": "C", "text": "80"},
            {"id": "D", "text": "90"},
        ],
        "correct_answer": "C",
        "explanation": "Each number is multiplied by 2 (5 * 2 = 10, 10 * 2 = 20, 20 * 2 = 40, 40 * 2 = 80).",
    },
    {
        "id_num": 2,
        "category": "number_series",
        "difficulty": "Medium",
        "question_text": "Find the next number in the series: 3, 7, 15, 31, 63, ?",
        "options": [
            {"id": "A", "text": "125"},
            {"id": "B", "text": "127"},
            {"id": "C", "text": "129"},
            {"id": "D", "text": "131"},
        ],
        "correct_answer": "B",
        "explanation": "Pattern: multiply by 2 and add 1 (3*2+1=7, 7*2+1=15, 15*2+1=31, 31*2+1=63, 63*2+1=127).",
    },
    {
        "id_num": 3,
        "category": "number_series",
        "difficulty": "Medium",
        "question_text": "Find the missing number in the sequence: 2, 6, 12, 20, 30, ?, 56",
        "options": [
            {"id": "A", "text": "40"},
            {"id": "B", "text": "42"},
            {"id": "C", "text": "44"},
            {"id": "D", "text": "46"},
        ],
        "correct_answer": "B",
        "explanation": "The differences between consecutive numbers increase by 2: +4, +6, +8, +10, +12, +14. 30 + 12 = 42, and 42 + 14 = 56.",
    },
    {
        "id_num": 4,
        "category": "number_series",
        "difficulty": "Hard",
        "question_text": "Determine the next number in the series: 2, 3, 10, 39, 172, ?",
        "options": [
            {"id": "A", "text": "885"},
            {"id": "B", "text": "865"},
            {"id": "C", "text": "845"},
            {"id": "D", "text": "825"},
        ],
        "correct_answer": "A",
        "explanation": "Pattern: multiply by n and add n^2: (2*1 + 1^2 = 3), (3*2 + 2^2 = 10), (10*3 + 3^2 = 39), (39*4 + 4^2 = 172), (172*5 + 5^2 = 860 + 25 = 885).",
    },

    # ----------------------------------------------------
    # 2. Alphabet Series (3 Questions: 1 Easy, 1 Medium, 1 Hard)
    # ----------------------------------------------------
    {
        "id_num": 5,
        "category": "alphabet_series",
        "difficulty": "Easy",
        "question_text": "What comes next in the alphabetical sequence: B, E, H, K, ?",
        "options": [
            {"id": "A", "text": "M"},
            {"id": "B", "text": "N"},
            {"id": "C", "text": "O"},
            {"id": "D", "text": "P"},
        ],
        "correct_answer": "B",
        "explanation": "Each letter advances by +3 positions in the alphabet: B(2) + 3 = E(5), E(5) + 3 = H(8), H(8) + 3 = K(11), K(11) + 3 = N(14).",
    },
    {
        "id_num": 6,
        "category": "alphabet_series",
        "difficulty": "Medium",
        "question_text": "Identify the next term in the series: AZ, CX, EV, GT, ?",
        "options": [
            {"id": "A", "text": "IR"},
            {"id": "B", "text": "HS"},
            {"id": "C", "text": "IS"},
            {"id": "D", "text": "JQ"},
        ],
        "correct_answer": "A",
        "explanation": "First letters increase by +2 (A, C, E, G, I); second letters decrease by -2 (Z, X, V, T, R). The next term is IR.",
    },
    {
        "id_num": 7,
        "category": "alphabet_series",
        "difficulty": "Hard",
        "question_text": "Find the missing term in the sequence: WFB, TGD, QHG, ?",
        "options": [
            {"id": "A", "text": "NIJ"},
            {"id": "B", "text": "NIK"},
            {"id": "C", "text": "OIK"},
            {"id": "D", "text": "NJJ"},
        ],
        "correct_answer": "B",
        "explanation": "1st letter: W(-3)->T(-3)->Q(-3)->N. 2nd letter: F(+1)->G(+1)->H(+1)->I. 3rd letter: B(+2)->D(+3)->G(+4)->K. Result is NIK.",
    },

    # ----------------------------------------------------
    # 3. Coding-Decoding (3 Questions: 1 Easy, 1 Medium, 1 Hard)
    # ----------------------------------------------------
    {
        "id_num": 8,
        "category": "coding_decoding",
        "difficulty": "Easy",
        "question_text": "In a certain code, 'COMPUTER' is written as 'DPNQVUGS'. Following the same rule, how is 'LAPTOP' written?",
        "options": [
            {"id": "A", "text": "MBQUPO"},
            {"id": "B", "text": "MBQUQP"},
            {"id": "C", "text": "NAQVQP"},
            {"id": "D", "text": "MCQUPO"},
        ],
        "correct_answer": "B",
        "explanation": "Each letter is shifted by +1: L->M, A->B, P->Q, T->U, O->P, P->Q, producing MBQUQP.",
    },
    {
        "id_num": 9,
        "category": "coding_decoding",
        "difficulty": "Medium",
        "question_text": "If 'GLOVE' is coded numerically as '7-12-15-22-5', how is 'SHIRT' coded in the same system?",
        "options": [
            {"id": "A", "text": "19-8-9-18-20"},
            {"id": "B", "text": "18-9-9-17-20"},
            {"id": "C", "text": "19-7-9-18-21"},
            {"id": "D", "text": "20-8-10-18-19"},
        ],
        "correct_answer": "A",
        "explanation": "Letters correspond directly to their standard alphabetical positions: S=19, H=8, I=9, R=18, T=20.",
    },
    {
        "id_num": 10,
        "category": "coding_decoding",
        "difficulty": "Hard",
        "question_text": "If 'ROAD' is coded as 'URDG' and 'SWAN' is coded as 'VZDO', how should 'BRIDGE' be coded?",
        "options": [
            {"id": "A", "text": "EUFDJH"},
            {"id": "B", "text": "DULHJJ"},
            {"id": "C", "text": "EULGJH"},
            {"id": "D", "text": "DTMGIG"},
        ],
        "correct_answer": "C",
        "explanation": "Each letter shifts forward by +3 positions: B->E, R->U, I->L, D->G, G->J, E->H, giving EULGJH.",
    },

    # ----------------------------------------------------
    # 4. Blood Relations (3 Questions: 1 Easy, 2 Medium)
    # ----------------------------------------------------
    {
        "id_num": 11,
        "category": "blood_relations",
        "difficulty": "Easy",
        "question_text": "Pointing to a photograph, Rohit said, 'She is the daughter of my grandfather's only son.' How is the girl related to Rohit?",
        "options": [
            {"id": "A", "text": "Sister"},
            {"id": "B", "text": "Mother"},
            {"id": "C", "text": "Cousin"},
            {"id": "D", "text": "Aunt"},
        ],
        "correct_answer": "A",
        "explanation": "Rohit's grandfather's only son is Rohit's father. The daughter of Rohit's father is Rohit's sister.",
    },
    {
        "id_num": 12,
        "category": "blood_relations",
        "difficulty": "Medium",
        "question_text": "A is the brother of B. B is the sister of C. C is the father of D. How is A related to D?",
        "options": [
            {"id": "A", "text": "Father"},
            {"id": "B", "text": "Paternal Uncle"},
            {"id": "C", "text": "Grandfather"},
            {"id": "D", "text": "Brother"},
        ],
        "correct_answer": "B",
        "explanation": "C is the father of D. A is the brother of C. Therefore, A is the paternal uncle of D.",
    },
    {
        "id_num": 13,
        "category": "blood_relations",
        "difficulty": "Medium",
        "question_text": "Introducing a man, a woman says, 'His wife is the only daughter of my father.' How is the man related to the woman?",
        "options": [
            {"id": "A", "text": "Brother"},
            {"id": "B", "text": "Father"},
            {"id": "C", "text": "Husband"},
            {"id": "D", "text": "Uncle"},
        ],
        "correct_answer": "C",
        "explanation": "The only daughter of the woman's father is the woman herself. Since his wife is the woman herself, the man is her husband.",
    },

    # ----------------------------------------------------
    # 5. Direction and Distance (3 Questions: 1 Easy, 1 Medium, 1 Hard)
    # ----------------------------------------------------
    {
        "id_num": 14,
        "category": "direction_distance",
        "difficulty": "Easy",
        "question_text": "A person walks 10 meters North, then turns right and walks 10 meters. In which direction is he now facing?",
        "options": [
            {"id": "A", "text": "North"},
            {"id": "B", "text": "South"},
            {"id": "C", "text": "East"},
            {"id": "D", "text": "West"},
        ],
        "correct_answer": "C",
        "explanation": "Facing North, a right turn of 90 degrees clockwise points directly East.",
    },
    {
        "id_num": 15,
        "category": "direction_distance",
        "difficulty": "Medium",
        "question_text": "Ravi walks 8 km South, then turns left and walks 6 km. How far is he from his initial starting point?",
        "options": [
            {"id": "A", "text": "14 km"},
            {"id": "B", "text": "10 km"},
            {"id": "C", "text": "12 km"},
            {"id": "D", "text": "8 km"},
        ],
        "correct_answer": "B",
        "explanation": "By Pythagoras theorem, distance = sqrt(8^2 + 6^2) = sqrt(64 + 36) = sqrt(100) = 10 km.",
    },
    {
        "id_num": 16,
        "category": "direction_distance",
        "difficulty": "Hard",
        "question_text": "Starting from point P, Priya walks 15 m West, turns right and walks 20 m. She turns right again and walks 30 m, and finally turns right and walks 20 m to reach point Q. How far and in which direction is point Q from point P?",
        "options": [
            {"id": "A", "text": "15 m East"},
            {"id": "B", "text": "15 m West"},
            {"id": "C", "text": "25 m North"},
            {"id": "D", "text": "45 m East"},
        ],
        "correct_answer": "A",
        "explanation": "Coordinates: P(0,0) -> (-15,0) -> (-15,20) -> (15,20) -> Q(15,0). Point Q is exactly 15 meters East of Point P.",
    },

    # ----------------------------------------------------
    # 6. Pattern Recognition (3 Questions: 1 Easy, 1 Medium, 1 Hard)
    # ----------------------------------------------------
    {
        "id_num": 17,
        "category": "pattern_recognition",
        "difficulty": "Easy",
        "question_text": "Identify the pattern and find the next element: 1A, 2B, 4D, 8H, ?",
        "options": [
            {"id": "A", "text": "12J"},
            {"id": "B", "text": "16P"},
            {"id": "C", "text": "16L"},
            {"id": "D", "text": "14N"},
        ],
        "correct_answer": "B",
        "explanation": "Numbers double (1, 2, 4, 8, 16); alphabetical positions double: A(1), B(2), D(4), H(8), P(16). Result is 16P.",
    },
    {
        "id_num": 18,
        "category": "pattern_recognition",
        "difficulty": "Medium",
        "question_text": "Observe the pattern: (2, 3, 13), (3, 4, 25), (4, 5, 41). Following this rule, what is the third number for (5, 6, ?)?",
        "options": [
            {"id": "A", "text": "55"},
            {"id": "B", "text": "61"},
            {"id": "C", "text": "65"},
            {"id": "D", "text": "71"},
        ],
        "correct_answer": "B",
        "explanation": "Rule: a^2 + b^2 = c. For (5, 6), 5^2 + 6^2 = 25 + 36 = 61.",
    },
    {
        "id_num": 19,
        "category": "pattern_recognition",
        "difficulty": "Hard",
        "question_text": "If 3 # 4 = 25, 4 # 5 = 41, and 5 # 2 = 29, what is the value of 6 # 7?",
        "options": [
            {"id": "A", "text": "85"},
            {"id": "B", "text": "92"},
            {"id": "C", "text": "84"},
            {"id": "D", "text": "76"},
        ],
        "correct_answer": "A",
        "explanation": "The operation is the sum of squares: x^2 + y^2. For 6 and 7: 6^2 + 7^2 = 36 + 49 = 85.",
    },

    # ----------------------------------------------------
    # 7. Logical Statements (2 Questions: 1 Medium, 1 Hard)
    # ----------------------------------------------------
    {
        "id_num": 20,
        "category": "logical_statements",
        "difficulty": "Medium",
        "question_text": "Statements: (1) All laptops are electronic devices. (2) Some electronic devices are portable. Which conclusion definitely follows?",
        "options": [
            {"id": "A", "text": "All portable devices are laptops."},
            {"id": "B", "text": "Some laptops are definitely portable."},
            {"id": "C", "text": "Some electronic devices are laptops."},
            {"id": "D", "text": "No laptops are electronic devices."},
        ],
        "correct_answer": "C",
        "explanation": "Since all laptops are electronic devices, the immediate converse 'Some electronic devices are laptops' is necessarily true.",
    },
    {
        "id_num": 21,
        "category": "logical_statements",
        "difficulty": "Medium",
        "question_text": "Statements: (1) Some managers are leaders. (2) All leaders are innovators. Conclusions: I. Some innovators are managers. II. All innovators are leaders. Which conclusion(s) logically follow?",
        "options": [
            {"id": "A", "text": "Only conclusion I follows"},
            {"id": "B", "text": "Only conclusion II follows"},
            {"id": "C", "text": "Both conclusion I and II follow"},
            {"id": "D", "text": "Neither conclusion follows"},
        ],
        "correct_answer": "A",
        "explanation": "Some managers are leaders + All leaders are innovators => Some managers are innovators => Some innovators are managers (I follows). However, all innovators are not necessarily leaders (II does not follow).",
    },

    # ----------------------------------------------------
    # 8. Odd One Out (2 Questions: 1 Easy, 1 Medium)
    # ----------------------------------------------------
    {
        "id_num": 22,
        "category": "odd_one_out",
        "difficulty": "Easy",
        "question_text": "Choose the word which is least like the other words in the group:",
        "options": [
            {"id": "A", "text": "Iron"},
            {"id": "B", "text": "Copper"},
            {"id": "C", "text": "Wood"},
            {"id": "D", "text": "Silver"},
        ],
        "correct_answer": "C",
        "explanation": "Iron, Copper, and Silver are metallic elements and electrical conductors, whereas Wood is an organic non-metal insulator.",
    },
    {
        "id_num": 23,
        "category": "odd_one_out",
        "difficulty": "Medium",
        "question_text": "Find the odd number-pair out:",
        "options": [
            {"id": "A", "text": "(14, 28)"},
            {"id": "B", "text": "(18, 36)"},
            {"id": "C", "text": "(22, 44)"},
            {"id": "D", "text": "(26, 54)"},
        ],
        "correct_answer": "D",
        "explanation": "In all pairs except D, the second number is double the first: 14*2=28, 18*2=36, 22*2=44. For (26, 54), 26*2=52 != 54.",
    },

    # ----------------------------------------------------
    # 9. Analogy (2 Questions: 1 Easy, 1 Medium)
    # ----------------------------------------------------
    {
        "id_num": 24,
        "category": "analogy",
        "difficulty": "Easy",
        "question_text": "Architect : Building :: Sculptor : ?",
        "options": [
            {"id": "A", "text": "Museum"},
            {"id": "B", "text": "Statue"},
            {"id": "C", "text": "Stone"},
            {"id": "D", "text": "Chisel"},
        ],
        "correct_answer": "B",
        "explanation": "An architect creates a building; a sculptor creates a statue.",
    },
    {
        "id_num": 25,
        "category": "analogy",
        "difficulty": "Medium",
        "question_text": "Calendar : Dates :: Dictionary : ?",
        "options": [
            {"id": "A", "text": "Words"},
            {"id": "B", "text": "Books"},
            {"id": "C", "text": "Language"},
            {"id": "D", "text": "Pages"},
        ],
        "correct_answer": "A",
        "explanation": "A calendar is a reference compilation of dates; a dictionary is a reference compilation of words.",
    },
]


def get_default_logical_reasoning_questions() -> list[dict]:
    """Return all 25 logical reasoning questions formatted for session insertion."""
    questions = []
    for item in LOGICAL_REASONING_QUESTIONS:
        scoring_key = {
            opt["id"]: (1.0 if opt["id"] == item["correct_answer"] else 0.0)
            for opt in item["options"]
        }
        questions.append({
            "category": item["category"],
            "difficulty": item["difficulty"],
            "question_type": "multiple_choice",
            "question_text": item["question_text"],
            "options": item["options"],
            "scoring_key": scoring_key,
            "max_score": 1.0,
            "explanation": item["explanation"],
        })
    return questions
