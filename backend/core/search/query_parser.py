import json
import os
from datetime import datetime, timezone
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class SearchFilter(BaseModel):
    event_types: list[str] | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    camera_id: str | None = None
    min_confidence: float | None = None

SYSTEM_PROMPT = """You convert an investigator's natural-language evidence search into a JSON filter.
Detection event_type values follow the pattern "<OBJECT>_DETECTED" (e.g. PERSON_DETECTED, VEHICLE_DETECTED,
BOTTLE_DETECTED) or "MOTION" for generic motion. Infer the right event_type(s) from the object(s) mentioned.
Return ONLY JSON, no prose, in this shape:
{"event_types": [...] | null, "start_time": "ISO8601" | null, "end_time": "ISO8601" | null,
 "camera_id": "..." | null, "min_confidence": float | null}
If a date isn't mentioned, assume the reference date given. Do not invent a camera_id unless one is stated.
If the query implies spatial/directional logic (e.g. "enters through the gate"), leave camera_id/event_types
as your best guess but do not fabricate a filter field for direction - that isn't supported yet.
"""

def parse_query(nl_query: str, reference_date: datetime | None = None, api_key: str | None = None) -> SearchFilter:
    from groq import Groq
    key = api_key or os.getenv("GROQ_API_KEY")
    client = Groq(api_key=key) if key else Groq()
    ref = (reference_date or datetime.now(timezone.utc)).isoformat()
    resp = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        max_tokens=300,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Reference date/time: {ref}\nQuery: {nl_query}"},
        ],
        response_format={"type": "json_object"},
    )
    return SearchFilter(**json.loads(resp.choices[0].message.content.strip()))
