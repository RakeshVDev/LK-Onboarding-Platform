
from collections import Counter

from services.training.app.services.assessment_mock import (
    generate_mock_questions,
)

questions = generate_mock_questions()

print("Total questions:", len(questions))

category_counts = Counter(
    question["category"] for question in questions
)

for category, count in sorted(category_counts.items()):
    print(f"{category}: {count}")

print("\nFirst question:")
print(questions[0]["question_text"])

print("\nOptions:")
for option in questions[0]["options"]:
    print(option["id"], "-", option["text"])

print("\nScoring key:")
print(questions[0]["scoring_key"])

print("\nMock assessment generation successful!")
