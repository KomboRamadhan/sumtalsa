from fastapi import FastAPI,Depends,HTTPException,Header
from fastapi.staticfiles import StaticFiles
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from pathlib import Path
import os

from .database import Base,engine,get_db
from . import models,schemas
from .security import hash_password,verify_password,create_token,decode_token
from .ai_service import generate

Base.metadata.create_all(bind=engine)
app=FastAPI(title="SumTalsa API",version="1.2.0")

if os.getenv("FORCE_HTTPS","false").lower()=="true":
    app.add_middleware(HTTPSRedirectMiddleware)
allowed_hosts=os.getenv("ALLOWED_HOSTS","*").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
STATIC=Path(__file__).resolve().parent.parent/"static"

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
                db.add(school)
                db.flush()
            user=models.User(
                full_name=name,
                email=email,
                password_hash=hash_password(password),
                role="super_admin",
                school_id=school.id,
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


def current_user(authorization:str=Header(default=""),db:Session=Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401,"Missing token")
    token=authorization.split(" ",1)[1]
    try:
        data=decode_token(token)
    except Exception:
        raise HTTPException(401,"Invalid or expired token")
    user=db.query(models.User).filter(
        models.User.id==int(data["sub"]),
        models.User.active==True,
    ).first()
    if not user:
        raise HTTPException(401,"User not found or inactive")
    return user


def require_roles(*roles):
    def dep(user=Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403,"Insufficient permission")
        return user
    return dep


@app.get("/api/health")
def health():
    return {"ok":True,"service":"SumTalsa","version":"1.2.0"}


@app.post("/api/register")
def register(body:schemas.RegisterIn,db:Session=Depends(get_db)):
    if os.getenv("ALLOW_PUBLIC_REGISTRATION","false").lower()!="true":
        raise HTTPException(403,"Public registration is disabled. Ask your school administrator to create your account.")
    if body.role not in {"teacher","student","parent"}:
        raise HTTPException(403,"This role cannot be self-registered")
    email=body.email.strip().lower()
    if db.query(models.User).filter(models.User.email==email).first():
        raise HTTPException(409,"Email already registered")
    school=None
    if body.school_name:
        school=db.query(models.School).filter(models.School.name==body.school_name.strip()).first()
        if not school:
            raise HTTPException(400,"School is not registered. Ask the administrator to add it first.")
    user=models.User(
        full_name=body.full_name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        role=body.role,
        school_id=school.id if school else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "token":create_token({"sub":str(user.id),"role":user.role}),
        "user":{"id":user.id,"name":user.full_name,"email":user.email,"role":user.role},
    }


@app.post("/api/login")
def login(body:schemas.LoginIn,db:Session=Depends(get_db)):
    user=db.query(models.User).filter(models.User.email==body.email.strip().lower()).first()
    if not user or not verify_password(body.password,user.password_hash):
        raise HTTPException(401,"Invalid email or password")
    if not user.active:
        raise HTTPException(403,"This account is inactive. Contact your administrator.")
    return {
        "token":create_token({"sub":str(user.id),"role":user.role}),
        "user":{"id":user.id,"name":user.full_name,"email":user.email,"role":user.role,"school_id":user.school_id},
    }


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {"id":user.id,"name":user.full_name,"email":user.email,"role":user.role,"school_id":user.school_id}


# ---------- Administration ----------
@app.get("/api/admin/schools")
def admin_schools(db:Session=Depends(get_db),user=Depends(require_roles("super_admin"))):
    schools=db.query(models.School).order_by(models.School.name.asc()).all()
    return [{
        "id":s.id,
        "name":s.name,
        "region":s.region or "",
        "council":s.council or "",
        "created_at":s.created_at.isoformat() if s.created_at else "",
        "users":db.query(models.User).filter(models.User.school_id==s.id).count(),
    } for s in schools]


@app.post("/api/admin/schools")
def admin_create_school(body:schemas.AdminSchoolIn,db:Session=Depends(get_db),user=Depends(require_roles("super_admin"))):
    name=body.name.strip()
    if db.query(models.School).filter(models.School.name==name).first():
        raise HTTPException(409,"School already exists")
    school=models.School(name=name,region=(body.region or "").strip() or None,council=(body.council or "").strip() or None)
    db.add(school)
    db.flush()
    db.add(models.AuditLog(user_id=user.id,action="school.create",details=name))
    db.commit()
    db.refresh(school)
    return {"id":school.id,"ok":True}


@app.get("/api/admin/users")
def admin_users(db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    q=db.query(models.User)
    if user.role=="school_admin":
        q=q.filter(models.User.school_id==user.school_id)
    users=q.order_by(models.User.id.desc()).limit(500).all()
    school_map={s.id:s.name for s in db.query(models.School).all()}
    return [{
        "id":u.id,
        "name":u.full_name,
        "email":u.email,
        "role":u.role,
        "active":bool(u.active),
        "school_id":u.school_id,
        "school_name":school_map.get(u.school_id,""),
        "created_at":u.created_at.isoformat() if u.created_at else "",
    } for u in users]


@app.post("/api/admin/users")
def admin_create_user(body:schemas.AdminUserIn,db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    email=body.email.strip().lower()
    if db.query(models.User).filter(models.User.email==email).first():
        raise HTTPException(409,"Email already registered")

    if user.role=="school_admin":
        if body.role not in {"teacher","student","parent"}:
            raise HTTPException(403,"School administrators can create teacher, student and parent accounts only")
        school_id=user.school_id
    else:
        if body.role not in {"teacher","student","parent","school_admin"}:
            raise HTTPException(403,"Invalid role")
        school_id=body.school_id

    if not school_id:
        raise HTTPException(400,"A school is required for this account")
    school=db.query(models.School).filter(models.School.id==school_id).first()
    if not school:
        raise HTTPException(404,"School not found")

    new_user=models.User(
        full_name=body.full_name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        role=body.role,
        school_id=school_id,
        active=True,
    )
    db.add(new_user)
    db.flush()
    db.add(models.AuditLog(user_id=user.id,action="user.create",details=f"{email} | {body.role} | school={school_id}"))
    db.commit()
    db.refresh(new_user)
    return {"id":new_user.id,"ok":True}


@app.post("/api/admin/users/{target_user_id}/status")
def admin_user_status(target_user_id:int,body:schemas.UserStatusIn,db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    target=db.query(models.User).filter(models.User.id==target_user_id).first()
    if not target:
        raise HTTPException(404,"User not found")
    if target.id==user.id:
        raise HTTPException(400,"You cannot deactivate your own account")
    if target.role=="super_admin":
        raise HTTPException(403,"Super Admin status cannot be changed here")
    if user.role=="school_admin":
        if target.school_id!=user.school_id or target.role=="school_admin":
            raise HTTPException(403,"You cannot change this account")
    target.active=body.active
    db.add(models.AuditLog(user_id=user.id,action="user.status",details=f"user={target.id} active={body.active}"))
    db.commit()
    return {"ok":True,"active":target.active}


@app.get("/api/admin/feedback")
def admin_feedback(db:Session=Depends(get_db),user=Depends(require_roles("super_admin"))):
    rows=db.query(models.Feedback).order_by(models.Feedback.id.desc()).limit(200).all()
    user_map={u.id:u for u in db.query(models.User).all()}
    school_map={s.id:s.name for s in db.query(models.School).all()}
    out=[]
    for x in rows:
        owner=user_map.get(x.user_id)
        out.append({
            "id":x.id,
            "module":x.module,
            "rating":x.rating,
            "comment":x.comment,
            "user":owner.full_name if owner else "",
            "role":owner.role if owner else "",
            "school":school_map.get(owner.school_id,"") if owner else "",
            "created_at":x.created_at.isoformat() if x.created_at else "",
        })
    return out


@app.get("/api/resources")
def list_resources(db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(models.Resource)
    if user.role not in {"school_admin","super_admin"}:
        q=q.filter(models.Resource.owner_id==user.id)
    elif user.role=="school_admin":
        q=q.filter(models.Resource.school_id==user.school_id)
    items=q.order_by(models.Resource.id.desc()).limit(200).all()
    return [{"id":x.id,"type":x.resource_type,"title":x.title,"content":x.content,"language":x.language,"created_at":x.created_at.isoformat()} for x in items]


@app.post("/api/resources")
def save_resource(body:schemas.ResourceIn,db:Session=Depends(get_db),user=Depends(current_user)):
    r=models.Resource(owner_id=user.id,school_id=user.school_id,resource_type=body.resource_type,title=body.title,content=body.content,language=body.language)
    db.add(r)
    db.add(models.AuditLog(user_id=user.id,action="resource.create",details=body.title))
    db.commit()
    db.refresh(r)
    return {"id":r.id,"ok":True}


@app.post("/api/interventions")
def save_intervention(body:schemas.InterventionIn,db:Session=Depends(get_db),user=Depends(require_roles("teacher","school_admin","super_admin"))):
    x=models.Intervention(owner_id=user.id,learner_or_group=body.learner_or_group,topic=body.topic,evidence=body.evidence,intervention_type=body.intervention_type,plan=body.plan)
    db.add(x)
    db.commit()
    db.refresh(x)
    return {"id":x.id,"ok":True}


@app.get("/api/interventions")
def list_interventions(db:Session=Depends(get_db),user=Depends(current_user)):
    q=db.query(models.Intervention)
    if user.role not in {"school_admin","super_admin"}:
        q=q.filter(models.Intervention.owner_id==user.id)
    elif user.role=="school_admin":
        school_user_ids=[x.id for x in db.query(models.User).filter(models.User.school_id==user.school_id).all()]
        q=q.filter(models.Intervention.owner_id.in_(school_user_ids or [-1]))
    return [{"id":x.id,"learner_or_group":x.learner_or_group,"topic":x.topic,"type":x.intervention_type,"status":x.status} for x in q.order_by(models.Intervention.id.desc()).limit(200).all()]


@app.post("/api/feedback")
def feedback(body:schemas.FeedbackIn,db:Session=Depends(get_db),user=Depends(current_user)):
    x=models.Feedback(user_id=user.id,module=body.module,rating=body.rating,comment=body.comment)
    db.add(x)
    db.commit()
    return {"ok":True}


@app.get("/api/curriculum/sources")
def curriculum_sources(user=Depends(current_user)):
    import json
    p=Path(__file__).resolve().parent.parent/"data"/"official_curriculum_sources.json"
    return json.loads(p.read_text(encoding="utf-8"))


@app.post("/api/curriculum/versions")
def curriculum_version(body:schemas.CurriculumVersionIn,db:Session=Depends(get_db),user=Depends(require_roles("super_admin"))):
    x=models.CurriculumVersion(name=body.name,version_year=body.version_year,status=body.status,source_reference=body.source_reference,notes=body.notes,created_by=user.id)
    db.add(x)
    db.commit()
    db.refresh(x)
    return {"id":x.id,"ok":True}


@app.get("/api/curriculum/versions")
def curriculum_versions(db:Session=Depends(get_db),user=Depends(current_user)):
    xs=db.query(models.CurriculumVersion).order_by(models.CurriculumVersion.id.desc()).all()
    return [{"id":x.id,"name":x.name,"year":x.version_year,"status":x.status,"source_reference":x.source_reference} for x in xs]


@app.post("/api/generate")
async def generate_content(body:schemas.GenerateIn,user=Depends(current_user)):
    text=await generate(body.module,body.prompt)
    return {"module":body.module,"content":text,"review_required":True}


@app.get("/api/admin/metrics")
def metrics(db:Session=Depends(get_db),user=Depends(require_roles("school_admin","super_admin"))):
    rq=db.query(models.Resource)
    uq=db.query(models.User)
    iq=db.query(models.Intervention)
    fq=db.query(models.Feedback)
    schools=None
    if user.role=="school_admin":
        rq=rq.filter(models.Resource.school_id==user.school_id)
        uq=uq.filter(models.User.school_id==user.school_id)
        school_user_ids=[x.id for x in db.query(models.User).filter(models.User.school_id==user.school_id).all()]
        iq=iq.filter(models.Intervention.owner_id.in_(school_user_ids or [-1]))
        fq=fq.filter(models.Feedback.user_id.in_(school_user_ids or [-1]))
    else:
        schools=db.query(models.School).count()
    result={"users":uq.count(),"resources":rq.count(),"interventions":iq.count(),"feedback":fq.count()}
    if schools is not None:
        result["schools"]=schools
    return result


app.mount("/",StaticFiles(directory=STATIC,html=True),name="static")
