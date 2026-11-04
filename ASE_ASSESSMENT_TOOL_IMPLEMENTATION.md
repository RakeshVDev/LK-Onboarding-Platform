# ASE Assessment Tool — Assessment expansion

## Included changes
- Assessment templates now have `assessment_type`: `psychometric`, `technical`, or `english_grammar`.
- Reusable manager-authored question bank is stored in `assessment_question_bank`.
- Admin and Teacher users can add questions with four options and a correct option from Assessment Management.
- Learners see active templates through the existing `/my-assessments` route.
- Technical and English Grammar tests use the saved question bank and require 20 active questions.
- Psychometric assessment continues to use the existing five-category question generator unless a complete 20-question bank is authored for that template.
- Report generation accepts arbitrary assessment categories instead of assuming exactly the five psychometric categories.
- Main application branding is updated to ASE Assessment Tool.

## Apply database migration
Run from `backend` with the project's virtual environment active:

```powershell
alembic upgrade head
```

IMPORTANT: Before applying, run `alembic current` and `alembic heads`. The migration in this archive follows revision `0ebc47aa3f15`. If your live database reports a different head (for example `a05ff5678e02`), stop and reconcile the migration graph with your current repository before upgrading. Do not stamp or downgrade blindly.

## Seed the three tests and sample question banks
Run from `backend`:

```powershell
python seed_ase_assessments.py
```

The script is idempotent by assessment type. It creates/updates:
1. ASE Psychometric Assessment
2. ASE Technical Assessment
3. ASE English Grammar Assessment

It also seeds 20 sample technical questions and 20 sample English grammar questions if their respective question bank is empty. The seed script uses `ASE_SEED_MANAGER_ID` for audit metadata (default `1`); set it to a valid Identity user ID if your organization requires a real manager ID.

## Manual question management
Admin and Teacher users can use Assessment Management → Question Bank to add questions and choose the correct option. The backend stores the scoring key privately; learner question responses do not expose it. Deactivation is soft-delete.

## Test sequence
1. Apply migration after checking the revision graph.
2. Run the seed script.
3. Start the Identity and Training services.
4. Sign in as Admin or Teacher; create/edit templates and add questions.
5. Sign in as Learner; verify all three tests appear.
6. Complete each test and verify scores and report generation.
7. Verify unauthenticated and unauthorized API calls are rejected.

## Verification limitation
Backend Python files were syntax-compiled in the build environment. A full Angular production build and live MySQL/API integration test were not completed because frontend dependency installation did not finish in the build environment. Run `npm ci` and `npm run build` in your local frontend environment before deployment.
