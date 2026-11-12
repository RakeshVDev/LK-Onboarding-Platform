"""Idempotently seed the three ASE Assessment Tool learner tests.

Run from backend: python seed_ase_assessments.py
The Identity user IDs are external to the Training database. This script
uses the configured seed manager ID (default 1) only as audit metadata.
"""
import os
from services.training.app.db.session import SessionLocal
from services.training.app.models.assessment import AssessmentTemplate, AssessmentQuestionBank

MANAGER_ID = int(os.getenv("ASE_SEED_MANAGER_ID", "1"))
TESTS = [
    {
        "name": "ASE Psychometric Assessment",
        "assessment_type": "psychometric",
        "description": "Developmental assessment covering work preferences, reasoning, judgement, emotional intelligence and adaptability.",
        "category_config": {
            "personality_work_preferences": {"label": "Personality & Work Preferences", "question_count": 4},
            "logical_reasoning": {"label": "Logical Reasoning", "question_count": 4},
            "situational_judgement": {"label": "Situational Judgement", "question_count": 4},
            "emotional_intelligence": {"label": "Emotional Intelligence", "question_count": 4},
            "learning_adaptability": {"label": "Learning & Adaptability", "question_count": 4},
        },
    },
    {
        "name": "ASE Technical Assessment",
        "assessment_type": "technical",
        "description": "Role-relevant technical knowledge assessment. Admins and teachers add and maintain the question bank.",
        "category_config": {"technical_knowledge": {"label": "Technical Knowledge", "question_count": 20}},
    },
    {
        "name": "ASE English Grammar Assessment",
        "assessment_type": "english_grammar",
        "description": "English grammar, vocabulary and sentence usage assessment. Admins and teachers add and maintain the question bank.",
        "category_config": {"english_grammar": {"label": "English Grammar", "question_count": 20}},
    },
    {
        "name": "ASE Logical Reasoning Assessment",
        "assessment_type": "logical_reasoning",
        "description": "Standardized 25-question corporate examination evaluating deductive logic, series, relations, patterns, and analytical reasoning within 30 minutes.",
        "question_count": 25,
        "category_config": {
            "number_series": {"label": "Number Series", "question_count": 4},
            "alphabet_series": {"label": "Alphabet Series", "question_count": 3},
            "coding_decoding": {"label": "Coding-Decoding", "question_count": 3},
            "blood_relations": {"label": "Blood Relations", "question_count": 3},
            "direction_distance": {"label": "Direction and Distance", "question_count": 3},
            "pattern_recognition": {"label": "Pattern Recognition", "question_count": 3},
            "logical_statements": {"label": "Logical Statements", "question_count": 2},
            "odd_one_out": {"label": "Odd One Out", "question_count": 2},
            "analogy": {"label": "Analogy", "question_count": 2},
        },
    },
]


TECHNICAL_QUESTIONS = [
("Which data structure follows FIFO order?", ["Stack", "Queue", "Tree", "Graph"], "B"),
("Which SQL command retrieves rows from a table?", ["SELECT", "UPDATE", "ALTER", "DROP"], "A"),
("Which HTTP method is commonly used to retrieve a resource?", ["POST", "DELETE", "GET", "PATCH"], "C"),
("What does OOP stand for?", ["Object-Oriented Programming", "Order of Operations", "Open Output Protocol", "Object Operating Process"], "A"),
("Which keyword is commonly used to define a class in Python?", ["function", "class", "struct", "object"], "B"),
("What is the time complexity of binary search on a sorted array?", ["O(n)", "O(log n)", "O(n²)", "O(1) always"], "B"),
("Which SQL clause filters grouped records?", ["WHERE", "ORDER BY", "HAVING", "LIMIT"], "C"),
("What does API stand for?", ["Application Programming Interface", "Applied Program Internet", "Application Process Input", "Advanced Programming Instruction"], "A"),
("Which Git command creates a local copy of a remote repository?", ["push", "commit", "clone", "merge"], "C"),
("Which status code indicates a successful HTTP request?", ["301", "404", "500", "200"], "D"),
("Which structure is best suited to last-in, first-out operations?", ["Queue", "Stack", "Heap", "Hash map"], "B"),
("What is a primary key used for in a relational database?", ["Encrypting rows", "Uniquely identifying a row", "Sorting every query", "Joining databases automatically"], "B"),
("Which Java feature allows one class to inherit another class's members?", ["Encapsulation", "Inheritance", "Compilation", "Serialization"], "B"),
("What does CSS primarily control?", ["Database storage", "Server routing", "Web page presentation", "Network addressing"], "C"),
("Which of these is a valid JSON value?", ['{"active": true}', "function() {}", "<div>", "SELECT *"], "A"),
("What is the purpose of an index in a database?", ["Improve lookup performance", "Delete duplicate tables", "Encrypt passwords", "Replace primary keys"], "A"),
("Which layer commonly handles HTTP requests in FastAPI?", ["Router", "Database index", "CSS selector", "Compiler"], "A"),
("What does ACID in database transactions include?", ["Atomicity", "Availability", "Accessibility", "Adaptability"], "A"),
("Which operator checks equality in Python?", ["=", "==", ":=", "!="], "B"),
("What is the main purpose of unit testing?", ["Test individual units of code", "Deploy an application", "Design database schemas", "Monitor network traffic"], "A"),
]
ENGLISH_QUESTIONS = [
("Choose the grammatically correct sentence.", ["She go to work daily.", "She goes to work daily.", "She going to work daily.", "She gone to work daily."], "B"),
("Choose the correct article: He is ___ honest person.", ["a", "an", "the", "no article"], "B"),
("Choose the correct past tense of 'write'.", ["Writed", "Written", "Wrote", "Writing"], "C"),
("Choose the correct subject-verb agreement.", ["The team are ready.", "The team is ready.", "The team be ready.", "The team were ready yesterday."], "B"),
("Select the correct preposition: She is good ___ mathematics.", ["in", "on", "at", "for"], "C"),
("Choose the correct plural of 'analysis'.", ["Analysises", "Analyses", "Analysis", "Analys"], "B"),
("Choose the correct sentence.", ["I have lived here for five years.", "I am live here for five years.", "I living here since five years.", "I has lived here for five years."], "A"),
("Choose the correct comparative form of 'good'.", ["Gooder", "More good", "Best", "Better"], "D"),
("Select the correct pronoun: This matter is between you and ___.", ["I", "me", "my", "mine"], "B"),
("Choose the correctly punctuated sentence.", ["Lets eat, Grandma.", "Let's eat Grandma.", "Lets eat Grandma", "Let's, eat Grandma."], "A"),
("Choose the correct passive voice: 'The team completed the task.'", ["The task completed the team.", "The task was completed by the team.", "The task is completing by the team.", "The team was completed by the task."], "B"),
("Choose the correct conjunction: I stayed home ___ it was raining.", ["because", "although", "unless", "but"], "A"),
("Identify the correctly spelled word.", ["Accomodation", "Acommodation", "Accommodation", "Accommadation"], "C"),
("Choose the correct form: If I ___ more time, I would learn French.", ["have", "had", "will have", "having"], "B"),
("Choose the correct sentence.", ["There are less errors today.", "There are fewer errors today.", "There is fewer errors today.", "There are fewest error today."], "B"),
("Choose the correct reported speech: He said, 'I am busy.'", ["He said that he is busy.", "He said that I was busy.", "He said that he was busy.", "He says he busy."], "C"),
("Select the correct word: The new policy will ___ everyone.", ["affect", "effect", "effects", "affects"], "A"),
("Choose the correct question tag: You are coming, ___?", ["are you", "aren't you", "don't you", "won't you"], "B"),
("Choose the correct tense: By next week, she ___ the course.", ["completes", "completed", "will have completed", "has complete"], "C"),
("Choose the correct sentence.", ["Neither of the answers is correct.", "Neither of the answers are correct.", "Neither answers be correct.", "Neither of answer is correct."], "A"),
]

from services.training.app.services.assessment_logical_reasoning import LOGICAL_REASONING_QUESTIONS


def seed_logical_reasoning_bank(db, template):
    db.query(AssessmentQuestionBank).filter(
        AssessmentQuestionBank.template_id == template.id
    ).delete()
    db.flush()
    for idx, item in enumerate(LOGICAL_REASONING_QUESTIONS, start=1):
        scoring_key = {
            opt["id"]: (1.0 if opt["id"] == item["correct_answer"] else 0.0)
            for opt in item["options"]
        }
        db.add(AssessmentQuestionBank(
            template_id=template.id,
            category=item["category"],
            difficulty=item.get("difficulty", "Medium"),
            question_type="multiple_choice",
            question_text=item["question_text"],
            options=item["options"],
            scoring_key=scoring_key,
            max_score=1.0,
            negative_marks=0.0,
            display_order=idx,
            in_assessment=True,
            is_active=True,
            created_by_user_id=MANAGER_ID,
        ))
    db.flush()
    print(f"Seeded 25 logical reasoning questions for template {template.id}")


def seed_bank(db, template, rows, category):
    existing_count = db.query(AssessmentQuestionBank).filter(
        AssessmentQuestionBank.template_id == template.id,
        AssessmentQuestionBank.is_active.is_(True),
    ).count()
    if existing_count:
        return
    for idx, (question, choices, correct) in enumerate(rows, start=1):
        options = [{"id": chr(65+i), "text": text} for i, text in enumerate(choices)]
        key = {option["id"]: (1.0 if option["id"] == correct else 0.0) for option in options}
        db.add(AssessmentQuestionBank(
            template_id=template.id,
            category=category,
            difficulty="Medium",
            question_type="multiple_choice",
            question_text=question,
            options=options,
            scoring_key=key,
            max_score=1.0,
            negative_marks=0.0,
            display_order=idx,
            in_assessment=True,
            is_active=True,
            created_by_user_id=MANAGER_ID,
        ))


def main():
    db = SessionLocal()
    try:
        for item in TESTS:
            existing = db.query(AssessmentTemplate).filter(
                AssessmentTemplate.assessment_type == item["assessment_type"]
            ).first()
            expected_count = item.get("question_count", 20)
            if existing:
                existing.name = item["name"]
                existing.description = item["description"]
                existing.question_count = expected_count
                existing.category_config = item["category_config"]
                existing.is_active = True
                print(f"Updated: {existing.name} (ID {existing.id})")
            else:
                row = AssessmentTemplate(
                    **item,
                    is_active=True,
                    created_by_user_id=MANAGER_ID,
                )
                db.add(row)
                db.flush()
                print(f"Created: {row.name} (ID {row.id})")
        db.flush()
        technical = db.query(AssessmentTemplate).filter_by(assessment_type="technical").first()
        grammar = db.query(AssessmentTemplate).filter_by(assessment_type="english_grammar").first()
        logical = db.query(AssessmentTemplate).filter_by(assessment_type="logical_reasoning").first()
        if technical:
            seed_bank(db, technical, TECHNICAL_QUESTIONS, "technical_knowledge")
        if grammar:
            seed_bank(db, grammar, ENGLISH_QUESTIONS, "english_grammar")
        if logical:
            seed_logical_reasoning_bank(db, logical)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
