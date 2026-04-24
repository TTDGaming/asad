from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Project, Translation
from ..schemas import TranslationCreate, TranslationOut, TranslationUpdate

router = APIRouter(prefix="/api/translations", tags=["translations"])


def _fmt_timestamp(value: float | None) -> str:
    if value is None:
        value = 0.0
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    ms = int(round((value - int(value)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


@router.get("", response_model=list[TranslationOut])
def list_translations(project_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Translation)
        .filter(Translation.project_id == project_id)
        .order_by(Translation.order_index.asc(), Translation.id.asc())
        .all()
    )


@router.post("", response_model=TranslationOut, status_code=201)
def create_translation(payload: TranslationCreate, db: Session = Depends(get_db)):
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(404, "Project not found")
    row = Translation(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{translation_id}", response_model=TranslationOut)
def update_translation(
    translation_id: int, payload: TranslationUpdate, db: Session = Depends(get_db)
):
    row = db.get(Translation, translation_id)
    if row is None:
        raise HTTPException(404, "Translation not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{translation_id}", status_code=204)
def delete_translation(translation_id: int, db: Session = Depends(get_db)):
    row = db.get(Translation, translation_id)
    if row is None:
        raise HTTPException(404, "Translation not found")
    db.delete(row)
    db.commit()
    return None


@router.get("/export/srt", response_class=PlainTextResponse)
def export_srt(project_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Translation)
        .filter(Translation.project_id == project_id)
        .order_by(Translation.order_index.asc(), Translation.id.asc())
        .all()
    )
    parts: list[str] = []
    for idx, row in enumerate(rows, start=1):
        start = _fmt_timestamp(row.start_time)
        end = _fmt_timestamp(row.end_time if row.end_time else (row.start_time or 0) + 2)
        text = row.translated_text.strip() or row.source_text.strip()
        parts.append(f"{idx}\n{start} --> {end}\n{text}\n")
    return "\n".join(parts)
