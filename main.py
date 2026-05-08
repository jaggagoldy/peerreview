from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import Session, select, func
from models import Project, Review, User, DeletedProject, Notification, ProjectEditHistory, engine, create_db_and_tables
from datetime import date
import hashlib
import json
import shutil
import os
import threading
import time
from typing import List, Optional

app = FastAPI(title="360° Project Review System")
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.filters["from_json"] = json.loads

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# --- EMAIL SERVICE (SendGrid HTTP API - Works on Render) ---
SENDGRID_API_KEY_ENV = "SENDGRID_API_KEY"
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "goldy.jagga@quickreply.ai").strip()  # Must be verified in SendGrid

def get_sendgrid_api_key() -> str:
    return os.getenv(SENDGRID_API_KEY_ENV, "").strip()

def send_review_notification_email_sync(
    to_email: str,
    user_name: str,
    project_name: str,
    project_sprint: str,
    review_rows: List[dict],
):
    """Sends review notification via SendGrid HTTP API (works on Render)."""
    print(f"[EMAIL] Attempting to send to {to_email} for project {project_name}")
    api_key = get_sendgrid_api_key()
    
    if not api_key:
        print(f"[EMAIL] FAILED: {SENDGRID_API_KEY_ENV} is not visible to the running app process.")
        return
    print(f"[EMAIL] SendGrid key loaded from {SENDGRID_API_KEY_ENV} (length={len(api_key)}, prefix={api_key[:3]}...)")
    
    if not review_rows:
        print("[EMAIL] FAILED: No reviews to include in email. Skipping.")
        return

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, ReplyTo

    cc_emails = ["hridayesh.gupta@quickreply.ai", "goldy.jagga@quickreply.ai"]
    # Avoid CC-ing the reviewer themselves
    cc_emails = [e for e in cc_emails if e != to_email]
    subject = f"Performance Review Submitted: {project_name} ({project_sprint})"

    breakdown_text = ""
    for r in review_rows:
        breakdown_text += f"\n---\nResource: {r['rated_person']} ({r['rated_role']})\nRating: {r['score_1']}/5\nRemarks: {r['remarks'] or 'N/A'}\n"

    email_body = f"""Hello {user_name},

You have successfully submitted performance reviews for '{project_name}'.
{breakdown_text}
Improvement Feedback: {review_rows[0]['improvement_feedback'] or 'N/A'}
Delay Notes: {review_rows[0]['delay_reason'] or 'N/A'}

This is an automated notification from the 360 Peer Review System.
"""
    message = Mail(
        from_email=Email(FROM_EMAIL, "360 Peer Review System"),
        to_emails=to_email,
        subject=subject,
        plain_text_content=email_body
    )
    message.reply_to = ReplyTo(FROM_EMAIL)
    for cc in cc_emails:
        message.add_cc(cc)

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"[EMAIL] SUCCESS! Sent to {to_email}. Status: {response.status_code}")
    except Exception as e:
        status_code = getattr(e, "status_code", None)
        body = getattr(e, "body", "")
        print(f"[EMAIL] SendGrid Error: status={status_code} body={body} error={e}")

def send_review_notification_email(user: User, project: Project, reviews: List[Review], background_tasks: BackgroundTasks):
    """Triggers email sending in the background."""
    review_rows = [
        {
            "rated_person": r.rated_person,
            "rated_role": r.rated_role,
            "score_1": r.score_1,
            "remarks": r.remarks,
            "improvement_feedback": r.improvement_feedback,
            "delay_reason": r.delay_reason,
        }
        for r in reviews
    ]
    background_tasks.add_task(
        send_review_notification_email_sync,
        user.email,
        user.name,
        project.name,
        project.sprint,
        review_rows,
    )

# Master Data
DEV_TEAM_LIST = ["Yash Mangal", "Ashish Karn", "Jatin Nehlani", "Nikhil Thakur", "Rushil Shah", "Aditya Singh", "Atul Singh", "Hari Sachdeva", "Hridyesh Sharma", "Manik Gandhi", "Niteesh Mahato"]
QA_TEAM_LIST = ["Anirudh Sharma", "Prateek Pandey", "Shaik Ameer Basha"]
PRODUCT_LIST = ["Abhinav Kapoor", "Himanshu Gupta", "Hridayesh Gupta"] # Removed Prateek Sharma, added Himanshu & Hridayesh
TECH_LEAD_LIST = ["Niteesh Mahato", "Hridayesh Gupta"]

MEMBER_NAME_ALIASES = {
    "Rushil": "Rushil Shah",
    "Aditya": "Aditya Singh",
    "Atul": "Atul Singh",
    "Hridyesh": "Hridyesh Sharma",
}

USER_EMAILS = [
    {"email": "himanshu.gupta@quickreply.ai", "name": "Himanshu Gupta", "role": "CEO", "admin": True},
    {"email": "hridayesh.gupta@quickreply.ai", "name": "Hridayesh Gupta", "role": "CTO", "admin": True},
    {"email": "goldy.jagga@quickreply.ai", "name": "Goldy Jagga", "role": "Scrum Master", "admin": True},
    {"email": "niteesh.mahato@quickreply.ai", "name": "Niteesh Mahato", "role": "Dev", "admin": False},
    {"email": "prateek.pandey@quickreply.ai", "name": "Prateek Pandey", "role": "QA", "admin": False},
    {"email": "hridyesh.sharma@quickreply.ai", "name": "Hridyesh Sharma", "role": "Dev", "admin": False},
    {"email": "abhinav.kapoor@quickreply.ai", "name": "Abhinav Kapoor", "role": "Product", "admin": False},
    {"email": "atul.singh@quickreply.ai", "name": "Atul Singh", "role": "Dev", "admin": False},
    {"email": "aditya.singh@quickreply.ai", "name": "Aditya Singh", "role": "Dev", "admin": False},
    {"email": "rushil.shah@quickreply.ai", "name": "Rushil Shah", "role": "Dev", "admin": False},
    {"email": "jatin.nehlani@quickreply.ai", "name": "Jatin Nehlani", "role": "Dev", "admin": False},
    {"email": "ashish.karn@quickreply.ai", "name": "Ashish Karn", "role": "Dev", "admin": False},
    {"email": "anirudh.sharma@quickreply.ai", "name": "Anirudh Sharma", "role": "QA", "admin": False},
    {"email": "hari.sachdeva@quickreply.ai", "name": "Hari Sachdeva", "role": "Dev", "admin": False},
    {"email": "yash.mangal@quickreply.ai", "name": "Yash Mangal", "role": "Dev", "admin": False},
    {"email": "ameer.basha@quickreply.ai", "name": "Shaik Ameer Basha", "role": "QA", "admin": False},
    {"email": "manik.gandhi@quickreply.ai", "name": "Manik Gandhi", "role": "Dev", "admin": False},
    {"email": "nikhil.thakur@quickreply.ai", "name": "Nikhil Thakur", "role": "Dev", "admin": False},
]

ADMIN_EMAILS = ["himanshu.gupta@quickreply.ai", "hridayesh.gupta@quickreply.ai", "goldy.jagga@quickreply.ai"]

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    
    # Manual migration for SQLite: Ensure all columns exist
    with Session(engine) as session:
        try:
            from sqlalchemy import text
            # Add project_size
            try:
                session.execute(text("ALTER TABLE project ADD COLUMN project_size INTEGER DEFAULT 2"))
                session.commit()
            except Exception: session.rollback()
            
            # Add delivery_status
            try:
                session.execute(text("ALTER TABLE project ADD COLUMN delivery_status VARCHAR DEFAULT 'On Time'"))
                session.commit()
            except Exception: session.rollback()
            
            print("✅ Migration: Verified Project table columns.")
        except Exception as e:
            print(f"❌ Migration Error: {e}")
            session.rollback()

    # Seed users
    with Session(engine) as session:
        for u_data in USER_EMAILS:
            existing = session.exec(select(User).where(User.email == u_data["email"])).first()
            
            role = u_data["role"]
            is_admin = u_data["admin"]
            
            # Default tabs
            is_super = u_data["email"] in ADMIN_EMAILS
            if is_super:
                tabs = ["home", "review", "dashboard", "setup", "admin"]
            elif role == "Tech Lead":
                tabs = ["home", "review", "dashboard", "setup"]
            else:
                tabs = ["home", "review", "dashboard"]
            
            perms = {"tabs": tabs, "is_superadmin": is_super}
            
            # Password Logic
            if is_super:
                default_pass = "Quickreply@123"
            else:
                default_pass = "12345678"

            if not existing:
                user = User(
                    email=u_data["email"],
                    name=u_data["name"],
                    role=role,
                    is_admin=is_admin or is_super,
                    password_hash=hash_password(default_pass),
                    permissions=json.dumps(perms)
                )
                session.add(user)
            else:
                # Update existing user info
                existing.role = role
                existing.is_admin = is_admin or is_super
                existing.permissions = json.dumps(perms)
                # Force password update for seeding if needed
                existing.password_hash = hash_password(default_pass)
                session.add(existing)
        
        session.commit()

    # Start nightly backup scheduler in background thread
    backup_thread = threading.Thread(target=nightly_backup_scheduler, daemon=True)
    backup_thread.start()


def nightly_backup_scheduler():
    """Runs in background, creates a DB snapshot every day at 23:00."""
    import datetime
    while True:
        now = datetime.datetime.now()
        # Calculate seconds until next 23:00
        target = now.replace(hour=23, minute=0, second=0, microsecond=0)
        if now >= target:
            target += datetime.timedelta(days=1)
        wait_secs = (target - now).total_seconds()
        time.sleep(wait_secs)
        # Create backup
        try:
            backup_dir = "data/backups"
            os.makedirs(backup_dir, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            src = "data/database.db"
            dst = f"{backup_dir}/database_backup_{stamp}.db"
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"[BACKUP] Snapshot created: {dst}")
        except Exception as e:
            print(f"[BACKUP] Failed: {e}")


def get_session():
    with Session(engine) as session:
        yield session

def get_current_user(request: Request, session: Session = Depends(get_session)):
    user_email = request.session.get("user")
    if not user_email:
        return None
    return session.exec(select(User).where(User.email == user_email)).first()

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})

@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == email)).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid email or password."})
    request.session["user"] = email
    request.session["user_name"] = user.name
    request.session["user_role"] = user.role
    request.session["is_admin"] = user.is_admin
    request.session["permissions"] = json.loads(user.permissions)
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# ---- Profile: Reset own password ----
@app.post("/profile/reset-password")
async def reset_own_password(
    request: Request,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/login")
    if new_password != confirm_password:
        return RedirectResponse(url="/?profile_error=Passwords+do+not+match", status_code=303)
    if len(new_password) < 6:
        return RedirectResponse(url="/?profile_error=Password+must+be+at+least+6+characters", status_code=303)
    current_user.password_hash = hash_password(new_password)
    session.add(current_user)
    session.commit()
    return RedirectResponse(url="/?profile_success=Password+updated+successfully", status_code=303)

def is_real_member(name: Optional[str]) -> bool:
    return bool(name and name.strip() and name.strip().upper() not in {"N/A", "NA", "NONE"})

def normalize_member_name(name: Optional[str]) -> str:
    if not is_real_member(name):
        return ""
    cleaned = name.strip()
    return MEMBER_NAME_ALIASES.get(cleaned, cleaned)

def normalize_member_list(names: Optional[List[str]]) -> List[str]:
    normalized = []
    for name in names or []:
        member_name = normalize_member_name(name)
        if member_name and member_name not in normalized:
            normalized.append(member_name)
    return normalized

def parse_dt(dt_str: Optional[str]):
    if not dt_str:
        return None
    try:
        return date.fromisoformat(dt_str)
    except Exception:
        return None

def get_project_members(p: Project) -> List[str]:
    devs = json.loads(p.dev_team) if p.dev_team else []
    qas = json.loads(p.qa_team) if p.qa_team else []
    optional_members = [p.product_owner, getattr(p, 'tech_lead_name', '')]
    return normalize_member_list(devs + qas + optional_members)

def notify_project_members(session: Session, project: Project, title: str, message: str):
    for member_name in set(get_project_members(project)):
        user = session.exec(select(User).where(User.name == member_name)).first()
        if user:
            session.add(Notification(
                user_id=user.id,
                title=title,
                message=message,
                link=f"/dashboard?project_id={project.id}"
            ))

def get_project_stats(p: Project, all_reviews: List[Review]):
    """
    Helper to calculate membership and live status for a project.
    """
    expected_reviewers = set(get_project_members(p))
    
    submitted_reviewers = set([r.reviewer_name for r in all_reviews if r.project_id == p.id])
    
    pending_count = len(expected_reviewers - submitted_reviewers)
    is_live = pending_count == 0 and len(expected_reviewers) > 0
    
    return {
        "expected_count": len(expected_reviewers),
        "submitted_count": len(submitted_reviewers),
        "pending_count": pending_count,
        "is_live": is_live,
        "expected_names": list(expected_reviewers),
        "submitted_names": list(submitted_reviewers)
    }

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    profile_success: Optional[str] = None,
    profile_error: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")

    all_projects = session.exec(select(Project)).all()
    all_reviews = session.exec(select(Review)).all()

    # Filter projects visible to this user
    if current_user.is_admin:
        user_projects = all_projects
    else:
        user_projects = [
            p for p in all_projects
            if current_user.name in get_project_members(p)
        ]

    # Build project-level status & stats
    project_status = []
    live_project_ids = set()
    live_count = 0
    
    for p in user_projects:
        stats = get_project_stats(p, all_reviews)
        submitted = current_user.name in stats["submitted_names"]
        
        project_status.append({
            "project": p,
            "completed": submitted,
            "stats": stats
        })
        if stats["is_live"]:
            live_project_ids.add(p.id)
            live_count += 1

    pending_count = len(project_status) - live_count

    # ---- Personal Performance Stats (reviews RECEIVED about the user) ----
    # RULES: 
    # 1. Admin sees everything.
    # 2. Regular user sees reviews ONLY from LIVE projects.
    if current_user.is_admin:
        my_reviews_received = [r for r in all_reviews if r.rated_person == current_user.name]
    else:
        my_reviews_received = [
            r for r in all_reviews 
            if r.rated_person == current_user.name and r.project_id in live_project_ids
        ]

    my_role = current_user.role
    overall_avg = 0
    if my_reviews_received:
        overall_avg = round(sum(r.score_1 for r in my_reviews_received) / len(my_reviews_received), 2)

    # ---- Reviews GIVEN by the user (what they rated others) ----
    my_reviews_given = [r for r in all_reviews if r.reviewer_name == current_user.name]
    # Group by project
    given_by_project = {}
    for r in my_reviews_given:
        if r.project_id not in given_by_project:
            p_obj = session.get(Project, r.project_id)
            given_by_project[r.project_id] = {"project_name": p_obj.name if p_obj else "Unknown", "entries": []}
        given_by_project[r.project_id]["entries"].append(r)

    perms = json.loads(current_user.permissions)
    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request,
        "user": current_user,
        "project_status": project_status,
        "live_count": live_count,
        "pending_count": pending_count,
        "my_reviews_received": my_reviews_received,
        "overall_avg": overall_avg,
        "given_by_project": given_by_project,
        "total_received": len(my_reviews_received),
        "total_given": len(my_reviews_given),
        "perms_is_superadmin": perms.get("is_superadmin", False),
        "profile_success": profile_success,
        "profile_error": profile_error,
    })

@app.get("/setup", response_class=HTMLResponse)
async def project_setup(request: Request, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user: return RedirectResponse(url="/login")
    perms = json.loads(current_user.permissions)
    if "setup" not in perms.get("tabs", []):
        return HTMLResponse("Unauthorized", status_code=403)
    
    projects = session.exec(select(Project).order_by(Project.release_date.desc())).all()
    histories = session.exec(select(ProjectEditHistory).order_by(ProjectEditHistory.edited_at.desc())).all()
    histories_by_project = {}
    for entry in histories:
        histories_by_project.setdefault(entry.project_id, []).append(entry)
    return templates.TemplateResponse(request=request, name="setup.html", context={
        "request": request,
        "projects": projects,
        "histories_by_project": histories_by_project,
        "dev_list": DEV_TEAM_LIST,
        "qa_list": QA_TEAM_LIST,
        "product_list": PRODUCT_LIST,
        "tech_lead_list": TECH_LEAD_LIST,
        "perms_is_superadmin": perms.get("is_superadmin", False)
    })

@app.post("/setup")
async def create_project(
    name: str = Form(...),
    sprint: str = Form(...),
    asana_link: Optional[str] = Form(None),
    design_date: Optional[str] = Form(None),
    dev_start: Optional[str] = Form(None),
    qa_start: Optional[str] = Form(None),
    qa_end: Optional[str] = Form(None),
    release_date: str = Form(...),
    dev_team: Optional[List[str]] = Form(None),
    qa_team: Optional[List[str]] = Form(None),
    product: Optional[str] = Form(None),
    dev_poc: Optional[str] = Form(None),
    qa_poc: Optional[str] = Form(None),
    tech_lead_name: Optional[str] = Form(None),
    project_size: int = Form(2),
    delivery_status: str = Form("On Time"),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_admin:
        return HTMLResponse("Unauthorized", status_code=403)
    
    # Robust Team/POC handling
    dev_team = normalize_member_list(dev_team)
    qa_team = normalize_member_list(qa_team)
    product = normalize_member_name(product)
    tech_lead_name = normalize_member_name(tech_lead_name)
    dev_poc = normalize_member_name(dev_poc)
    qa_poc = normalize_member_name(qa_poc)
    
    # Smart POC Logic: If single person in team, they are the POC
    if len(dev_team) == 1: dev_poc = dev_team[0]
    if len(qa_team) == 1: qa_poc = qa_team[0]
    
    if not dev_poc and dev_team: dev_poc = dev_team[0]
    if not dev_poc: dev_poc = "N/A"
    if not qa_poc: qa_poc = "N/A"

    project = Project(
        name=name,
        sprint=sprint,
        asana_link=asana_link,
        design_date=parse_dt(design_date),
        dev_start=parse_dt(dev_start),
        qa_start=parse_dt(qa_start),
        qa_end=parse_dt(qa_end),
        release_date=date.fromisoformat(release_date),
        dev_team=json.dumps(dev_team),
        qa_team=json.dumps(qa_team) if qa_team else "[]",
        product_owner=product,
        dev_poc=dev_poc,
        qa_poc=qa_poc if qa_poc else "N/A",
        tech_lead_name=tech_lead_name,
        project_size=project_size,
        delivery_status=delivery_status
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    notify_project_members(
        session,
        project,
        "New Project Assigned",
        f"You have been assigned to project: {name}"
    )
    session.commit()

    return RedirectResponse(url="/", status_code=303)

@app.post("/admin/projects/update")
async def update_project(
    project_id: int = Form(...),
    name: str = Form(...),
    sprint: str = Form(...),
    asana_link: Optional[str] = Form(None),
    design_date: Optional[str] = Form(None),
    dev_start: Optional[str] = Form(None),
    qa_start: Optional[str] = Form(None),
    qa_end: Optional[str] = Form(None),
    release_date: str = Form(...),
    project_size: int = Form(...),
    delivery_status: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user:
        return RedirectResponse(url="/login")
    perms = json.loads(current_user.permissions)
    if not perms.get("is_superadmin"):
        return HTMLResponse("Unauthorized", status_code=403)

    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    editable_fields = {
        "name": name.strip(),
        "sprint": sprint.strip(),
        "asana_link": asana_link.strip() if asana_link else None,
        "design_date": parse_dt(design_date),
        "dev_start": parse_dt(dev_start),
        "qa_start": parse_dt(qa_start),
        "qa_end": parse_dt(qa_end),
        "release_date": date.fromisoformat(release_date),
        "project_size": project_size,
        "delivery_status": delivery_status,
    }

    labels = {
        "name": "Project Name",
        "sprint": "Sprint",
        "asana_link": "Project Link",
        "design_date": "Design Date",
        "dev_start": "Dev Start",
        "qa_start": "QA Ready",
        "qa_end": "QA End",
        "release_date": "Release Date",
        "project_size": "Project Score",
        "delivery_status": "Delivery Status",
    }
    changes = {}
    for field, new_value in editable_fields.items():
        old_value = getattr(project, field)
        if old_value != new_value:
            changes[field] = {
                "label": labels[field],
                "old": str(old_value) if old_value is not None else "",
                "new": str(new_value) if new_value is not None else "",
            }
            setattr(project, field, new_value)

    if changes:
        session.add(project)
        history = ProjectEditHistory(
            project_id=project.id,
            edited_by=current_user.name,
            changes_json=json.dumps(changes)
        )
        session.add(history)
        changed_labels = ", ".join(change["label"] for change in changes.values())
        notify_project_members(
            session,
            project,
            "Project Updated",
            f"{project.name} was updated by {current_user.name}: {changed_labels}"
        )
        session.commit()

    return RedirectResponse(url="/setup", status_code=303)

@app.get("/review", response_class=HTMLResponse)
async def review_form(request: Request, project_id: Optional[int] = None, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    
    perms = json.loads(current_user.permissions)
    is_super = perms.get("is_superadmin")

    # Only show projects where user is involved (Dev, QA, TL, or Product)
    # STRICT RULE: Even super admins should only see projects they are part of FOR RATING PURPOSE
    all_projects = session.exec(select(Project).order_by(Project.release_date.desc())).all()
    user_projects = []
    
    for p in all_projects:
        team = get_project_members(p)
        if current_user.name in team:
            user_projects.append(p)

    selected_project = None
    if project_id:
        selected_project = session.get(Project, project_id)
        if selected_project:
            team = get_project_members(selected_project)
            if current_user.name not in team:
                return HTMLResponse("Unauthorized: You are not involved in this project and cannot submit reviews for it.", status_code=403)
    
    is_admin = current_user.is_admin

    # Check if review already completed for selected project
    already_reviewed = False
    if project_id:
        existing = session.exec(select(Review).where(
            Review.project_id == project_id, 
            Review.reviewer_name == current_user.name
        )).first()
        already_reviewed = existing is not None

    selected_project = None
    devs = []
    qas = []
    product = ""
    tech_lead_name = ""
    
    if project_id:
        selected_project = session.get(Project, project_id)
        if selected_project:
            devs = normalize_member_list(json.loads(selected_project.dev_team))
            qas = normalize_member_list(json.loads(selected_project.qa_team))
            product = normalize_member_name(selected_project.product_owner)
            tech_lead_name = normalize_member_name(getattr(selected_project, 'tech_lead_name', ''))
            
    is_tl = current_user.role == "Tech Lead" or current_user.is_admin or (selected_project and current_user.name == getattr(selected_project, 'tech_lead_name', ''))
    all_users = session.exec(select(User)).all()
    user_roles = {u.name: u.role for u in all_users}
    
    EXCLUDED_FROM_RATING = ["CEO", "CTO", "Scrum Master"]
    
    all_members = []
    for d in devs:
        if d != current_user.name and user_roles.get(d) not in EXCLUDED_FROM_RATING:
            all_members.append((d, "Dev"))
    for q in qas:
        if q != current_user.name and user_roles.get(q) not in EXCLUDED_FROM_RATING:
            all_members.append((q, "QA"))
    if is_real_member(product) and product != current_user.name and user_roles.get(product) not in EXCLUDED_FROM_RATING:
        all_members.append((product, "Product"))
    
    # Add Tech Lead as a rateable person
    if is_real_member(tech_lead_name) and tech_lead_name != current_user.name and user_roles.get(tech_lead_name) not in EXCLUDED_FROM_RATING:
        all_members.append((tech_lead_name, "Tech Lead"))

    return templates.TemplateResponse(request=request, name="review.html", context={
        "request": request,
        "projects": user_projects,
        "selected_project": selected_project,
        "devs": devs,
        "qas": qas,
        "product": product,
        "tech_lead_name": tech_lead_name,
        "all_members": all_members,
        "already_reviewed": already_reviewed,
        "is_tech_lead": is_tl,
        "user": current_user
    })

@app.post("/review")
async def submit_reviews(
    request: Request,
    background_tasks: BackgroundTasks,
    project_id: int = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")
    
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # SECURITY CHECK: Is user part of this project? (STRICT: Admin status doesn't grant review access)
    devs = normalize_member_list(json.loads(project.dev_team))
    qas = normalize_member_list(json.loads(project.qa_team))
    all_members = get_project_members(project)
    
    if current_user.name not in all_members:
        raise HTTPException(status_code=403, detail="You are not authorized to review this project as you are not a team member.")

    # Prevent Duplicate Submission
    existing = session.exec(select(Review).where(Review.project_id == project_id, Review.reviewer_name == current_user.name)).first()
    if existing:
        return templates.TemplateResponse(request=request, name="review.html", context={
            "request": request,
            "already_reviewed": True,
            "selected_project": project,
            "user": current_user
        })

    form_data = await request.form()
    ratings_raw = {}
    for key, value in form_data.items():
        if key.startswith("rating[") and "]" in key:
            parts = key.split("][")
            name = parts[0].replace("rating[", "").replace("]", "")
            field = parts[1].replace("]", "")
            if name not in ratings_raw:
                ratings_raw[name] = {}
            ratings_raw[name][field] = value

    improvement = form_data.get("improvement_feedback", "")
    submitted_reviews_summary = []

    for person_name, scores in ratings_raw.items():
        # Validate rated person is in project
        role = ""
        project_tech_lead = normalize_member_name(project.tech_lead_name)
        project_product = normalize_member_name(project.product_owner)
        if person_name == project_tech_lead: role = "Tech Lead"
        elif person_name in devs: role = "Dev"
        elif person_name in qas: role = "QA"
        elif person_name == project_product: role = "Product"
        
        if not role: continue
        
        review = Review(
            project_id=project_id,
            reviewer_name=current_user.name,
            reviewer_role=current_user.role,
            rated_person=person_name,
            rated_role=role,
            score_1=int(scores.get("score_1", 3)),
            score_2=0,
            score_3=0,
            score_poc=None,
            score_tech_lead=None,
            remarks=scores.get("remark", ""),
            improvement_feedback=improvement,
            delay_reason=form_data.get("delay_reason", "")
        )
        session.add(review)
        submitted_reviews_summary.append(review)
    
    session.commit()

    # --- EMAIL NOTIFICATION LOGIC ---
    try:
        send_review_notification_email(current_user, project, submitted_reviews_summary, background_tasks)
    except Exception as e:
        print(f"Email failed: {e}")

    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    project_id: Optional[str] = None,
    role: Optional[str] = Query(None),
    user_name: List[str] = Query(default=[]),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")

    is_admin = current_user.is_admin

    # NON-ADMIN: Lock name & role to themselves, no peeking at others
    if not is_admin:
        user_name = [current_user.name]
        role = current_user.role

    # Handle empty string from query params for project_id
    pid = None
    if project_id and project_id.isdigit():
        pid = int(project_id)

    # Base queries
    all_reviews = session.exec(select(Review)).all()
    all_projects = session.exec(select(Project)).all()
    all_users = session.exec(select(User)).all()

    # Calculate live status for all projects
    live_project_ids = set()
    project_metadata = {}
    for p in all_projects:
        p_stats = get_project_stats(p, all_reviews)
        project_metadata[p.id] = p_stats
        if p_stats["is_live"]:
            live_project_ids.add(p.id)

    # For non-admins, only their assigned projects appear in the project dropdown
    if is_admin:
        visible_projects = all_projects
    else:
        visible_projects = [
            p for p in all_projects
            if current_user.name in get_project_members(p)
        ]

    # Filter base reviews: non-admins only see reviews from live projects
    base_reviews = all_reviews
    if not is_admin:
        base_reviews = [r for r in all_reviews if r.project_id in live_project_ids]

    # Apply filters to current view
    filtered_reviews = list(base_reviews)
    if pid:
        filtered_reviews = [r for r in filtered_reviews if r.project_id == pid]
    if role:
        filtered_reviews = [r for r in filtered_reviews if r.rated_role == role]
    if user_name:
        filtered_reviews = [r for r in filtered_reviews if r.rated_person in user_name]

    # Calculations for Leaderboard (on filtered data)
    stats = {}
    team_sums = {"Dev": {"s1": 0, "count": 0},
                 "QA": {"s1": 0, "count": 0},
                 "Product": {"s1": 0, "count": 0},
                 "Tech Lead": {"s1": 0, "count": 0}}

    for r in filtered_reviews:
        if r.rated_person not in stats:
            stats[r.rated_person] = {"s1_total": 0, "count": 0, "role": r.rated_role}

        stats[r.rated_person]["s1_total"] += r.score_1
        # Team aggregations
        if r.rated_role in team_sums:
            team_sums[r.rated_role]["s1"] += r.score_1
            team_sums[r.rated_role]["count"] += 1
            
    # Precompute user role map early for the leaderboard
    user_role_map = {u.name: u.role for u in all_users}
    project_map = {p.id: p for p in all_projects}

    # Group scores by user and project for weighted impact calculation
    user_project_scores = {}
    for r in filtered_reviews:
        user_project_scores.setdefault(r.rated_person, {}).setdefault(r.project_id, []).append(r.score_1)

    leaderboard = []
    for name, projects_data in user_project_scores.items():
        total_impact = 0
        total_s1 = 0
        total_count = 0
        involved_project_ids = set(projects_data.keys())
        
        for p_id, scores in projects_data.items():
            proj = project_map.get(p_id)
            if proj:
                avg_for_proj = sum(scores) / len(scores)
                p_size = getattr(proj, 'project_size', 2)
                if p_size is None: p_size = 2
                total_impact += avg_for_proj * p_size
                total_s1 += sum(scores)
                total_count += len(scores)
        
        person_pocs = [p for p in all_projects if p.dev_poc == name or p.qa_poc == name]
        overall = total_s1 / total_count if total_count > 0 else 0
        current_role = user_role_map.get(name, "Unknown")
        
        leaderboard.append({
            "name": name,
            "role": current_role,
            "overall": round(overall, 2),
            "impact_points": round(total_impact, 1),
            "project_count": len(involved_project_ids),
            "poc_count": len(person_pocs)
        })
    
    # Primary sort by Impact Points, secondary by Overall average
    leaderboard = sorted(leaderboard, key=lambda x: (x["impact_points"], x["overall"]), reverse=True)

    # Team Averages
    team_avgs = {}
    for loop_role, data in team_sums.items():
        if data["count"] > 0:
            team_avgs[loop_role] = {
                "overall": round(data["s1"] / data["count"], 2)
            }

    # Project Specific Info
    selected_project_info = None
    if pid:
        p_obj = session.get(Project, pid)
        if p_obj:
            # Aggregate improvements for this project
            project_feedback = list(set([r.improvement_feedback for r in filtered_reviews if r.improvement_feedback]))
            selected_project_info = {
                "id": p_obj.id,
                "name": p_obj.name,
                "sprint": p_obj.sprint,
                "dev_poc": p_obj.dev_poc,
                "qa_poc": p_obj.qa_poc,
                "tech_lead_name": getattr(p_obj, 'tech_lead_name', '') if is_real_member(getattr(p_obj, 'tech_lead_name', '')) else '',
                "asana_link": p_obj.asana_link,
                "design_date": p_obj.design_date,
                "dev_start": p_obj.dev_start,
                "qa_start": p_obj.qa_start,
                "qa_end": p_obj.qa_end,
                "release_date": p_obj.release_date,
                "feedback_list": project_feedback
            }

    # Detailed User Profile View data — only computed for a single selected user
    user_profile = None
    single_user = user_name[0] if len(user_name) == 1 else None
    if single_user:
        # Non-admins only see reviews for themselves from live projects
        if is_admin:
            user_reviews = [r for r in all_reviews if r.rated_person == single_user]
        else:
            user_reviews = [r for r in all_reviews if r.rated_person == single_user and r.project_id in live_project_ids]
        
        poc_projects = []
        for p in all_projects:
            if p.dev_poc == single_user or p.qa_poc == single_user:
                poc_projects.append(p)

        # Calculate score average for this specific user (single score model)
        u_s1 = 0
        if user_reviews:
            u_s1 = round(sum(r.score_1 for r in user_reviews) / len(user_reviews), 2)

        # Trend data for graph
        project_scores = {}
        for r in user_reviews:
            if r.project_id not in project_scores:
                project_scores[r.project_id] = []
            project_scores[r.project_id].append(r.score_1)

        profile_impact_points = 0
        for p_id, scores in project_scores.items():
            proj = project_map.get(p_id)
            if proj and scores:
                p_size = getattr(proj, 'project_size', 2)
                if p_size is None: p_size = 2
                profile_impact_points += (sum(scores) / len(scores)) * p_size

        trend = []
        for p_id in sorted(project_scores.keys()):
            pj = session.get(Project, p_id)
            if pj:
                avg = sum(project_scores[p_id]) / len(project_scores[p_id])
                p_date = pj.release_date.isoformat() if pj.release_date else date.today().isoformat()
                trend.append({"project": pj.name, "score": round(avg, 2), "date": p_date})

        # Best project
        best_project = None
        if project_scores:
            best_pid = max(project_scores, key=lambda k: sum(project_scores[k]) / len(project_scores[k]))
            best_pj = session.get(Project, best_pid)
            best_score = round(sum(project_scores[best_pid]) / len(project_scores[best_pid]), 2)
            if best_pj:
                best_project = {"name": best_pj.name, "score": best_score, "sprint": best_pj.sprint}

        # Resolve role from user database
        profile_user_obj = next((u for u in all_users if u.name == single_user), None)
        profile_role = profile_user_obj.role if profile_user_obj else (user_reviews[0].rated_role if user_reviews else "Unknown")

        # Get all projects this user is involved in (to show involvement status)
        involved_projects = []
        for p in all_projects:
            is_involved = False
            try:
                if single_user in get_project_members(p):
                    is_involved = True
            except: pass
            
            if is_involved:
                p_stats = project_metadata.get(p.id, {})
                involved_projects.append({
                    "id": p.id,
                    "name": p.name,
                    "sprint": p.sprint,
                    "is_live": p_stats.get("is_live", False),
                    "pending_count": p_stats.get("pending_count", 0),
                    "my_score": round(sum(project_scores[p.id]) / len(project_scores[p.id]), 2) if p.id in project_scores else None
                })

        user_profile = {
            "name": single_user,
            "role": profile_role,
            "total_projects": len(involved_projects),
            "live_projects": len([p for p in involved_projects if p["is_live"]]),
            "poc_count": len(poc_projects),
            "score_avg": u_s1,
            "impact_points": round(profile_impact_points, 1),
            "reviews": user_reviews,
            "trend": trend,
            "involved_projects": involved_projects,
            "all_projects": {p.id: p.name for p in all_projects},
            "best_project": best_project
        }

    avg_tl_score = 0  # Legacy field, no longer used

    # Smart filter maps for JS-driven dropdown auto-sync
    # user_role_map is already defined above

    user_projects_map = {}
    for p in all_projects:
        members = get_project_members(p)
        for m in members:
            user_projects_map.setdefault(m, [])
            if p.id not in user_projects_map[m]:
                user_projects_map[m].append(p.id)

    role_users_map = {}
    for u in all_users:
        role_users_map.setdefault(u.role, [])
        role_users_map[u.role].append(u.name)

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "request": request,
        "leaderboard": leaderboard,
        "team_avgs": team_avgs,
        "projects": visible_projects,
        "all_projects": all_projects,
        "users": all_users,
        "avg_tl_score": avg_tl_score,
        "filters": {"project_id": pid, "role": role, "user_name": user_name},
        "user_profile": user_profile,
        "project_info": selected_project_info,
        "is_admin": is_admin,
        "current_user": current_user,
        "user_role_map": user_role_map,
        "user_projects_map": user_projects_map,
        "role_users_map": role_users_map,
        "project_metadata": project_metadata,
    })


# --- Admin Section (Goldy Only) ---

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(
    request: Request, 
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    session: Session = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")
    perms = json.loads(current_user.permissions)
    if not perms.get("is_superadmin"):
        return HTMLResponse("Unauthorized", status_code=403)
    
    statement = select(User)
    if search:
        statement = statement.where(User.name.ilike(f"%{search}%"))
    if role:
        statement = statement.where(User.role == role)
    
    users = session.exec(statement.order_by(User.name)).all()
    return templates.TemplateResponse(request=request, name="admin_users.html", context={
        "request": request,
        "users": users,
        "search": search or "",
        "role": role or ""
    })

@app.post("/admin/users/update")
async def update_user(
    request: Request,
    user_id: int = Form(...),
    password: Optional[str] = Form(None),
    role: str = Form(...),
    is_admin: bool = Form(False),
    tabs: List[str] = Form([]),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")
    admin_perms = json.loads(current_user.permissions)
    if not admin_perms.get("is_superadmin"):
        return HTMLResponse("Unauthorized", status_code=403)

    user = session.get(User, user_id)
    if user:
        user.role = role
        user.is_admin = is_admin
        if password:
            user.password_hash = hash_password(password)
        
        # Build permissions
        new_perms = {"tabs": tabs}
        # Preserve superadmin flag for Goldy
        if user.email == "goldy.jagga@quickreply.ai":
            new_perms["is_superadmin"] = True
            
        user.permissions = json.dumps(new_perms)
        session.add(user)
        session.commit()
    
    return RedirectResponse(url="/admin/users", status_code=303)

# ---- Superadmin: Reset any user's password ----
@app.post("/admin/users/reset-password")
async def admin_reset_password(
    request: Request,
    user_id: int = Form(...),
    new_password: str = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")
    admin_perms = json.loads(current_user.permissions)
    if not admin_perms.get("is_superadmin"):
        return HTMLResponse("Unauthorized", status_code=403)
    user = session.get(User, user_id)
    if user and new_password:
        user.password_hash = hash_password(new_password)
        session.add(user)
        session.commit()
    return RedirectResponse(url="/admin/users", status_code=303)

# ---- Superadmin: Delete project -> Recycle Bin ----
@app.post("/admin/projects/delete")
async def delete_project(
    request: Request,
    project_id: int = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")
    perms = json.loads(current_user.permissions)
    if not perms.get("is_superadmin"):
        return HTMLResponse("Unauthorized", status_code=403)
    project = session.get(Project, project_id)
    if project:
        # Save to recycle bin
        deleted = DeletedProject(
            project_id=project.id,
            name=project.name,
            deleted_by=current_user.name,
            deleted_at=date.today(),
            data_json=json.dumps({
                "name": project.name, "sprint": project.sprint,
                "dev_team": project.dev_team, "qa_team": project.qa_team,
                "product_owner": project.product_owner, "dev_poc": project.dev_poc,
                "qa_poc": project.qa_poc, "release_date": str(project.release_date)
            })
        )
        session.add(deleted)
        session.delete(project)
        
        # Also delete all associated reviews for this project
        reviews_to_delete = session.exec(select(Review).where(Review.project_id == project.id)).all()
        for r in reviews_to_delete:
            session.delete(r)
            
        session.commit()
    return RedirectResponse(url="/", status_code=303)

# ---- Superadmin: Recycle Bin view ----
@app.get("/admin/recycle-bin", response_class=HTMLResponse)
async def recycle_bin(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")
    perms = json.loads(current_user.permissions)
    if not perms.get("is_superadmin"):
        return HTMLResponse("Unauthorized", status_code=403)
    deleted_projects = session.exec(select(DeletedProject).order_by(DeletedProject.deleted_at.desc())).all()
    return templates.TemplateResponse(request=request, name="recycle_bin.html", context={
        "request": request,
        "deleted_projects": deleted_projects,
        "current_user": current_user
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# --- NOTIFICATION APIs ---

@app.get("/api/notifications")
async def get_notifications(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if not current_user: return {"notifications": [], "unread_count": 0}
    from models import Notification
    notifs = session.exec(select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.id.desc()).limit(20)).all()
    unread_count = session.exec(select(func.count(Notification.id)).where(Notification.user_id == current_user.id, Notification.is_read == False)).one()
    return {
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "link": n.link,
                "is_read": n.is_read,
                "created_at": n.created_at.strftime("%d %b, %Y")
            } for n in notifs
        ],
        "unread_count": unread_count
    }

@app.post("/api/notifications/mark-read/{notif_id}")
async def mark_read(notif_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if not current_user: return {"status": "error"}
    from models import Notification
    notif = session.get(Notification, notif_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        session.add(notif)
        session.commit()
    return {"status": "ok"}

@app.post("/api/notifications/mark-read-all")
async def mark_read_all(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if not current_user: return {"status": "error"}
    from models import Notification
    unread = session.exec(select(Notification).where(Notification.user_id == current_user.id, Notification.is_read == False)).all()
    for n in unread:
        n.is_read = True
        session.add(n)
    session.commit()
    return {"status": "ok"}
