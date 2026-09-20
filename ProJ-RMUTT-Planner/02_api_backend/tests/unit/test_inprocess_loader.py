from __future__ import annotations

import pytest

from src.adapters.inprocess_loader import load_module_package


def test_raises_clear_error_when_module_folder_missing() -> None:
    with pytest.raises(RuntimeError, match="ไม่พบโมดูล"):
        load_module_package("99_does_not_exist", "mod99_test")
