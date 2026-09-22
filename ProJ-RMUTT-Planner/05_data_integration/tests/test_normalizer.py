"""Unit tests for Course Normalizer & RapidFuzz Search Index"""
import pytest
from src.normalizer import (
    CourseItem,
    CourseSearchIndex,
    extract_base_code,
    normalize_course_code,
    parse_credit_detail,
)


def test_normalize_course_code():
    assert normalize_course_code("  04000201 - 62  ") == "04000201-62"
    assert normalize_course_code("c0407131") == "C0407131"
    assert normalize_course_code("eng 101") == "ENG101"
    assert normalize_course_code("04000201–62") == "04000201-62"  # en-dash


def test_extract_base_code():
    assert extract_base_code("04000201-62") == "04000201"
    assert extract_base_code("C0407131") == "C0407131"
    assert extract_base_code("040603001") == "040603001"


def test_parse_credit_detail():
    # รูปแบบ 3(2-2-5)
    cr = parse_credit_detail("3(2-2-5)")
    assert cr.credits == 3
    assert cr.lecture == 2
    assert cr.lab == 2
    assert cr.self_study == 5

    # รูปแบบ 3(3-0-6)
    cr2 = parse_credit_detail("3 ( 3 - 0 - 6 )")
    assert cr2.credits == 3
    assert cr2.lecture == 3
    assert cr2.lab == 0
    assert cr2.self_study == 6

    # รูปแบบตัวเลขเดี่ยว
    cr3 = parse_credit_detail("3")
    assert cr3.credits == 3
    assert cr3.lecture == 3


def test_course_search_index_exact_and_fuzzy():
    courses = [
        CourseItem(code="04000201-62", name_th="ฟิสิกส์ 1", name_en="Physics I"),
        CourseItem(code="04000203-62", name_th="แคลคูลัส 1", name_en="Calculus I"),
        CourseItem(code="040603001", name_th="การเขียนโปรแกรมคอมพิวเตอร์", name_en="Computer Programming"),
    ]
    index = CourseSearchIndex(courses)

    # ค้นหาด้วยรหัสตรง
    res_code = index.search("04000201-62")
    assert len(res_code) > 0
    assert res_code[0]["code"] == "04000201-62"

    # ค้นหาด้วย base code
    res_base = index.search("04000201")
    assert len(res_base) > 0
    assert res_base[0]["code"] == "04000201-62"

    # ค้นหาด้วยภาษาอังกฤษ
    res_en = index.search("Physics")
    assert len(res_en) > 0
    assert res_en[0]["code"] == "04000201-62"

    # ค้นหาด้วยคำสะกดผิด (Fuzzy) เช่น "calcolus" หรือ "ฟิสิก"
    res_fuzzy = index.search("calcolus")
    assert len(res_fuzzy) > 0
    assert res_fuzzy[0]["code"] == "04000203-62"
