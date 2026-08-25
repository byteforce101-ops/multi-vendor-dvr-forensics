from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.db.models import Base, Case, Evidence
from backend.core.acquisition.service import import_evidence, hash_evidence, verify_evidence

engine = create_engine("sqlite:///backend/forensics.db")
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI(title="DVR Forensic Platform - Phase 0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/cases")
def create_case(name: str, investigator: str, db: Session = Depends(get_db)):
    case = Case(name=name, investigator=investigator)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case

@app.post("/cases/{case_id}/evidence")
def add_evidence(case_id: str, source_path: str, db: Session = Depends(get_db)):
    if not db.get(Case, case_id):
        raise HTTPException(404, "Case not found")
    evidence = import_evidence(db, case_id, source_path)
    evidence = hash_evidence(db, evidence)
    return evidence

@app.post("/evidence/{evidence_id}/verify")
def verify(evidence_id: str, db: Session = Depends(get_db)):
    evidence = db.get(Evidence, evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    return verify_evidence(db, evidence)

@app.get("/cases/{case_id}/evidence")
def list_evidence(case_id: str, db: Session = Depends(get_db)):
    return db.query(Evidence).filter(Evidence.case_id == case_id).all()