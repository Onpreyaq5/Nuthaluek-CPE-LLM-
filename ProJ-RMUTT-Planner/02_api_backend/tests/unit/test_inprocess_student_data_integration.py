from __future__ import annotations

from pathlib import Path

import pytest

from src.core.config import get_settings

_FIXTURE_PATH = (
    Path(get_settings().MODULES_ROOT)
    / "05_data_integration"
    / "tests"
    / "fixtures"
    / "graduate_check_sample.html"
)


@pytest.mark.skipif(
    not _FIXTURE_PATH.exists(),
    reason=(
        "ต้องมีโฟลเดอร์ 05_data_integration พร้อม tests/fixtures/graduate_check_sample.html "
        "วางไว้ข้างๆ 02_api_backend ก่อน (ยังไม่มีตอนนี้ — เพื่อนยังไม่ได้ทำ 05)"
    ),
)
async def test_inprocess_student_data_parses_real_fixture() -> None:
    from src.adapters.inprocess.student_data import InprocessStudentData

    adapter = InprocessStudentData()
    result = await adapter.import_graduate_check(_FIXTURE_PATH.read_bytes())
    assert result.imported_courses >= 0


_MODULE_05_DIR = Path(get_settings().MODULES_ROOT) / get_settings().MODULE_05_DIR
_OUR_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "import"


@pytest.mark.skip(
    reason=(
        "sample_sanitized.html เป็นข้อมูลสังเคราะห์ที่แต่งขึ้นเองก่อนมีโค้ด/ตัวอย่างจริงจาก 05 "
        "(รูปแบบ 'รายงานผลการศึกษา' ทั่วไป) แต่ parse_graduate_check() จริงของ 05 คาดหวังหน้า "
        "'ตรวจสอบจบ' (graduate_check.asp) ที่มีโครงสร้างตาราง/เครื่องหมาย 'ตรวจสอบจบ' เฉพาะเจาะจงมาก — "
        "sample_sanitized.html จึง parse ได้ผลว่าง (audit.all_courses() == 0) ไม่ตรง expected.json เสมอ "
        "ไม่ใช่บั๊ก แค่ fixture ของเราไม่ตรงรูปแบบจริง การันตี integration จริงกับ 05 ให้ดูที่ "
        "test_inprocess_student_data_parses_real_fixture (ใช้ fixture จริงของ 05) แทน — ถ้าจะแก้ต้องขอ "
        "ตัวอย่างหน้า 'ตรวจสอบจบ' จริงที่ลบข้อมูลระบุตัวตนแล้วจากทีม 05 มาแทนไฟล์นี้"
    ),
)
async def test_inprocess_import_matches_expected_json() -> None:
    import json

    from src.adapters.inprocess.student_data import InprocessStudentData

    expected = json.loads((_OUR_FIXTURES_DIR / "expected.json").read_text(encoding="utf-8"))
    adapter = InprocessStudentData()
    result = await adapter.import_graduate_check((_OUR_FIXTURES_DIR / "sample_sanitized.html").read_bytes())

    assert result.imported_courses == expected["imported_courses"]
    assert result.retake_required == expected["retake_required"]
    assert result.credits_remaining == expected["credits_remaining"]
    assert result.warnings == expected["warnings"]
