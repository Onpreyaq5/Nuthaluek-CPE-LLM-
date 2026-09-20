"""Prerequisite Graph (DAG) Engine
- สร้าง DAG ของวิชาบังคับก่อนด้วย NetworkX
- ตรวจจับ Cycle ในหลักสูตร (ถ้ามี = ข้อผิดพลาด)
- คำนวณรายวิชาที่ปลดล็อกแล้ว (Prereq ครบทุกตัว)
- คำนวณ Critical Path / Depth สำหรับจัด Priority P2_UNLOCK
"""
from __future__ import annotations

from typing import Any

import networkx as nx

from .normalizer import extract_base_code, normalize_course_code


class PrerequisiteDAG:
    """กราฟวิชาบังคับก่อน: Node = รหัสวิชา, Directed Edge = (A, B) หมายถึง A ต้องผ่านก่อน B"""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_course(self, course_code: str, **attributes) -> None:
        """เพิ่มรายวิชาในกราฟ"""
        code = normalize_course_code(course_code)
        if not self.graph.has_node(code):
            self.graph.add_node(code, **attributes)
        else:
            self.graph.nodes[code].update(attributes)

    def add_prerequisite(self, course_code: str, prereq_code: str, prereq_type: str = "before") -> None:
        """เพิ่มความสัมพันธ์: prereq_code ต้องผ่านก่อน course_code
        prereq_type: 'before' (ต้องผ่านก่อน) หรือ 'concurrent' (ลงพร้อมกันได้)
        """
        c_code = normalize_course_code(course_code)
        p_code = normalize_course_code(prereq_code)
        self.add_course(c_code)
        self.add_course(p_code)
        # Edge จาก prereq -> course
        self.graph.add_edge(p_code, c_code, type=prereq_type)

    def is_valid_dag(self) -> bool:
        """ตรวจสอบว่ากราฟไม่มีวงวน (DAG)"""
        return nx.is_directed_acyclic_graph(self.graph)

    def find_cycles(self) -> list[list[str]]:
        """คืนรายการวงวนที่พบ (ถ้ามี)"""
        try:
            return list(nx.simple_cycles(self.graph))
        except Exception:
            return []

    def get_direct_prerequisites(self, course_code: str) -> list[str]:
        """คืนค่ารายวิชาที่ต้องผ่านก่อนวิชานี้โดยตรง"""
        code = normalize_course_code(course_code)
        if not self.graph.has_node(code):
            return []
        return sorted(list(self.graph.predecessors(code)))

    def get_all_prerequisites(self, course_code: str) -> set[str]:
        """คืนค่ารายวิชาทั้งหมดที่ต้องผ่านก่อน (Ancestors ทั้งหมดในกราฟ)"""
        code = normalize_course_code(course_code)
        if not self.graph.has_node(code):
            return set()
        return nx.ancestors(self.graph, code)

    def get_direct_unlocks(self, course_code: str) -> list[str]:
        """คืนค่ารายวิชาที่วิชานี้ปลดล็อกได้โดยตรง (Successors)"""
        code = normalize_course_code(course_code)
        if not self.graph.has_node(code):
            return []
        return sorted(list(self.graph.successors(code)))

    def get_all_unlocks(self, course_code: str) -> set[str]:
        """คืนค่ารายวิชาทั้งหมดที่วิชานี้จะปลดล็อกต่อเป็นทอดๆ (Descendants)"""
        code = normalize_course_code(course_code)
        if not self.graph.has_node(code):
            return set()
        return nx.descendants(self.graph, code)

    def is_eligible(self, course_code: str, passed_courses: set[str]) -> bool:
        """ตรวจสอบว่านักศึกษามีสิทธิ์ลงวิชานี้หรือไม่ (ผ่าน prereq ครบทุกตัว และยังไม่เคยผ่านวิชานี้)"""
        code = normalize_course_code(course_code)
        # ถ้ารหัสวิชาหรือ base code อยู่ใน passed_courses แล้ว ถือว่าผ่านแล้ว
        norm_passed = {normalize_course_code(p) for p in passed_courses}
        base_passed = {extract_base_code(p) for p in passed_courses}

        if code in norm_passed or extract_base_code(code) in base_passed:
            return False

        prereqs = self.get_direct_prerequisites(code)
        for p in prereqs:
            if p not in norm_passed and extract_base_code(p) not in base_passed:
                return False
        return True

    def get_eligible_courses(
        self,
        passed_courses: set[str],
        candidate_courses: list[str] | None = None
    ) -> list[str]:
        """คำนวณรายวิชาที่ 'ปลดล็อก' ได้ในเทอมนี้
        หากระบุ candidate_courses จะกรองเฉพาะในรายการนั้น มิฉะนั้นจะตรวจทุกวิชาในกราฟ
        """
        targets = candidate_courses if candidate_courses is not None else list(self.graph.nodes)
        eligible = [c for c in targets if self.is_eligible(c, passed_courses)]
        return sorted(eligible)

    def calculate_critical_path_depth(self, course_code: str) -> int:
        """คำนวณความลึกของสายวิชาบังคับที่ต่อจากวิชานี้ (Longest path length จากโหนดนี้)"""
        code = normalize_course_code(course_code)
        if not self.graph.has_node(code):
            return 0

        descendants = nx.descendants(self.graph, code)
        if not descendants:
            return 0

        subgraph = self.graph.subgraph(descendants | {code})
        try:
            return nx.dag_longest_path_length(subgraph)
        except Exception:
            return len(descendants)

    def calculate_critical_path_scores(self) -> dict[str, int]:
        """คำนวณคะแนน Critical Path สำหรับทุกวิชาในกราฟ
        คะแนน = ความลึกของสายวิชา (depth) * 10 + จำนวนวิชาที่ปลดล็อกได้ทั้งหมด
        """
        scores: dict[str, int] = {}
        for node in self.graph.nodes:
            depth = self.calculate_critical_path_depth(node)
            num_descendants = len(self.get_all_unlocks(node))
            scores[node] = depth * 10 + num_descendants
        return scores

    def get_course_prereq_info(self, course_code: str) -> dict[str, Any]:
        """สรุปข้อมูลวิชาบังคับก่อนและวิชาที่ปลดล็อกสำหรับ Course API"""
        code = normalize_course_code(course_code)
        direct_prereqs = self.get_direct_prerequisites(code)
        all_prereqs = sorted(list(self.get_all_prerequisites(code)))
        direct_unlocks = self.get_direct_unlocks(code)
        all_unlocks = sorted(list(self.get_all_unlocks(code)))
        depth = self.calculate_critical_path_depth(code)

        return {
            "course_code": code,
            "direct_prerequisites": direct_prereqs,
            "all_prerequisites": all_prereqs,
            "direct_unlocks": direct_unlocks,
            "all_unlocks": all_unlocks,
            "critical_path_depth": depth,
            "critical_path_score": depth * 10 + len(all_unlocks),
        }
