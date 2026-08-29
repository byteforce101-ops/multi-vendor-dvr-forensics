import hashlib

CHUNK_SIZE = 8192

def compute_hashes(filepath: str) -> dict:
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
            md5.update(chunk)
    return {"sha256": sha256.hexdigest(), "md5": md5.hexdigest()}

def verify_hash(filepath: str, expected_sha256: str) -> bool:
    return compute_hashes(filepath)["sha256"] == expected_sha256
