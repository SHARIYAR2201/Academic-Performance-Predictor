from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.prediction import PredictionResponse
from app.services import academic_service, prediction_service

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/students/{student_id}", response_model=PredictionResponse, status_code=201)
def generate_prediction(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)) -> PredictionResponse:
    academic_service.assert_user_can_access_student(db, current_user, student_id)
    return prediction_service.generate_prediction_for_student(db, student_id)
