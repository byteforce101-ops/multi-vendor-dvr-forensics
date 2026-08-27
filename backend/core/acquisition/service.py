import os
import shutil
import uuid
from pathlib import Path
from sqlalchemy.orm import Session

from backend.config.settings import get_settings
from backend.db.models import Evidence, EvidenceStatus
from backend.core.integrity.hashing import compute_hashes, verify_hash

def import_evidence(db: Session, case_id: str, source_path: str) -> Evidence:
    """Create an immutable local original and separate disposable working copy.

    Do not configure Supabase Storage as this original-evidence destination: it
    lacks evidence-retention/Object-Lock semantics. It remains suitable for
    extracted recordings and thumbnails after the video-processing phase.
    """
    if not os.path.isfile(source_path):
        raise FileNotFoundError(source_path)

    settings = get_settings()
    filename = os.path.basename(source_path)
    original_dest = settings.original_evidence_root / filename
    working_dest = settings.working_copy_root / filename

    settings.original_evidence_root.mkdir(parents=True, exist_ok=True)
    settings.working_copy_root.mkdir(parents=True, exist_ok=True)

    # Avoid silently overwriting prior evidence with the same filename —
    # each import gets a unique destination instead.
    if os.path.exists(original_dest):
        base, ext = os.path.splitext(filename)
        suffix = uuid.uuid4().hex[:8]
        filename = f"{base}_{suffix}{ext}"
        original_dest = settings.original_evidence_root / filename
        working_dest = settings.working_copy_root / filename

    shutil.copy2(source_path, original_dest)
    os.chmod(original_dest, 0o444)  # read-only, enforce the no-modification boundary
    shutil.copy2(original_dest, working_dest)

    evidence = Evidence(
        case_id=case_id,
        original_filename=filename,
        original_path=str(original_dest),
        working_copy_path=str(working_dest),
        status=EvidenceStatus.ACQUIRED,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


def import_uploaded_evidence(db: Session, case_id: str, upload) -> Evidence:
    """Stage a browser upload before passing it through the normal evidence workflow."""
    settings = get_settings()
    filename = Path(upload.filename or "evidence.bin").name
    staging_root = settings.working_copy_root / ".incoming"
    staging_root.mkdir(parents=True, exist_ok=True)
    staged_path = staging_root / f"{uuid.uuid4().hex}_{filename}"
    try:
        with staged_path.open("wb") as target:
            shutil.copyfileobj(upload.file, target, length=1024 * 1024)
        return import_evidence(db, case_id, str(staged_path))
    finally:
        upload.file.close()
        if staged_path.exists():
            staged_path.unlink()


def hash_evidence(db: Session, evidence: Evidence) -> Evidence:
    hashes = compute_hashes(evidence.working_copy_path)
    evidence.sha256 = hashes["sha256"]
    evidence.md5 = hashes["md5"]
    evidence.status = EvidenceStatus.HASHED
    db.commit()
    db.refresh(evidence)
    return evidence


def verify_evidence(db: Session, evidence: Evidence) -> Evidence:
    ok = verify_hash(evidence.working_copy_path, evidence.sha256)
    evidence.status = EvidenceStatus.VERIFIED if ok else EvidenceStatus.TAMPERED
    db.commit()
    db.refresh(evidence)
    return evidence
