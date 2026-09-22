"""06_schedule_conflict_engine - Quality-of-Life Evaluator (Soft Rules W1 - W5)
ตรวจสอบเงื่อนไขที่ส่งผลต่อคุณภาพชีวิตการเรียนของนักศึกษา
"""
from __future__ import annotations

from typing import Any
from ..models.schemas import (
    SectionInput,
    StudentPreferences,
    WarningDetail,
)
from .bitmask import (
    DAY_NAMES,
    DAY_NAMES_TH,
    ensure_section_mask,
    get_schedule_profile,
)


def evaluate_quality(
    sections: list[SectionInput],
    preferences: StudentPreferences | None = None,
) -> tuple[list[WarningDetail], dict[str, Any]]:
    """ประเมินกฎ Soft Rules (W1 - W5)
    คืนค่า: (warnings[], schedule_profile)
    """
    warnings: list[WarningDetail] = []
    if not sections:
        return warnings, {"days_on_campus": 0, "free_days": DAY_NAMES}

    # รวม Mask ของทุก Section
    total_mask = 0
    for sec in sections:
        total_mask |= ensure_section_mask(sec)

    profile = get_schedule_profile(total_mask)

    # W1: LONG_STRETCH (เรียนติดกันเกิน 6 ชม. ไม่มีพัก)
    if profile["max_consecutive_hours"] > 6.0:
        warnings.append(
            WarningDetail(
                code="W1",
                severity="WARNING",
                message_key="long_stretch",
                message_th=(
                    f"มีวันที่มีการเรียนติดต่อกันยาวนานเกิน 6 ชั่วโมง "
                    f"({profile['max_consecutive_hours']:.1f} ชม.) โดยไม่มีเวลาพักผ่อน"
                ),
                message_en=(
                    f"Consecutive class stretch exceeds 6 hours "
                    f"({profile['max_consecutive_hours']:.1f} hrs) without adequate break"
                ),
                detail={"max_consecutive_hours": profile["max_consecutive_hours"]},
            )
        )

    # W2: LARGE_GAP (ช่องว่างระหว่างคาบเกิน 4 ชม.)
    if profile["max_gap_hours"] > 4.0:
        warnings.append(
            WarningDetail(
                code="W2",
                severity="WARNING",
                message_key="large_gap",
                message_th=(
                    f"มีช่องว่างระหว่างคาบเรียนในวันเดียวกันยาวนานเกิน 4 ชั่วโมง "
                    f"({profile['max_gap_hours']:.1f} ชม.)"
                ),
                message_en=(
                    f"Gap between classes on the same day exceeds 4 hours "
                    f"({profile['max_gap_hours']:.1f} hrs)"
                ),
                detail={"max_gap_hours": profile["max_gap_hours"]},
            )
        )

    # W3: EARLY_CLASS (คาบเช้า 08:00 ในวันที่ผู้ใช้ขอว่าง หรือตั้งเลี่ยงคาบเช้า)
    if preferences:
        # ตรวจสอบวันที่ผู้ใช้ขอว่างไว้ แต่กลับมีเรียน
        free_days_requested = set(preferences.free_days)
        active_days = set(profile["active_days"])
        conflicted_free_days = free_days_requested.intersection(active_days)
        if conflicted_free_days:
            for d in conflicted_free_days:
                idx = DAY_NAMES.index(d) if d in DAY_NAMES else -1
                d_th = DAY_NAMES_TH[idx] if idx != -1 else d
                warnings.append(
                    WarningDetail(
                        code="W3",
                        severity="WARNING",
                        message_key="busy_preferred_free_day",
                        message_th=f"มีคาบเรียนในวัน{d_th} ซึ่งเป็นวันที่นักศึกษาตั้งค่าว่าต้องการเป็นวันว่าง",
                        message_en=f"Classes scheduled on {d}, which was requested as a free day",
                        detail={"day": d, "day_th": d_th},
                    )
                )

        # ตรวจสอบ avoid_morning
        if preferences.avoid_morning and profile["has_early_morning"]:
            warnings.append(
                WarningDetail(
                    code="W3",
                    severity="WARNING",
                    message_key="early_morning_class",
                    message_th="มีคาบเรียนช่วงเช้า (08:00 - 09:00) แม้ตั้งค่าหลีกเลี่ยงคาบเช้าไว้",
                    message_en="Early morning class (08:00 - 09:00) scheduled despite avoid morning preference",
                    detail={"has_early_morning": True},
                )
            )

    # W4: RUSH_MOVE (ต้องย้ายอาคาร/วิทยาเขตระหว่างคาบที่ติดกันน้อยกว่า 15 นาที)
    # รวบรวม meetings ทั้งหมดแล้วจัดกลุ่มตามวัน
    day_meetings: dict[int, list[tuple[int, int, str, str, str]]] = {}
    for sec in sections:
        for m in sec.meetings:
            building = m.building or ""
            campus = sec.campus or ""
            day_meetings.setdefault(m.day, []).append(
                (m.start_min, m.end_min, building, campus, sec.id)
            )

    for day, m_list in day_meetings.items():
        # เรียงตามเวลาเริ่ม
        m_list.sort(key=lambda x: x[0])
        for i in range(len(m_list) - 1):
            end_prev = m_list[i][1]
            start_next = m_list[i + 1][0]
            b_prev, b_next = m_list[i][2], m_list[i + 1][2]
            c_prev, c_next = m_list[i][3], m_list[i + 1][3]
            sec_prev, sec_next = m_list[i][4], m_list[i + 1][4]

            gap_mins = start_next - end_prev
            # หากคาบติดกัน (gap < 15 นาที) และอาคารหรือวิทยาเขตไม่ตรงกัน
            if 0 <= gap_mins < 15 and (
                (b_prev and b_next and b_prev != b_next)
                or (c_prev and c_next and c_prev != c_next)
            ):
                day_name = DAY_NAMES[day]
                day_th = DAY_NAMES_TH[day]
                warnings.append(
                    WarningDetail(
                        code="W4",
                        severity="WARNING",
                        message_key="rush_building_move",
                        message_th=(
                            f"ต้องย้ายสถานที่เรียนระหว่าง {sec_prev} ({b_prev or c_prev}) "
                            f"และ {sec_next} ({b_next or c_next}) ในวัน{day_th} โดยมีเวลาพักเพียง {gap_mins} นาที"
                        ),
                        message_en=(
                            f"Tight transit time ({gap_mins} mins) between {sec_prev} ({b_prev or c_prev}) "
                            f"and {sec_next} ({b_next or c_next}) on {day_name}"
                        ),
                        detail={
                            "day": day_name,
                            "from_sec": sec_prev,
                            "to_sec": sec_next,
                            "gap_minutes": gap_mins,
                        },
                    )
                )

    # W5: HEAVY_DAYS (เรียน 6 - 7 วันต่อสัปดาห์)
    if profile["days_on_campus"] >= 6:
        warnings.append(
            WarningDetail(
                code="W5",
                severity="WARNING",
                message_key="heavy_days",
                message_th=(
                    f"ต้องเดินทางมามหาวิทยาลัยถึง {profile['days_on_campus']} วันต่อสัปดาห์ "
                    f"ซึ่งอาจทำให้เหนื่อยล้าสะสม"
                ),
                message_en=(
                    f"Heavy schedule requiring {profile['days_on_campus']} days on campus per week"
                ),
                detail={"days_on_campus": profile["days_on_campus"]},
            )
        )

    return warnings, profile
