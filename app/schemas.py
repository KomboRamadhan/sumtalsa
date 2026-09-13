from pydantic import BaseModel,Field
from typing import Optional

class LoginIn(BaseModel):
    email:str
    password:str

class RegisterIn(BaseModel):
    full_name:str
    email:str
    password:str=Field(min_length=8)
    role:str="teacher"
    school_name:Optional[str]=None

class ResourceIn(BaseModel):
    resource_type:str
    title:str
    content:str
    language:str="English"

class InterventionIn(BaseModel):
    learner_or_group:str
    topic:str
    evidence:str=""
    intervention_type:str=""
    plan:str=""

class FeedbackIn(BaseModel):
    module:str
    rating:int=Field(ge=1,le=5)
    comment:str=""

class CurriculumVersionIn(BaseModel):
    name:str
    version_year:str
    status:str="draft"
    source_reference:str=""
    notes:str=""

class GenerateIn(BaseModel):
    module:str
    prompt:str
