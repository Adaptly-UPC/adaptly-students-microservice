from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.v1.students.services.excel_inspect import inspect_excel

from app.api.v1.students.services.excel_proccessor_high_level import ExcelProcessor as ExcelProcessorHighSchool
from app.api.v1.students.services.excel_processor_primary_level import ExcelProcessor as ExcelProcessorPrimary

router = APIRouter(
    prefix="/students",
    tags=["Students"],
    responses={404: {"description": "Not found"}}
)


@router.post("/upload-excel/")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    rows_inserted = inspect_excel(content)
    return {"message": "Datos insertados correctamente", "rows_inserted": rows_inserted}


@router.post("/save-high-school-grades/")
async def parse_save_data(file: UploadFile = File(...), db: Session = Depends
(get_db)):
    processor = ExcelProcessorHighSchool(db)
    excel_content = await file.read()
    return processor.process_excel(excel_content)


@router.post("/save-primary-grades/")
async def parse_save_primary_data(file: UploadFile = File(...), db: Session = Depends(get_db)):
    processor = ExcelProcessorPrimary(db)
    excel_content = await file.read()
    return processor.process_student_califications(excel_content)