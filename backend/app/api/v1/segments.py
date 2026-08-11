from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.schemas import SegmentCreate
from app.storage.database import get_db
from app.storage.repositories import SegmentRepository, WatchlistRepository

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get("")
def list_segments(session: Session = Depends(get_db)):
    return SegmentRepository(session).list_all()


@router.post("")
def create_segment(payload: SegmentCreate, session: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Segment name cannot be empty")
    repo = SegmentRepository(session)
    if repo.get_by_name(name):
        raise HTTPException(status_code=409, detail="A segment with this name already exists")
    return repo.create(name)


@router.delete("/{segment_id}")
def delete_segment(segment_id: int, session: Session = Depends(get_db)):
    repo = SegmentRepository(session)
    segment = repo.get_by_id(segment_id)
    if not segment:
        raise HTTPException(status_code=404, detail="Not found")
    WatchlistRepository(session).clear_segment(segment_id)
    repo.delete(segment_id)
    return {"ok": True}
