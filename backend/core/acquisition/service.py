import os
import shutil
from sqlalchemy.orm import Session
from backend.db.models import Evidence, EvidenceStatus
from backend.core.integrity.hashing import compute_hashes, verify_hash

WORKING_COPY_ROOT = "backend/storage/working_copies"
ORIGINAL_ROOT = "backend/storage/original"

def import_evidence(db: Session, case_id: str, source_path: str) -> Evidence:
    """Copies source into original/ (untouched reference), then makes a working copy.
    Never reads source_path again after this — all downstream ops use working_copy_path."""
    if not os.path.isfile(source_path):
        raise FileNotFoundError(source_path)

    filename = os.path.basename(source_path)
    original_dest = os.path.join(ORIGINAL_ROOT, filename)
    working_dest = os.path.join(WORKING_COPY_ROOT, filename)

    os.makedirs(ORIGINAL_ROOT, exist_ok=True)
    os.makedirs(WORKING_COPY_ROOT, exist_ok=True)

    shutil.copy2(source_path, original_dest)
    os.chmod(original_dest, 0o444)  # read-only, enforce the no-modification boundary
    shutil.copy2(original_dest, working_dest)

    evidence = Evidence(
        case_id=case_id,
        original_filename=filename,
        original_path=original_dest,
        working_copy_path=working_dest,
        status=EvidenceStatus.ACQUIRED,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence

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