from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path


TEST_ROOT = Path(tempfile.mkdtemp(prefix="infohound-tests-")).resolve()
os.environ["INFOHOUND_DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'infohound.db').as_posix()}"
os.environ["INFOHOUND_EXPORT_PATH"] = (TEST_ROOT / "exports").as_posix()
os.environ["INFOHOUND_RAW_STORAGE_PATH"] = (TEST_ROOT / "raw").as_posix()


def reset_test_state() -> None:
    from backend.app.db import Base, engine

    export_dir = TEST_ROOT / "exports"
    raw_dir = TEST_ROOT / "raw"

    if export_dir.exists():
        shutil.rmtree(export_dir)
    if raw_dir.exists():
        shutil.rmtree(raw_dir)

    export_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        reset_test_state()
