from fastapi import FastAPI, UploadFile, File, Depends
from typing import Annotated

from .services.storage_service import StorageService, get_storage_service

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "User-Service"}

@app.post("/upload/")
async def upload_file(
    file: UploadFile, 
    storage: Annotated[StorageService, Depends(get_storage_service)]
):
    try:
        storage.upload(file.filename, file.file)
        # In a real app, you would save metadata to a database here
        return {"filename": file.filename, "url": storage.get_public_url(file.filename)}
    except Exception as e:
        return {"error": str(e)}

# In a real app, you'd have more endpoints for user management, etc.
# @app.get("/users/me")
# def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
#    # Decode token based on auth provider (Firebase, Cognito) and return user
#    return {"user": "details"}