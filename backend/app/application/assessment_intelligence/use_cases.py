"""Application analyzer & use case for Reading Comprehension & Analytical Deduction metrics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.domain.assessment_intelligence import DimensionScoreEntity


class ComprehensionDimensionAnalyzer:
    """Evaluates reading comprehension accuracy, textual inference, and analytical deduction locally."""

    def analyze_responses(self, question_records: list[dict[str, Any]]) -> list[DimensionScoreEntity]:
        by_subdimension: dict[str, list[tuple[float, float]]] = defaultdict(list)

        for item in question_records:
            cat = str(item.get("category") or "reading_comprehension").lower().strip()
            max_score = max(1.0, float(item.get("max_score") or 1.0))
            earned = max(0.0, float(item.get("points_awarded") or 0.0))
            by_subdimension[cat].append((earned, max_score))

        if not by_subdimension:
            return []

        dimensions: list[DimensionScoreEntity] = []
        total_earned = 0.0
        total_max = 0.0

        for sub_key, pairs in sorted(by_subdimension.items()):
            sub_earned = sum(p[0] for p in pairs)
            sub_max = sum(p[1] for p in pairs)
            total_earned += sub_earned
            total_max += sub_max
            pct = round((sub_earned / sub_max) * 100.0, 2) if sub_max > 0 else 0.0
            band = "Exceptional" if pct >= 85 else ("Proficient" if pct >= 70 else ("Developing" if pct >= 50 else "Needs Attention"))
            label = sub_key.replace("_", " ").title()
            interp = (
                f"Demonstrates strong textual grounding in {label}."
                if pct >= 70
                else f"Needs closer close-reading and evidence verification in {label}."
            )
            dimensions.append(
                DimensionScoreEntity(
                    dimension_key=sub_key,
                    dimension_label=label,
                    normalized_score=pct,
                    raw_score=round(sub_earned, 2),
                    max_score=round(sub_max, 2),
                    percentile_band=band,
                    interpretation=interp,
                    evidence=[f"Scored {sub_earned:.1f}/{sub_max:.1f} across {len(pairs)} passage-dependent items"],
                )
            )

        overall_pct = round((total_earned / total_max) * 100.0, 2) if total_max > 0 else 0.0
        if "analytical_deduction" not in by_subdimension:
            dimensions.append(
                DimensionScoreEntity(
                    dimension_key="analytical_deduction",
                    dimension_label="Analytical Deduction",
                    normalized_score=overall_pct,
                    raw_score=round(total_earned, 2),
                    max_score=round(total_max, 2),
                    percentile_band="Proficient" if overall_pct >= 70 else "Developing",
                    interpretation=(
                        "Passage-bound logical inference and claim verification derived accurately from evidence."
                        if overall_pct >= 70
                        else "Practice isolating explicit evidence from distractor assumptions within complex passages."
                    ),
                    evidence=[f"Passage deduction accuracy: {overall_pct:.1f}%"],
                )
            )

        return dimensions

