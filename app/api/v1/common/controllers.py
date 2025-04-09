from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends
from app.api.v1.common.services.insert_base_data import InsertBaseData
from app.db.database import get_db

router = APIRouter(
  prefix="/common",
  tags=["Common"],
  responses={404: {"description": "Not found"}}
)

@router.post("/insert-base-data/")
async def insert_base_data(db: Session = Depends(get_db)):
    insert_base_data = InsertBaseData(db)
    insert_base_data.insert_base_data()
    return {"message": "Datos insertados correctamente"}
