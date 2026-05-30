from pydantic import BaseModel, ConfigDict
from datetime import datetime

class UserCreate(BaseModel):
    username : str 
    email : str 
    password : str 

class UserRead(BaseModel):
    id : int
    username : str 
    email : str 
    created_at : datetime 
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token : str
    token_type : str = "bearer"
