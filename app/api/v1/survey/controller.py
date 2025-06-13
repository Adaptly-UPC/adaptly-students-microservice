from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db

from app.api.v1.survey.services.survey_processor import SurveyProcessor

router = APIRouter(
    prefix="/survey",
    tags=["Survey"],
    responses={404: {"description": "Not found"}}
)

@router.post("/save-survey/")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    processor = SurveyProcessor(db)
    excel_content = await file.read()
    return processor.process_student_survey(excel_content)

