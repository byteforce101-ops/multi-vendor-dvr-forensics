from backend.core.search.query_parser import parse_query, SearchFilter
from backend.db.repositories.events_repository import EventsRepository


class SearchService:
    def __init__(self, events_repo: EventsRepository):
        self.events_repo = events_repo

    def search(self, case_id: str, nl_query: str) -> dict:
        filt: SearchFilter = parse_query(nl_query)
        results = self.events_repo.search_events(
            case_id=case_id,
            event_types=filt.event_types,
            start_time=filt.start_time,
            end_time=filt.end_time,
            camera_id=filt.camera_id,
            min_confidence=filt.min_confidence,
        )
        return {"query": nl_query, "filter": filt.model_dump(mode="json"), "results": results}
