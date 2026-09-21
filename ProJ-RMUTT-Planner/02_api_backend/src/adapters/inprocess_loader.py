from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from src.core.config import get_settings


def load_module_package(folder_name: str, alias: str) -> ModuleType:
    """โหลดแพ็กเกจ <folder_name>/src เป็นโมดูลชื่อไม่ซ้ำ (alias) แล้ว register ใน sys.modules

    จำเป็นเพราะโฟลเดอร์โมดูลขึ้นต้นด้วยตัวเลข (import ตรงไม่ได้) และหลายโมดูลใช้ชื่อแพ็กเกจ
    ภายในซ้ำกัน (relative import) — path อ่านจาก settings.MODULES_ROOT (env MODULES_ROOT)
    อ่านโค้ดของโมดูลปลายทางอย่างเดียว ห้ามแก้
    """

    if alias in sys.modules:
        return sys.modules[alias]

    modules_root = Path(get_settings().MODULES_ROOT)
    package_dir = modules_root / folder_name / "src"
    init_file = package_dir / "__init__.py"

    if not init_file.exists():
        raise RuntimeError(
            f"ไม่พบโมดูล {folder_name} ที่ {package_dir} — ต้องมีโฟลเดอร์ {folder_name}/src วางไว้ที่ "
            f"MODULES_ROOT ({modules_root}) ก่อนใช้ ADAPTER=inprocess "
            "(ตอนนี้โมดูลนี้ยังไม่มีโค้ด ให้ใช้ ADAPTER=mock หรือ http ไปก่อน)"
        )

    spec = importlib.util.spec_from_file_location(
        alias, init_file, submodule_search_locations=[str(package_dir)]
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"โหลด spec ของโมดูล {folder_name} ไม่สำเร็จ ({package_dir})")

    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module
