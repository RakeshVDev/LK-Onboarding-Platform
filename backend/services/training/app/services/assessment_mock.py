
import random
from collections import Counter
from typing import Optional


CATEGORIES = {
    "personality_work_preferences": "Personality & Work Preferences",
    "logical_reasoning": "Logical Reasoning",
    "situational_judgement": "Situational Judgement",
    "emotional_intelligence": "Emotional Intelligence",
    "learning_adaptability": "Learning & Adaptability",
}


def make_question(category, question, options, scores):
    return {
        "category": category,
        "question_type": "single_choice",
        "question_text": question,
        "options": [
            {"id": key, "text": text}
            for key, text in zip("ABCD", options)
        ],
        "scoring_key": scores,
        "max_score": 4.0,
    }


def build_question_bank():
    bank = {category: [] for category in CATEGORIES}

    # 1. Personality and work preferences
    personality_options = [
        "I strongly prefer working independently.",
        "I usually prefer independent work with occasional collaboration.",
        "I enjoy collaborating with others on most tasks.",
        "I strongly prefer team-based collaboration.",
    ]
    personality_scores = {"A": 4, "B": 3, "C": 2, "D": 1}

    personality_questions = [
        "When starting a new project, which working approach suits you best?",
        "How do you prefer to organize your daily work?",
        "When facing a challenging assignment, how do you prefer to proceed?",
        "Which work environment helps you perform most comfortably?",
        "How do you prefer to contribute during team meetings?",
        "When planning a task, what approach do you usually take?",
        "How do you prefer to receive updates about team activities?",
        "When completing a complex assignment, what working style suits you?",
    ]

    for question in personality_questions:
        bank["personality_work_preferences"].append(
            make_question(
                "personality_work_preferences",
                question,
                personality_options,
                personality_scores,
            )
        )

    # 2. Logical reasoning
    logical_questions = [
        {
            "question": "Find the next number: 2, 4, 8, 16, ?",
            "options": ["18", "24", "32", "36"],
            "answer": "C",
        },
        {
            "question": "All developers know programming. Rahul is a developer. What follows?",
            "options": [
                "Rahul knows programming.",
                "Rahul is a manager.",
                "Rahul knows every language.",
                "No conclusion is possible.",
            ],
            "answer": "A",
        },
        {
            "question": "Five machines make five items in five minutes. How long do ten machines take to make ten items?",
            "options": ["2.5 minutes", "5 minutes", "10 minutes", "20 minutes"],
            "answer": "B",
        },
        {
            "question": "A task takes three hours. It starts at 9:30 AM. When does it finish?",
            "options": ["11:30 AM", "12:00 PM", "12:30 PM", "1:00 PM"],
            "answer": "C",
        },
        {
            "question": "Find the missing number: 3, 6, 12, 24, ?",
            "options": ["30", "36", "42", "48"],
            "answer": "D",
        },
        {
            "question": "If all roses are flowers and some flowers fade quickly, which statement must be true?",
            "options": [
                "All flowers are roses.",
                "All roses fade quickly.",
                "All roses are flowers.",
                "No roses fade quickly.",
            ],
            "answer": "C",
        },
        {
            "question": "A meeting starts at 2:15 PM and lasts 45 minutes. When does it end?",
            "options": ["2:45 PM", "3:00 PM", "3:15 PM", "3:30 PM"],
            "answer": "B",
        },
        {
            "question": "Find the next number: 1, 4, 9, 16, 25, ?",
            "options": ["30", "32", "35", "36"],
            "answer": "D",
        },
    ]

    for item in logical_questions:
        scoring = {
            option: 4 if option == item["answer"] else 0
            for option in "ABCD"
        }
        bank["logical_reasoning"].append(
            make_question(
                "logical_reasoning",
                item["question"],
                item["options"],
                scoring,
            )
        )

    # 3. Situational judgement
    situational_options = [
        "Ignore the issue and continue without informing anyone.",
        "Wait until someone else identifies and solves the issue.",
        "Understand the issue and discuss a suitable solution.",
        "Take responsible action and communicate the outcome.",
    ]
    situational_scores = {"A": 0, "B": 1, "C": 3, "D": 4}

    situational_questions = [
        "You discover an important error just before a project deadline. What would you do?",
        "A teammate cannot complete assigned work on time. How would you respond?",
        "You receive an unfamiliar task with unclear instructions. What is your first step?",
        "You disagree with a decision made by your project team. How would you handle it?",
        "You notice a colleague has misunderstood an important requirement. What would you do?",
        "Two urgent tasks have overlapping deadlines. How would you respond?",
        "A project deliverable may be delayed. What should you do?",
        "You identify a process that is creating repeated errors. How would you handle it?",
    ]

    for question in situational_questions:
        bank["situational_judgement"].append(
            make_question(
                "situational_judgement",
                question,
                situational_options,
                situational_scores,
            )
        )

    # 4. Emotional intelligence
    emotional_options = [
        "React immediately without considering the situation.",
        "Avoid discussing the situation.",
        "Listen and try to understand the other person's perspective.",
        "Listen carefully, manage my response and communicate constructively.",
    ]
    emotional_scores = {"A": 0, "B": 1, "C": 3, "D": 4}

    emotional_questions = [
        "A colleague criticizes your work. How do you normally respond?",
        "A teammate appears frustrated during a group discussion. What would you do?",
        "You make a mistake that affects another team member. How would you handle it?",
        "You receive feedback that you initially disagree with. What is your response?",
        "A colleague misunderstands your communication. How would you resolve it?",
        "A team member has a different working style from yours. How would you collaborate?",
        "You feel stressed because of a demanding deadline. How would you manage your response?",
        "Someone takes credit for work you contributed to. How would you handle the situation?",
    ]

    for question in emotional_questions:
        bank["emotional_intelligence"].append(
            make_question(
                "emotional_intelligence",
                question,
                emotional_options,
                emotional_scores,
            )
        )

    # 5. Learning and adaptability
    learning_options = [
        "Avoid the new task whenever possible.",
        "Wait for someone to complete it for me.",
        "Try to understand it using available resources.",
        "Actively learn, practise and seek feedback to improve.",
    ]
    learning_scores = {"A": 0, "B": 1, "C": 3, "D": 4}

    learning_questions = [
        "Your organization introduces a new technology. How would you respond?",
        "You receive a task involving a skill you have never used. What would you do?",
        "Your first attempt at learning a new concept is unsuccessful. How would you proceed?",
        "How do you generally respond to constructive feedback about your learning progress?",
        "Your team changes its workflow. How would you adapt?",
        "You discover that your current knowledge is insufficient for a task. What would you do?",
        "A training session introduces an unfamiliar concept. How would you approach it?",
        "You need to learn a new tool within a short period. How would you proceed?",
    ]

    for question in learning_questions:
        bank["learning_adaptability"].append(
            make_question(
                "learning_adaptability",
                question,
                learning_options,
                learning_scores,
            )
        )

    return bank


QUESTION_BANK = build_question_bank()


def generate_mock_questions(
    seed: Optional[int] = None,
) -> list[dict]:
    """
    Select exactly 20 questions:
    four random questions from each of five categories.

    Supplying a seed makes the selection reproducible for tests.
    """

    rng = random.Random(seed)
    selected = []

    for category in CATEGORIES:
        category_questions = QUESTION_BANK[category]

        if len(category_questions) < 4:
            raise ValueError(
                f"Insufficient questions in category: {category}"
            )

        selected.extend(
            rng.sample(category_questions, 4)
        )

    rng.shuffle(selected)

    if len(selected) != 20:
        raise ValueError("Assessment must contain exactly 20 questions")

    counts = Counter(
        question["category"] for question in selected
    )

    if any(counts[category] != 4 for category in CATEGORIES):
        raise ValueError("Each category must contain exactly four questions")

    return [dict(question) for question in selected]


def validate_question_bank():
    """Validate the question bank before using it."""

    for category in CATEGORIES:
        questions = QUESTION_BANK[category]

        if len(questions) < 4:
            raise ValueError(f"{category} needs at least four questions")

        question_texts = [
            question["question_text"] for question in questions
        ]

        if len(question_texts) != len(set(question_texts)):
            raise ValueError(f"Duplicate questions found in {category}")

        for question in questions:
            option_ids = {
                option["id"] for option in question["options"]
            }

            if option_ids != {"A", "B", "C", "D"}:
                raise ValueError("Invalid option IDs")

            if set(question["scoring_key"]) != option_ids:
                raise ValueError("Scoring key does not match options")

            if max(question["scoring_key"].values()) != question["max_score"]:
                raise ValueError("Maximum score does not match scoring key")

    return True
