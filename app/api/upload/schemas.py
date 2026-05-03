from pydantic import BaseModel

class UploadResponse(BaseModel):
    status: str
    file_location: str