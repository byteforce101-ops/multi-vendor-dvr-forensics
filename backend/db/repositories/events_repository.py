from sqlalchemy.orm import Session
from backend.db.models import Event


class EventsRepository:
    def __init__(self, db: Session):
        self.db = db

    def search_events(self, case_id, event_types=None, start_time=None,
                       end_time=None, camera_id=None, min_confidence=None):
        query = self.db.query(Event).filter(Event.case_id == case_id)
        if event_types:
            query = query.filter(Event.event_type.in_(event_types))
        if start_time:
            query = query.filter(Event.end_time >= start_time)
        if end_time:
            query = query.filter(Event.start_time <= end_time)
        if camera_id:
            query = query.filter(Event.camera_id == camera_id)
        if min_confidence:
            query = query.filter(Event.confidence >= min_confidence)
        return query.order_by(Event.start_time).all()
