from fastapi import APIRouter

from models.classification import CLASSIFICATION_META, Classification
from schemas.classification_schema import ClassificationRead

router = APIRouter(tags=["meta"])


@router.get("/meta/classifications", response_model=list[ClassificationRead])
def list_classifications():
    return [
        ClassificationRead(key=classification.value, **CLASSIFICATION_META[classification])
        for classification in Classification
    ]