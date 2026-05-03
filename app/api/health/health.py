from fastapi import APIRouter, status

router = APIRouter(prefix="/api")


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    Checks the health of the application.
    """
    return {"status": "ok"}
