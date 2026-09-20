import pytest
from backend.config.settings import get_settings

@pytest.fixture(autouse=True)
def isolate_storage(tmp_path, monkeypatch):
    """
    Autouse fixture to isolate test runs from the real backend/storage directory.
    Monkeypatches ORIGINAL_EVIDENCE_ROOT, WORKING_COPY_ROOT, and EXTRACTED_MEDIA_ROOT
    to temporary directories and clears the get_settings LRU cache.
    """
    orig_root = tmp_path / "storage" / "original"
    work_root = tmp_path / "storage" / "working_copies"
    extr_root = tmp_path / "storage" / "extracted"
    
    orig_root.mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)
    extr_root.mkdir(parents=True, exist_ok=True)
    
    monkeypatch.setenv("ORIGINAL_EVIDENCE_ROOT", str(orig_root))
    monkeypatch.setenv("WORKING_COPY_ROOT", str(work_root))
    monkeypatch.setenv("EXTRACTED_MEDIA_ROOT", str(extr_root))
    
    get_settings.cache_clear()
    try:
        yield
    finally:
        get_settings.cache_clear()
