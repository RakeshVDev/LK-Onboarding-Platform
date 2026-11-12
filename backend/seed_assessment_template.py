
from services.training.app.db.session import SessionLocal
from services.training.app.models.assessment import AssessmentTemplate

CATEGORY_CONFIG = {
    "personality_work_preferences": {
        "label": "Personality & Work Preferences",
        "question_count": 4,
    },
    "logical_reasoning": {
        "label": "Logical Reasoning",
        "question_count": 4,
    },
    "situational_judgement": {
        "label": "Situational Judgement",
        "question_count": 4,
    },
    "emotional_intelligence": {
        "label": "Emotional Intelligence",
        "question_count": 4,
    },
    "learning_adaptability": {
        "label": "Learning & Adaptability",
        "question_count": 4,
    },
}


def seed_template():
    db = SessionLocal()

    try:
        existing = (
            db.query(AssessmentTemplate)
            .filter(
                AssessmentTemplate.name.in_(
                    ["ASE Psychometric Assessment", "L&K Psychometric Assessment"]
                )
            )
            .first()
        )

        if existing:
            existing.name = "ASE Psychometric Assessment"
            existing.is_active = True
            existing.question_count = 20
            existing.category_config = CATEGORY_CONFIG
            db.commit()

            print("Existing assessment template activated.")
            print("Template ID:", existing.id)
            return

        template = AssessmentTemplate(
            name="ASE Psychometric Assessment",
            description=(
                "A 20-question developmental assessment covering "
                "personality, reasoning, judgement, emotional "
                "intelligence, and learning adaptability."
            ),
            question_count=20,
            category_config=CATEGORY_CONFIG,
            is_active=True,
            created_by_user_id=None,
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        print("Assessment template created successfully!")
        print("Template ID:", template.id)
        print("Question count:", template.question_count)
        print("Active:", template.is_active)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_template()
