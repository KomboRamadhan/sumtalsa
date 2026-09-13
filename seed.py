from app.database import Base,engine,SessionLocal
from app.models import School,User,CurriculumVersion,CurriculumNode
from app.security import hash_password

Base.metadata.create_all(bind=engine)
db=SessionLocal()
school=db.query(School).filter(School.name=="SumTalsa Demo School").first()
if not school:
    school=School(name="SumTalsa Demo School",region="Tanzania")
    db.add(school);db.flush()

users=[
("Teacher Demo","teacher@sumtalsa.local","Teacher123!","teacher"),
("Student Demo","student@sumtalsa.local","Student123!","student"),
("Parent Demo","parent@sumtalsa.local","Parent123!","parent"),
("School Admin","admin@sumtalsa.local","Admin123!","school_admin"),
("Super Admin","super@sumtalsa.local","Super123!","super_admin"),
]
for name,email,pw,role in users:
    if not db.query(User).filter(User.email==email).first():
        db.add(User(full_name=name,email=email,password_hash=hash_password(pw),role=role,school_id=school.id))

cv=db.query(CurriculumVersion).filter(CurriculumVersion.name=="Tanzania Ordinary Secondary Curriculum Form I-IV").first()
if not cv:
    cv=CurriculumVersion(name="Tanzania Ordinary Secondary Curriculum Form I-IV",version_year="2023",status="approved",source_reference="TIE / MoEST, Curriculum for Ordinary Secondary Education Form I-IV, approved 9 August 2023, ISBN 978-9987-09-856-9",notes="Authoritative curriculum source verified. Subject competency nodes require syllabus-level verification.")
    db.add(cv);db.flush()
    db.add_all([
      CurriculumNode(curriculum_version_id=cv.id,class_level="Form I",subject_name="Biology",topic="Introduction to Biology",verified=False),
      CurriculumNode(curriculum_version_id=cv.id,class_level="Form II",subject_name="Geography",topic="Map Reading",verified=False),
    ])
db.commit();db.close()
print("Seed complete.")
