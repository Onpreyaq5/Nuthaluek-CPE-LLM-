from __future__ import annotations

from src.schemas.contracts import RecommendationComposeRequest

DISCLAIMER = (
    "ระบบนี้เป็นเครื่องมือช่วยวางแผนเบื้องต้น ไม่ใช่การยืนยันจากมหาวิทยาลัย "
    "โปรดตรวจสอบกับระบบทะเบียนและอาจารย์ที่ปรึกษาก่อนลงทะเบียนจริง"
)


def compose(request: RecommendationComposeRequest) -> dict:
    recommendations = []
    for index, candidate in enumerate(request.candidates):
        recommendations.append(
            {
                "rank": index + 1,
                "plan_id": candidate.plan_id,
                "name": candidate.name,
                "term": candidate.term,
                "weekly_schedule": [section.model_dump() for section in candidate.sections],
                "summary": candidate.summary,
                "reasons": candidate.rule_reasons,
                "explanation": candidate.explanation,
                "risks": candidate.risks,
                "tradeoffs": {
                    "advantages": candidate.summary.get("advantages", []),
                    "disadvantages": candidate.summary.get("disadvantages", []),
                },
            }
        )
    return {"recommendations": recommendations, "disclaimer": DISCLAIMER}
