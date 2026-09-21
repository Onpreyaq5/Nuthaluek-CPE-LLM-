"""ทดสอบการแปลงผลจากโมดูล 06 เป็นคำอธิบาย และการตรวจกติกาหน่วยกิต 9–21"""
import pytest

from src.models.schemas import ConflictIn, ExplainPlanRequest, PlanItemIn
from src.services.explainer import check_credits, explain_plan
from src.services.knowledge import knowledge_base


@pytest.fixture(scope="module", autouse=True)
def loaded_kb():
    knowledge_base.load()


def plan(*items):
    return [PlanItemIn(course_code=c, section=s, course_name=n, credits=cr) for c, s, n, cr in items]


CPE_PLAN_18 = plan(
    ("04100201-66", "02", "สถาปัตยกรรมคอมพิวเตอร์", 3),
    ("04100202-66", "02", "การเขียนโปรแกรมเชิงวัตถุ", 3),
    ("04100203-66", "02", "ระบบฐานข้อมูล", 3),
    ("04100204-66", "02", "เครือข่ายคอมพิวเตอร์", 3),
    ("04000207-63", "01", "สถิติวิศวกรรม", 3),
    ("01000301-62", "01", "วิทยาศาสตร์และเทคโนโลยีสมัยใหม่", 3),
)


# ── กติกาหน่วยกิต ───────────────────────────────────────────────
@pytest.mark.parametrize(
    "credits,expected",
    [(9, "ok"), (15, "ok"), (21, "ok"), (22, "over"), (30, "over"), (8, "under"), (3, "under")],
)
def test_credit_boundaries(credits, expected):
    assert check_credits(credits, "1/2569")["status"] == expected


def test_summer_term_caps_at_9():
    assert check_credits(9, "3/2569")["status"] == "ok"
    assert check_credits(12, "3/2569")["status"] == "over"
    # ภาคฤดูร้อนไม่มีขั้นต่ำ
    assert check_credits(3, "3/2569")["status"] == "ok"


def test_credit_note_tells_how_much_to_adjust():
    over = check_credits(24, "1/2569")
    assert "3" in over["note"]
    under = check_credits(6, "1/2569")
    assert "3" in under["note"]


# ── การอธิบายแผน ────────────────────────────────────────────────
def test_clean_plan_is_ok():
    res = explain_plan(ExplainPlanRequest(term="1/2569", plan=CPE_PLAN_18))
    assert res.verdict == "ok"
    assert res.credit_check["total_credits"] == 18
    assert res.credit_check["status"] == "ok"
    assert "ไม่มี" in res.headline or "ใช้ได้" in res.headline


def test_time_clash_is_blocked_and_explained_in_thai():
    res = explain_plan(ExplainPlanRequest(
        term="1/2569",
        plan=CPE_PLAN_18,
        conflicts=[ConflictIn(
            code="C1", severity="ERROR", message_key="time_clash",
            message_th="04100201-66 หมู่ 01 เรียนทับกับ 04100202-66 หมู่ 01",
            subjects=["04100201-66-01", "04100202-66-01"],
            detail={"day": 0, "overlap_start": 540, "overlap_end": 660},
            suggestions=[{"action": "change_section", "to": "04100201-66-02"}],
        )],
    ))
    assert res.verdict == "blocked"
    assert "เวลาเรียนชนกัน" in res.explanation
    assert "วันจันทร์" in res.explanation      # แปลง day=0 เป็นชื่อวันไทย
    assert "09:00" in res.explanation          # แปลงนาทีเป็นเวลา
    assert "11:00" in res.explanation
    assert res.next_steps


def test_exam_clash_explained():
    res = explain_plan(ExplainPlanRequest(
        term="1/2569", plan=CPE_PLAN_18,
        conflicts=[ConflictIn(
            code="C2", severity="ERROR", message_key="exam_clash",
            subjects=["04100203-66-01", "04000207-63-01"],
            detail={"exam_date": "2569-09-07", "start_min": 780, "end_min": 960},
        )],
    ))
    assert res.verdict == "blocked"
    assert "เวลาสอบชนกัน" in res.explanation
    assert "2569-09-07" in res.explanation


def test_over_credit_plan_flagged():
    big = CPE_PLAN_18 + plan(
        ("04100208-66", "01", "การพัฒนาเว็บแอปพลิเคชัน", 3),
        ("04100105-66", "01", "คณิตศาสตร์ดิสครีต", 3),
    )  # 24 หน่วยกิต
    res = explain_plan(ExplainPlanRequest(term="1/2569", plan=big))
    assert res.credit_check["status"] == "over"
    assert res.verdict == "warning"
    assert any("ถอด" in s for s in res.next_steps)


def test_under_credit_plan_flagged():
    small = plan(("04100201-66", "02", "สถาปัตยกรรมคอมพิวเตอร์", 3))
    res = explain_plan(ExplainPlanRequest(term="1/2569", plan=small))
    assert res.credit_check["status"] == "under"
    assert any("เพิ่ม" in s for s in res.next_steps)


def test_warnings_only_is_not_blocked():
    res = explain_plan(ExplainPlanRequest(
        term="1/2569", plan=CPE_PLAN_18,
        warnings=[ConflictIn(code="W2", severity="WARNING", message_key="large_gap",
                             message_th="วันอังคารมีช่องว่าง 4 ชั่วโมง")],
    ))
    assert res.verdict == "warning"
    assert "ข้อควรระวัง" in res.explanation


def test_explanation_attaches_regulation_sources():
    """ผลที่ติด C1/C4 ต้องแนบระเบียบที่เกี่ยวข้องมาด้วย"""
    res = explain_plan(ExplainPlanRequest(
        term="1/2569", plan=CPE_PLAN_18,
        conflicts=[ConflictIn(code="C1", severity="ERROR", subjects=["a", "b"])],
    ))
    assert res.sources, "ต้องมีแหล่งอ้างอิงระเบียบ"


def test_disclaimer_always_present():
    res = explain_plan(ExplainPlanRequest(term="1/2569", plan=CPE_PLAN_18))
    assert "ไม่ใช่การยืนยันจากมหาวิทยาลัย" in res.disclaimer


def test_never_invents_numbers():
    """ถ้า 06 ไม่ส่ง detail มา คำอธิบายต้องไม่มีตัวเลขเวลาโผล่มาเอง"""
    res = explain_plan(ExplainPlanRequest(
        term="1/2569", plan=CPE_PLAN_18,
        conflicts=[ConflictIn(code="C1", severity="ERROR", subjects=["x-01", "y-01"])],
    ))
    assert "09:00" not in res.explanation
    assert "วันจันทร์" not in res.explanation
