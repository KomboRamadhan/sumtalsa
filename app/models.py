from sqlalchemy import Column,Integer,String,Text,DateTime,ForeignKey,Boolean
from datetime import datetime
from .database import Base

class School(Base):
    __tablename__="schools"
    id=Column(Integer,primary_key=True,index=True)
    name=Column(String(180),nullable=False,unique=True)
    region=Column(String(120))
    council=Column(String(120))
    created_at=Column(DateTime,default=datetime.utcnow)

class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True,index=True)
    school_id=Column(Integer,ForeignKey("schools.id"),nullable=True)
    full_name=Column(String(180),nullable=False)
    email=Column(String(180),nullable=False,unique=True,index=True)
    password_hash=Column(String(255),nullable=False)
    role=Column(String(40),nullable=False,default="teacher")
    education_level=Column(String(60),nullable=True)
    class_level=Column(String(40),nullable=True)
    active=Column(Boolean,default=True)
    created_at=Column(DateTime,default=datetime.utcnow)

class CurriculumVersion(Base):
    __tablename__="curriculum_versions"
    id=Column(Integer,primary_key=True,index=True)
    name=Column(String(220),nullable=False)
    version_year=Column(String(20),nullable=False)
    status=Column(String(40),default="draft")
    source_reference=Column(Text)
    notes=Column(Text)
    created_by=Column(Integer,ForeignKey("users.id"),nullable=True)
    created_at=Column(DateTime,default=datetime.utcnow)

class CurriculumNode(Base):
    __tablename__="curriculum_nodes"
    id=Column(Integer,primary_key=True,index=True)
    curriculum_version_id=Column(Integer,ForeignKey("curriculum_versions.id"),nullable=False)
    class_level=Column(String(40),nullable=False)
    subject_name=Column(String(120),nullable=False)
    subject_code=Column(String(40))
    competency=Column(Text)
    specific_competency=Column(Text)
    topic=Column(String(220))
    subtopic=Column(String(220))
    learning_outcome=Column(Text)
    source_page=Column(String(80))
    verified=Column(Boolean,default=False)

class Resource(Base):
    __tablename__="resources"
    id=Column(Integer,primary_key=True,index=True)
    owner_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    school_id=Column(Integer,ForeignKey("schools.id"),nullable=True)
    resource_type=Column(String(60),nullable=False)
    material_type=Column(String(80),nullable=True)
    education_level=Column(String(60),nullable=True)
    class_level=Column(String(40),nullable=True)
    subject_name=Column(String(120),nullable=True)
    visibility=Column(String(20),default="school")
    title=Column(String(220),nullable=False)
    content=Column(Text,nullable=False)
    language=Column(String(20),default="English")
    created_at=Column(DateTime,default=datetime.utcnow)

class Intervention(Base):
    __tablename__="interventions"
    id=Column(Integer,primary_key=True,index=True)
    owner_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    learner_or_group=Column(String(180),nullable=False)
    topic=Column(String(220),nullable=False)
    evidence=Column(Text)
    intervention_type=Column(String(120))
    plan=Column(Text)
    status=Column(String(40),default="open")
    created_at=Column(DateTime,default=datetime.utcnow)

class Feedback(Base):
    __tablename__="feedback"
    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=False)
    module=Column(String(120))
    rating=Column(Integer)
    comment=Column(Text)
    created_at=Column(DateTime,default=datetime.utcnow)

class AuditLog(Base):
    __tablename__="audit_logs"
    id=Column(Integer,primary_key=True,index=True)
    user_id=Column(Integer,ForeignKey("users.id"),nullable=True)
    action=Column(String(180),nullable=False)
    details=Column(Text)
    created_at=Column(DateTime,default=datetime.utcnow)
