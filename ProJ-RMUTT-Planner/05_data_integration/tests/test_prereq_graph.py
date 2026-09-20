"""Unit tests for Prerequisite Graph (DAG) Engine"""
import pytest
from src.prereq_graph import PrerequisiteDAG


def test_dag_creation_and_prereqs():
    dag = PrerequisiteDAG()
    # A -> B -> C
    dag.add_prerequisite("B", "A")
    dag.add_prerequisite("C", "B")

    assert dag.is_valid_dag()
    assert dag.get_direct_prerequisites("B") == ["A"]
    assert dag.get_all_prerequisites("C") == {"A", "B"}
    assert dag.get_direct_unlocks("A") == ["B"]
    assert dag.get_all_unlocks("A") == {"B", "C"}


def test_cycle_detection():
    dag = PrerequisiteDAG()
    # A -> B -> C -> A (มี cycle)
    dag.add_prerequisite("B", "A")
    dag.add_prerequisite("C", "B")
    dag.add_prerequisite("A", "C")

    assert not dag.is_valid_dag()
    cycles = dag.find_cycles()
    assert len(cycles) > 0


def test_eligible_courses_unlock():
    dag = PrerequisiteDAG()
    dag.add_prerequisite("CAL2", "CAL1")
    dag.add_prerequisite("PROG2", "PROG1")
    dag.add_prerequisite("DATA_STRUCT", "PROG2")

    # ถ้ายังไม่เคยผ่านอะไรเลย
    unlocked = dag.get_eligible_courses(passed_courses=set())
    # CAL1 และ PROG1 ไม่มี prereq -> ปลดล็อกได้
    assert set(unlocked) == {"CAL1", "PROG1"}

    # ถ้าผ่าน CAL1 และ PROG1 แล้ว
    unlocked2 = dag.get_eligible_courses(passed_courses={"CAL1", "PROG1"})
    assert set(unlocked2) == {"CAL2", "PROG2"}

    # ถ้าผ่าน PROG2 เพิ่ม
    unlocked3 = dag.get_eligible_courses(passed_courses={"CAL1", "PROG1", "PROG2"})
    assert set(unlocked3) == {"CAL2", "DATA_STRUCT"}


def test_critical_path_depth_and_scores():
    dag = PrerequisiteDAG()
    # Chain: A -> B -> C -> D (ความลึก A = 3)
    # Branch: A -> E (ความลึก 1)
    dag.add_prerequisite("B", "A")
    dag.add_prerequisite("C", "B")
    dag.add_prerequisite("D", "C")
    dag.add_prerequisite("E", "A")

    assert dag.calculate_critical_path_depth("A") == 3
    assert dag.calculate_critical_path_depth("B") == 2
    assert dag.calculate_critical_path_depth("D") == 0

    scores = dag.calculate_critical_path_scores()
    # A ปลดล็อก 4 วิชา (B,C,D,E) และ depth 3 -> คะแนนสูงสุด
    assert scores["A"] > scores["B"]
    assert scores["B"] > scores["C"]
