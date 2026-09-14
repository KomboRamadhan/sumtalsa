from pydantic import BaseModel,Field
from typing import Optional

class LoginIn(BaseModel):
    email:str
    password:str

class RegisterIn(BaseModel):
    full_name:str=Field(min_length=2,max_length=180)
    email:str
    password:str=Field(min_length=8)
    role:str="teacher"
    school_id:Optional[int]=None
    school_name:Optional[str]=None
    education_level:Optional[str]=None
    class_level:Optional[str]=None

class ForgotPasswordIn(BaseModel):
    email:str

class AdminPasswordResetIn(BaseModel):
    password:str=Field(min_length=8)

class AdminSchoolIn(BaseModel):
    name:str=Field(min_length=2,max_length=180)
    region:Optional[str]=None
    council:Optional[str]=None

class AdminUserIn(BaseModel):
    full_name:str=Field(min_length=2,max_length=180)
    email:str
    password:str=Field(min_length=8)
    role:str="teacher"
    school_id:Optional[int]=None
    education_level:Optional[str]=None
    class_level:Optional[str]=None

class UserStatusIn(BaseModel):
    active:bool

class ProfileEducationIn(BaseModel):
    education_level:str
    class_level:str

class ResourceIn(BaseModel):
    resource_type:str
    title:str
    content:str
    language:str="English"
    material_type:Optional[str]=None
    education_level:Optional[str]=None
    class_level:Optional[str]=None
    subject_name:Optional[str]=None
    visibility:str="school"

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
