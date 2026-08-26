from backend.parsers.hikvision.parser import HikvisionParser

FIXTURE = "backend/tests/fixtures/hikvision_synthetic.dd"

def test_detect():
    parser = HikvisionParser()
    matched, confidence, info = parser.detect(FIXTURE)
    assert matched is True
    assert confidence > 0.5
    print("detect() OK:", info)

def test_validate():
    parser = HikvisionParser()
    is_valid, warnings = parser.validate(FIXTURE)
    assert is_valid is True
    print("validate() OK:", warnings)

def test_parse():
    parser = HikvisionParser()
    result = parser.parse(FIXTURE, "backend/storage/extracted/test_run")
    assert result.success is True
    assert len(result.recordings) == 3
    partial = [r for r in result.recordings if r.recovery_status == "PARTIAL"]
    assert len(partial) == 1  # the in-progress recording
    print("parse() OK:", [r.camera_id for r in result.recordings])

if __name__ == "__main__":
    test_detect()
    test_validate()
    test_parse()
    print("All checks passed.")   