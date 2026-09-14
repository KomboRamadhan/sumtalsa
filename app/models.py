from fastapi import FastAPI,Depends,HTTPException,Header,Query
from fastapi.staticfiles import StaticFiles
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import inspect,text,or_
from pathlib import Path
import os

from .database import Base,engine,get_db
from . import models,schemas
from .security import hash_password,verify_password,create_token,decode_token
from .ai_service import generate

Base.metadata.create_all(bind=engine)

def _add_column_if_missing(table_name,column_name,column_sql):
    inspector=inspect(engine)
    columns={c["name"] for c in inspector.get_columns(table_name)}
    if column_name not in columns:
        with engine.begin() as conn:
            conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}'))

def migrate_schema():
    _add_column_if_missing("users","education_level","VARCHAR(60)")
    _add_column_if_missing("users","class_level","VARCHAR(40)")
    _add_column_if_missing("resources","material_type","VARCHAR(80)")
    _add_column_if_missing("resources","education_level","VARCHAR(60)")
    _add_column_if_missing("resources","class_level","VARCHAR(40)")
    _add_column_if_missing("resources","subject_name","VARCHAR(120)")
    _add_column_if_missing("resources","visibility","VARCHAR(20) DEFAULT 'school'")

migrate_schema()
app=FastAPI(title="SumTalsa API",version="1.4.0")

if os.getenv("FORCE_HTTPS","false").lower()=="true":
    app.add_middleware(HTTPSRedirectMiddleware)
allowed_hosts=os.getenv("ALLOWED_HOSTS","*").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
STATIC=Path(__file__).resolve().parent.parent/"static"

EDUCATION_LEVELS={
    "Primary Education":[f"Standard {r}" for r in ["I","II","III","IV","V","VI","VII"]],
    "Ordinary Level":[f"Form {r}" for r in ["I","II","III","IV"]],
    "Advanced Level":[f"Form {r}" for r in ["V","VI"]],
}

def validate_education(level,class_level,required=False):
    if not level and not class_level and not required:
        return
    if level not in EDUCATION_LEVELS:
        raise HTTPException(400,"Choose a valid education level")
    if class_level not in EDUCATION_LEVELS[level]:
        raise HTTPException(400,"Choose a valid class/form for the selected education level")

@app.on_event("startup")
def bootstrap_super_admin():
    email=os.getenv("BOOTSTRAP_SUPERADMIN_EMAIL","").strip().lower()
    password=os.getenv("BOOTSTRAP_SUPERADMIN_PASSWORD","").strip()
    name=os.getenv("BOOTSTRAP_SUPERADMIN_NAME","SumTalsa Super Admin").strip()
    if not email or not password:
        return
    db=next(get_db())
    try:
        existing=db.query(models.User).filter(models.User.email==email).first()
        if not existing:
            school=db.query(models.School).filter(models.School.name=="SumTalsa Platform").first()
            if not school:
                school=models.School(name="SumTalsa Platform",region="Tanzania")
                db.add(school); db.flush()
            user=models.User(full_name=name,email=email,password_hash=hash_password(password),role="super_admin",school_id=school.id)
            db.add(user); db.commit()
    finally:
        db.close()

def current_user(authorization:str=Header(default=""),db:Session=Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401,"Missing token")
    try:
        data=decode_token(authorization.split(" ",1)[1]); uid=int(data["sub"])
    except Exception:
        raise HTTPException(401,"Invalid or expired token")
    user=db.query(models.User).filter(models.User.id==uid,models.User.active==True).first()
    if not user:
        raise HTTPException(401,"User not found or inactive")
    return user

def require_roles(*roles):
    def dep(user=Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403,"Insufficient permission")
        return user
    return dep

def user_payload(user):
    return {"id":user.id,"name":user.full_name,"email":user.email,"role":user.role,"school_id":user.school_id,
            "education_level":user.education_level,"class_level":user.class_level}

@app.get("/api/health")
def health(): return {"ok":True,"service":"SumTalsa","version":"1.4.0"}

@app.get("/api/public/education-levels")
def public_education_levels(): return EDUCATION_LEVELS

@app.get("/api/public/schools")
def public_schools(db:Session=Depends(get_db)):
    xs=db.query(models.School).filter(models.School.name!="SumTalsa Platform").order_by(models.School.name.asc()).all()
    return [{"id":x.id,"name":x.name,"region":x.region or "","council":x.council or ""} for x in xs]

@app.post("/api/register")
def register(body:schemas.RegisterIn,db:Session=Depends(get_db)):
    if body.role not in {"teacher","student","parent"}:
        raise HTTPException(403,"Only Teacher, Student or Parent can self-register")
    email=body.email.strip().lower()
    if db.query(models.User).filter(models.User.email==email).first(): raise HTTPException(409,"Email already registered")
    school=None
    if body.school_id:
        school=db.query(models.School).filter(models.School.id==body.school_id,models.School.name!="SumTalsa Platform").first()
    elif body.school_name:
        school=db.query(models.School).filter(models.School.name==body.school_name.strip(),models.School.name!="SumTalsa Platform").first()
    if not school: raise HTTPException(400,"Choose a registered school")
    if body.role=="student": validate_education(body.education_level,body.class_level,required=True)
    elif body.education_level or body.class_level: validate_education(body.education_level,body.class_level)
    user=models.User(full_name=body.full_name.strip(),email=email,password_hash=hash_password(body.password),role=body.role,
                     school_id=school.id,education_level=body.education_level,class_level=body.class_level,active=True)
    db.add(user); db.flush(); db.add(models.AuditLog(user_id=user.id,action="user.self_register",details=f"{email} | {body.role}")); db.commit(); db.refresh(user)
    return {"token":create_token({"sub":str(user.id),"role":user.role}),"user":user_payload(user)}

@app.post("/api/password/forgot")
def forgot_password(body:schemas.ForgotPasswordIn,db:Session=Depends(get_db)):
    email=body.email.strip().lower(); user=db.query(models.User).filter(models.User.email==email).first()
    if user:
        db.add(models.AuditLog(user_id=user.id,action="password.reset.request",details=email)); db.commit()
    return {"ok":True,"message":"If the email is registered, a password reset request has been recorded. Please contact your school administrator for a temporary password."}

@app.post("/api/login")
def login(body:schemas.LoginIn,db:Session=Depends(get_db)):
    user=db.query(models.User).filter(models.User.email==body.email.strip().lower()).first()
    if not user or not verify_password(body.password,user.password_hash): raise HTTPException(401,"Invalid email or password")
    if not user.active: raise HTTPException(403,"This account is inactive. Contact your administrator.")
    return {"token":create_token({"sub":str(user.id),"role":user.role}),"user":user_payload(user)}

@app.get("/api/me")
def me(user=Depends(current_user)): return user_payload(user)

@app.post("/api/me/education")
def update_my_education(body:schemas.ProfileEducationIn,db:Session=Depends(get_db),user=Depends(require_roles("student"))):
    validate_education(body.education_level,body.class_level,required=True)
    user.education_level=body.education_level; user.class_level=body.class_level
    db.add(models.AuditLog(user_id=user.id,action="profile.education.update",details=f"{body.education_level} | {body.class_level}")); db.commit()
    return user_payload(user)

@app.get("/api/admin/schools")
def admin_schools(db:Session=Depends(get_db),user=Depends(require_roles("super_admin"))):
    schools=db.query(models.School).order_by(models.School.name.asc()).all()
    return [{"id":s.id,"name":s.name,"region":s.region or "","council":s.council or "","created_at":s.created_at.isoformat() if s.created_at else "",
             "users":db.query(models.User).filter(models.User.school_id==s.id).count()} for s in schools]

@app.post("/api/admin/schools")
def admin_create_school(body:schemas.AdminSchoolIn,db:Session=Depends(get_db),user=Depends(require_roles("super_admin"))):
    name=body.name.strip()
    if db.query(models.School).filter(models.School.name==name).first(): raise HTTPException(409,"School already exists")
    school=models.School(name=name,region=(body.region or "").strip() or None,council=(body.council or "").strip() or None)
    db.add(school); db.flush(); db.add(models.AuditLog(user_id=user.id,action="school.create",details=name)); db.commit(); db.refresh(school)
    return {"id":school.id,"ok":True}

def reset_requested(db,target_id):
    req=db.query(models.AuditLog).filter(models.AuditLog.user_id==target_id,models.AuditLog.action=="password.reset.request").order_by(models.AuditLog.id.desc()).first()
    done=db.query(models.AuditLog).filter(models.AuditLog.user_id==target_id,models.AuditLog.action=="password.reset.completed").order_by(models.AuditLog.id.desc()).first()
    return bool(req and (not done or req.id>done.id))

@app.get("/api/admin/users")
def admin_users(db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    q=db.query(models.User)
    if user.role=="school_admin": q=q.filter(models.User.school_id==user.school_id)
    users=q.order_by(models.User.id.desc()).limit(500).all(); school_map={s.id:s.name for s in db.query(models.School).all()}
    return [{"id":u.id,"name":u.full_name,"email":u.email,"role":u.role,"active":bool(u.active),"school_id":u.school_id,"school_name":school_map.get(u.school_id,""),
             "education_level":u.education_level or "","class_level":u.class_level or "","reset_requested":reset_requested(db,u.id),"created_at":u.created_at.isoformat() if u.created_at else ""} for u in users]

@app.post("/api/admin/users")
def admin_create_user(body:schemas.AdminUserIn,db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    email=body.email.strip().lower()
    if db.query(models.User).filter(models.User.email==email).first(): raise HTTPException(409,"Email already registered")
    if user.role=="school_admin":
        if body.role not in {"teacher","student","parent"}: raise HTTPException(403,"School administrators can create Teacher, Student and Parent accounts only")
        school_id=user.school_id
    else:
        if body.role not in {"teacher","student","parent","school_admin"}: raise HTTPException(403,"Invalid role")
        school_id=body.school_id
    if not school_id: raise HTTPException(400,"A school is required")
    if not db.query(models.School).filter(models.School.id==school_id).first(): raise HTTPException(404,"School not found")
    if body.role=="student": validate_education(body.education_level,body.class_level,required=True)
    new_user=models.User(full_name=body.full_name.strip(),email=email,password_hash=hash_password(body.password),role=body.role,school_id=school_id,
                         education_level=body.education_level,class_level=body.class_level,active=True)
    db.add(new_user); db.flush(); db.add(models.AuditLog(user_id=user.id,action="user.create",details=f"{email} | {body.role} | school={school_id}")); db.commit(); db.refresh(new_user)
    return {"id":new_user.id,"ok":True}

@app.post("/api/admin/users/{target_user_id}/password")
def admin_reset_password(target_user_id:int,body:schemas.AdminPasswordResetIn,db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    target=db.query(models.User).filter(models.User.id==target_user_id).first()
    if not target: raise HTTPException(404,"User not found")
    if target.role=="super_admin": raise HTTPException(403,"Super Admin password cannot be reset here")
    if user.role=="school_admin" and (target.school_id!=user.school_id or target.role not in {"teacher","student","parent"}): raise HTTPException(403,"You cannot reset this account")
    target.password_hash=hash_password(body.password); target.active=True
    db.add(models.AuditLog(user_id=target.id,action="password.reset.completed",details=f"reset_by={user.id}")); db.commit(); return {"ok":True}

@app.post("/api/admin/users/{target_user_id}/status")
def admin_user_status(target_user_id:int,body:schemas.UserStatusIn,db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    target=db.query(models.User).filter(models.User.id==target_user_id).first()
    if not target: raise HTTPException(404,"User not found")
    if target.id==user.id: raise HTTPException(400,"You cannot deactivate your own account")
    if target.role=="super_admin": raise HTTPException(403,"Super Admin status cannot be changed here")
    if user.role=="school_admin" and (target.school_id!=user.school_id or target.role=="school_admin"): raise HTTPException(403,"You cannot change this account")
    target.active=body.active; db.add(models.AuditLog(user_id=user.id,action="user.status",details=f"user={target.id} active={body.active}")); db.commit()
    return {"ok":True,"active":target.active}

@app.get("/api/admin/feedback")
def admin_feedback(db:Session=Depends(get_db),user=Depends(require_roles("super_admin"))):
    rows=db.query(models.Feedback).order_by(models.Feedback.id.desc()).limit(200).all(); user_map={u.id:u for u in db.query(models.User).all()}; school_map={s.id:s.name for s in db.query(models.School).all()}; out=[]
    for x in rows:
        owner=user_map.get(x.user_id); out.append({"id":x.id,"module":x.module,"rating":x.rating,"comment":x.comment,"user":owner.full_name if owner else "","role":owner.role if owner else "","school":school_map.get(owner.school_id,"") if owner else "","created_at":x.created_at.isoformat() if x.created_at else ""})
    return out

def resource_payload(x):
    return {"id":x.id,"type":x.resource_type,"material_type":x.material_type or x.resource_type,"education_level":x.education_level or "","class_level":x.class_level or "",
            "subject_name":x.subject_name or "","visibility":x.visibility or "school","title":x.title,"content":x.content,"language":x.language,"created_at":x.created_at.isoformat() if x.created_at else ""}

@app.get("/api/resources")
def list_resources(db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(models.Resource)
    if user.role=="school_admin": q=q.filter(models.Resource.school_id==user.school_id)
    elif user.role!="super_admin": q=q.filter(models.Resource.owner_id==user.id)
    return [resource_payload(x) for x in q.order_by(models.Resource.id.desc()).limit(200).all()]

@app.get("/api/learn/resources")
def learn_resources(education_level:str=Query(default=""),class_level:str=Query(default=""),subject:str=Query(default=""),material_type:str=Query(default=""),db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(models.Resource).filter(or_(models.Resource.visibility=="public",(models.Resource.visibility=="school") & (models.Resource.school_id==user.school_id),models.Resource.owner_id==user.id))
    if education_level: q=q.filter(models.Resource.education_level==education_level)
    if class_level: q=q.filter(models.Resource.class_level==class_level)
    if subject: q=q.filter(models.Resource.subject_name==subject)
    if material_type: q=q.filter(models.Resource.material_type==material_type)
    return [resource_payload(x) for x in q.order_by(models.Resource.id.desc()).limit(200).all()]

@app.get("/api/learn/subjects")
def learn_subjects(education_level:str=Query(default=""),class_level:str=Query(default=""),db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(models.Resource.subject_name).filter(models.Resource.subject_name.isnot(None)).filter(or_(models.Resource.visibility=="public",(models.Resource.visibility=="school") & (models.Resource.school_id==user.school_id),models.Resource.owner_id==user.id))
    if education_level: q=q.filter(models.Resource.education_level==education_level)
    if class_level: q=q.filter(models.Resource.class_level==class_level)
    return sorted({x[0] for x in q.all() if x[0]})

@app.post("/api/resources")
def save_resource(body:schemas.ResourceIn,db:Session=Depends(get_db),user=Depends(current_user)):
    if body.education_level or body.class_level: validate_education(body.education_level,body.class_level)
    visibility=body.visibility if body.visibility in {"private","school","public"} else "school"
    if user.role=="student": visibility="private"
    r=models.Resource(owner_id=user.id,school_id=user.school_id,resource_type=body.resource_type,material_type=body.material_type or body.resource_type,
                      education_level=body.education_level,class_level=body.class_level,subject_name=(body.subject_name or "").strip() or None,visibility=visibility,
                      title=body.title,content=body.content,language=body.language)
    db.add(r); db.add(models.AuditLog(user_id=user.id,action="resource.create",details=body.title)); db.commit(); db.refresh(r); return {"id":r.id,"ok":True}

@app.post("/api/interventions")
def save_intervention(body:schemas.InterventionIn,db:Session=Depends(get_db),user=Depends(require_roles("teacher","school_admin","super_admin"))):
    x=models.Intervention(owner_id=user.id,learner_or_group=body.learner_or_group,topic=body.topic,evidence=body.evidence,intervention_type=body.intervention_type,plan=body.plan); db.add(x); db.commit(); db.refresh(x); return {"id":x.id,"ok":True}

@app.get("/api/interventions")
def list_interventions(db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(models.Intervention)
    if user.role not in {"school_admin","super_admin"}: q=q.filter(models.Intervention.owner_id==user.id)
    elif user.role=="school_admin":
        ids=[x.id for x in db.query(models.User).filter(models.User.school_id==user.school_id).all()]; q=q.filter(models.Intervention.owner_id.in_(ids or [-1]))
    return [{"id":x.id,"learner_or_group":x.learner_or_group,"topic":x.topic,"type":x.intervention_type,"status":x.status} for x in q.order_by(models.Intervention.id.desc()).limit(200).all()]

@app.post("/api/feedback")
def feedback(body:schemas.FeedbackIn,db:Session=Depends(get_db),user=Depends(current_user)):
    db.add(models.Feedback(user_id=user.id,module=body.module,rating=body.rating,comment=body.comment)); db.commit(); return {"ok":True}

@app.get("/api/curriculum/sources")
def curriculum_sources(user=Depends(current_user)):
    import json
    p=Path(__file__).resolve().parent.parent/"data"/"official_curriculum_sources.json"; return json.loads(p.read_text(encoding="utf-8"))

@app.post("/api/curriculum/versions")
def curriculum_version(body:schemas.CurriculumVersionIn,db:Session=Depends(get_db),user=Depends(require_roles("super_admin"))):
    x=models.CurriculumVersion(name=body.name,version_year=body.version_year,status=body.status,source_reference=body.source_reference,notes=body.notes,created_by=user.id); db.add(x); db.commit(); db.refresh(x); return {"id":x.id,"ok":True}

@app.get("/api/curriculum/versions")
def curriculum_versions(db:Session=Depends(get_db),user=Depends(current_user)):
    xs=db.query(models.CurriculumVersion).order_by(models.CurriculumVersion.id.desc()).all(); return [{"id":x.id,"name":x.name,"year":x.version_year,"status":x.status,"source_reference":x.source_reference} for x in xs]

@app.post("/api/generate")
async def generate_content(body:schemas.GenerateIn,user=Depends(current_user)):
    out=await generate(body.module,body.prompt); return {"module":body.module,"content":out,"review_required":True}

@app.get("/api/admin/metrics")
def metrics(db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    rq=db.query(models.Resource); uq=db.query(models.User); iq=db.query(models.Intervention); fq=db.query(models.Feedback); schools=None
    if user.role=="school_admin":
        rq=rq.filter(models.Resource.school_id==user.school_id); uq=uq.filter(models.User.school_id==user.school_id); ids=[x.id for x in db.query(models.User).filter(models.User.school_id==user.school_id).all()]; iq=iq.filter(models.Intervention.owner_id.in_(ids or [-1])); fq=fq.filter(models.Feedback.user_id.in_(ids or [-1]))
    else: schools=db.query(models.School).count()
    result={"users":uq.count(),"resources":rq.count(),"interventions":iq.count(),"feedback":fq.count()}
    if schools is not None: result["schools"]=schools
    return result

app.mount("/",StaticFiles(directory=str(STATIC),html=True),name="static")
