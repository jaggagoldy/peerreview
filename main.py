from fastapi import FastAPI, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import Session, select, func
from models import Project, Review, User, engine, create_db_and_tables
from datetime import date
import hashlib
import json
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

# --- EMAIL SERVICE (Simulated) ---
def send_review_notification_email(user: User, project: Project, reviews: List[Review]):
    """
    Sends a confirmation email to the user and CCs Hridayesh & Goldy.
    Includes a detailed breakdown of the submitted ratings.
    """
    to_email = user.email
    cc_emails = ["hridayesh.gupta@quickreply.ai", "goldy.jagga@quickreply.ai"]
    
    subject = f"Performance Review Submitted: {project.name} ({project.sprint})"
    
    # Constructing the breakdown
    breakdown_text = ""
    for r in reviews:
        breakdown_text += f"""
---
Resource: {r.rated_person} ({r.rated_role})
Scores: M1: {r.score_1} | M2: {r.score_2} | M3: {r.score_3}
{"POC Score: " + str(r.score_poc) if r.score_poc else ""}
{"Tech Lead Score: " + str(r.score_tech_lead) if r.score_tech_lead else ""}
Remarks: {r.remarks if r.remarks else "N/A"}
"""

    email_body = f"""
Hello {user.name},

You have successfully submitted performance reviews for the project '{project.name}'.

Details of your submission:
{breakdown_text}

Project Improvement Feedback:
{reviews[0].improvement_feedback if reviews else "N/A"}

Delay Reason (if any):
{reviews[0].delay_reason if reviews else "N/A"}

This is an automated notification. CC: {', '.join(cc_emails)}
"""
    
    print("="*60)
    print(f"📧 SENDING EMAIL...")
    print(f"Subject: {subject}")
    print(f"To: {to_email}")
    print(f"CC: {', '.join(cc_emails)}")
    print(f"Body:\n{email_body}")
    print("="*60)
    
    # In a real production environment, you would use smtplib here:
    # with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
    #     server.login(Config.SMTP_USER, Config.SMTP_PASS)
    #     server.send_message(msg)

# Master Data
DEV_TEAM_LIST = ["Yash Mangal", "Abhishek", "Ashish Karn", "Jatin Nehlani", "Nikhil Thakur", "Rushil", "Aditya", "Atul", "Hari Sachdeva", "Hridyesh", "Manik Gandhi", "Niteesh Mahato"]
QA_TEAM_LIST = ["Anirudh Sharma", "Prateek Pandey", "Shaik Ameer Basha"]
PRODUCT_LIST = ["Abhinav Kapoor", "Prateek Sharma"]
TECH_LEAD_LIST = ["Niteesh Mahato", "Hridayesh Gupta"]

USER_EMAILS = [
    {"email": "himanshu.gupta@quickreply.ai", "name": "Himanshu Gupta", "role": "CEO", "admin": True},
    {"email": "hridayesh.gupta@quickreply.ai", "name": "Hridayesh Gupta", "role": "CTO", "admin": True},
    {"email": "goldy.jagga@quickreply.ai", "name": "Goldy Jagga", "role": "Scrum Master", "admin": True},
    {"email": "niteesh.mahato@quickreply.ai", "name": "Niteesh Mahato", "role": "Tech Lead", "admin": True},
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
    {"email": "prateek.sharma@quickreply.ai", "name": "Prateek Sharma", "role": "Product", "admin": False},
    {"email": "yash.mangal@quickreply.ai", "name": "Yash Mangal", "role": "Dev", "admin": False},
    {"email": "ameer.basha@quickreply.ai", "name": "Shaik Ameer Basha", "role": "QA", "admin": False},
    {"email": "manik.gandhi@quickreply.ai", "name": "Manik Gandhi", "role": "Dev", "admin": False},
    {"email": "nikhil.thakur@quickreply.ai", "name": "Nikhil Thakur", "role": "Dev", "admin": False},
]

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    # Seed users
    with Session(engine) as session:
        for u_data in USER_EMAILS:
            existing = session.exec(select(User).where(User.email == u_data["email"])).first()
            if not existing:
                perms = {"tabs": ["home", "review", "dashboard"]}
                if u_data["admin"]:
                    perms["tabs"].append("setup")
                
                # Special case for Goldy (Superadmin)
                if u_data["email"] == "goldy.jagga@quickreply.ai":
                    perms["is_superadmin"] = True
                    perms["tabs"].append("admin") # Special admin tab

                user = User(
                    email=u_data["email"],
                    name=u_data["name"],
                    role=u_data["role"],
                    is_admin=u_data["admin"],
                    password_hash=hash_password("quickreply123"),
                    permissions=json.dumps(perms)
                )
                session.add(user)
        session.commit()

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
    request.session["is_admin"] = user.is_admin
    request.session["permissions"] = json.loads(user.permissions)
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if not current_user: return RedirectResponse(url="/login")

    all_projects = session.exec(select(Project)).all()
    all_reviews = session.exec(select(Review)).all()

    # Filter projects visible to this user
    if current_user.is_admin:
        user_projects = all_projects
    else:
        user_projects = [
            p for p in all_projects
            if current_user.name in json.loads(p.dev_team)
            or current_user.name in json.loads(p.qa_team)
            or current_user.name == p.product_owner
            or getattr(p, 'tech_lead_name', '') == current_user.name
        ]

    # Build project-level review status (pending / completed)
    project_status = []
    for p in user_projects:
        submitted = any(r.reviewer_name == current_user.name and r.project_id == p.id for r in all_reviews)
        project_status.append({
            "project": p,
            "completed": submitted
        })

    # ---- Personal Performance Stats (reviews RECEIVED about the user) ----
    my_reviews_received = [r for r in all_reviews if r.rated_person == current_user.name]

    my_role = current_user.role
    s1_avg = s2_avg = s3_avg = overall_avg = 0
    if my_reviews_received:
        s1_avg = round(sum(r.score_1 for r in my_reviews_received) / len(my_reviews_received), 2)
        s2_avg = round(sum(r.score_2 for r in my_reviews_received) / len(my_reviews_received), 2)
        s3_avg = round(sum(r.score_3 for r in my_reviews_received) / len(my_reviews_received), 2)
        overall_avg = round((s1_avg + s2_avg + s3_avg) / 3, 2)

    # Metric labels based on role
    role_metrics = {
        "Dev": ("Accountability", "Productivity", "Coordination"),
        "QA": ("Test Coverage", "Bug Quality", "Communication"),
        "Product": ("Req Clarity", "Support", "Change Handle"),
        "Tech Lead": ("Technical Guidance", "Code Quality Support", "Team Mentorship"),
    }
    m1, m2, m3 = role_metrics.get(my_role, ("Metric 1", "Metric 2", "Metric 3"))

    # ---- Reviews GIVEN by the user (what they rated others) ----
    my_reviews_given = [r for r in all_reviews if r.reviewer_name == current_user.name]
    # Group by project
    given_by_project = {}
    for r in my_reviews_given:
        if r.project_id not in given_by_project:
            p_obj = session.get(Project, r.project_id)
            given_by_project[r.project_id] = {"project_name": p_obj.name if p_obj else "Unknown", "entries": []}
        given_by_project[r.project_id]["entries"].append(r)

    return templates.TemplateResponse(request=request, name="index.html", context={
        "request": request,
        "user": current_user,
        "project_status": project_status,
        "my_reviews_received": my_reviews_received,
        "s1_avg": s1_avg, "s2_avg": s2_avg, "s3_avg": s3_avg, "overall_avg": overall_avg,
        "m1": m1, "m2": m2, "m3": m3,
        "given_by_project": given_by_project,
        "total_received": len(my_reviews_received),
        "total_given": len(my_reviews_given),
    })

@app.get("/setup", response_class=HTMLResponse)
async def project_setup(request: Request, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if not current_user: return RedirectResponse(url="/login")
    perms = json.loads(current_user.permissions)
    if "setup" not in perms.get("tabs", []):
        return HTMLResponse("Unauthorized", status_code=403)
    
    projects = session.exec(select(Project)).all()
    return templates.TemplateResponse(request=request, name="setup.html", context={
        "request": request,
        "projects": projects,
        "dev_list": DEV_TEAM_LIST,
        "qa_list": QA_TEAM_LIST,
        "product_list": PRODUCT_LIST,
        "tech_lead_list": TECH_LEAD_LIST
    })

@app.post("/setup")
async def create_project(
    name: str = Form(...),
    sprint: str = Form(...),
    design_date: date = Form(...),
    dev_start: date = Form(...),
    qa_start: date = Form(...),
    qa_end: date = Form(...),
    release_date: date = Form(...),
    dev_team: List[str] = Form(...),
    qa_team: List[str] = Form(...),
    product: str = Form(...),
    dev_poc: str = Form(...),
    qa_poc: str = Form(...),
    tech_lead_name: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not current_user or not current_user.is_admin:
        return HTMLResponse("Unauthorized", status_code=403)
    project = Project(
        name=name,
        sprint=sprint,
        design_date=design_date,
        dev_start=dev_start,
        qa_start=qa_start,
        qa_end=qa_end,
        release_date=release_date,
        dev_team=json.dumps(dev_team),
        qa_team=json.dumps(qa_team),
        product_owner=product,
        dev_poc=dev_poc,
        qa_poc=qa_poc,
        tech_lead_name=tech_lead_name
    )
    session.add(project)
    session.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/review", response_class=HTMLResponse)
async def review_form(request: Request, project_id: Optional[int] = None, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    
    # Admins/Tech Leads/Super admins see all projects, others see only assigned ones
    perms = json.loads(current_user.permissions)
    is_admin = current_user.is_admin
    
    all_projects = session.exec(select(Project)).all()
    if is_admin:
        user_projects = all_projects
    else:
        user_projects = [
            p for p in all_projects 
            if current_user.name in json.loads(p.dev_team) 
            or current_user.name in json.loads(p.qa_team)
            or current_user.name == p.product_owner
        ]

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
            devs = json.loads(selected_project.dev_team)
            qas = json.loads(selected_project.qa_team)
            product = selected_project.product_owner
            tech_lead_name = getattr(selected_project, 'tech_lead_name', '')

    # Build rateable members: everyone rates the Tech Lead; TL doesn't rate themselves
    is_tl = current_user.role == "Tech Lead" or current_user.is_admin
    all_members = []
    for d in devs:
        if not (is_tl and d == current_user.name):
            all_members.append((d, "Dev"))
    for q in qas:
        if not (is_tl and q == current_user.name):
            all_members.append((q, "QA"))
    if product:
        all_members.append((product, "Product"))
    # Add Tech Lead as a rateable person (skip if reviewer IS the tech lead)
    if tech_lead_name and tech_lead_name != current_user.name:
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
    project_id: int = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if not current_user: return RedirectResponse(url="/login")
    
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # SECURITY CHECK: Is user part of this project?
    devs = json.loads(project.dev_team)
    qas = json.loads(project.qa_team)
    all_members = devs + qas + [project.product_owner, getattr(project, 'tech_lead_name', '')]
    
    if current_user.name not in all_members and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You are not authorized to review this project.")

    # Prevent Duplicate Submission
    existing = session.exec(select(Review).where(Review.project_id == project_id, Review.reviewer_name == current_user.name)).first()
    if existing:
        return templates.TemplateResponse(request=request, name="review.html", context={
            "error": "You have already submitted reviews for this project.",
            "project": project,
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
        if person_name in devs: role = "Dev"
        elif person_name in qas: role = "QA"
        elif person_name == project.product_owner: role = "Product"
        elif person_name == project.tech_lead_name: role = "Tech Lead"
        
        if not role: continue # Security: Don't allow rating random people
        
        review = Review(
            project_id=project_id,
            reviewer_name=current_user.name, # Enforce identity
            reviewer_role=current_user.role,
            rated_person=person_name,
            rated_role=role,
            score_1=int(scores.get("score_1", 0)),
            score_2=int(scores.get("score_2", 0)),
            score_3=int(scores.get("score_3", 0)),
            score_poc=int(scores.get("score_poc")) if scores.get("score_poc") else None,
            score_tech_lead=int(scores.get("score_tech_lead")) if scores.get("score_tech_lead") else None,
            remarks=scores.get("remark", ""),
            improvement_feedback=improvement,
            delay_reason=form_data.get("delay_reason", "")
        )
        session.add(review)
        submitted_reviews_summary.append(review)
    
    session.commit()

    # --- EMAIL NOTIFICATION LOGIC ---
    try:
        send_review_notification_email(current_user, project, submitted_reviews_summary)
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

    # For non-admins, only their assigned projects appear in the project dropdown
    if is_admin:
        visible_projects = all_projects
    else:
        visible_projects = [
            p for p in all_projects
            if current_user.name in json.loads(p.dev_team)
            or current_user.name in json.loads(p.qa_team)
            or current_user.name == p.product_owner
            or getattr(p, 'tech_lead_name', '') == current_user.name
        ]

    # Apply filters to current view
    filtered_reviews = list(all_reviews)
    if pid:
        filtered_reviews = [r for r in filtered_reviews if r.project_id == pid]
    if role:
        filtered_reviews = [r for r in filtered_reviews if r.rated_role == role]
    if user_name:
        filtered_reviews = [r for r in filtered_reviews if r.rated_person in user_name]

    # Calculations for Leaderboard (on filtered data)
    stats = {}
    team_sums = {"Dev": {"s1": 0, "s2": 0, "s3": 0, "count": 0}, 
                 "QA": {"s1": 0, "s2": 0, "s3": 0, "count": 0}, 
                 "Product": {"s1": 0, "s2": 0, "s3": 0, "count": 0},
                 "Tech Lead": {"s1": 0, "s2": 0, "s3": 0, "count": 0}}
                 
    for r in filtered_reviews:
        if r.rated_person not in stats:
            stats[r.rated_person] = {"s1_total": 0, "s2_total": 0, "s3_total": 0, "count": 0, "role": r.rated_role, "poc_count": 0}
        
        stats[r.rated_person]["s1_total"] += r.score_1
        stats[r.rated_person]["s2_total"] += r.score_2
        stats[r.rated_person]["s3_total"] += r.score_3
        stats[r.rated_person]["count"] += 1
        
        # Team aggregations
        if r.rated_role in team_sums:
            team_sums[r.rated_role]["s1"] += r.score_1
            team_sums[r.rated_role]["s2"] += r.score_2
            team_sums[r.rated_role]["s3"] += r.score_3
            team_sums[r.rated_role]["count"] += 1

    leaderboard = []
    for name, data in stats.items():
        # Check overall POC count for this person
        person_pocs = [p for p in all_projects if p.dev_poc == name or p.qa_poc == name]
        
        s1_avg = data["s1_total"] / data["count"]
        s2_avg = data["s2_total"] / data["count"]
        s3_avg = data["s3_total"] / data["count"]
        overall = (s1_avg + s2_avg + s3_avg) / 3
        
        leaderboard.append({
            "name": name,
            "role": data["role"],
            "s1": round(s1_avg, 2),
            "s2": round(s2_avg, 2),
            "s3": round(s3_avg, 2),
            "overall": round(overall, 2),
            "poc_count": len(person_pocs)
        })
    leaderboard = sorted(leaderboard, key=lambda x: x["overall"], reverse=True)

    # Team Averages
    team_avgs = {}
    for loop_role, data in team_sums.items():
        if data["count"] > 0:
            avg_s1 = data["s1"] / data["count"]
            avg_s2 = data["s2"] / data["count"]
            avg_s3 = data["s3"] / data["count"]
            team_avgs[loop_role] = {
                "s1": round(avg_s1, 2),
                "s2": round(avg_s2, 2),
                "s3": round(avg_s3, 2),
                "overall": round((avg_s1 + avg_s2 + avg_s3) / 3, 2)
            }

    # Project Specific Info
    selected_project_info = None
    if pid:
        p_obj = session.get(Project, pid)
        if p_obj:
            # Aggregate improvements for this project
            project_feedback = list(set([r.improvement_feedback for r in filtered_reviews if r.improvement_feedback]))
            selected_project_info = {
                "name": p_obj.name,
                "sprint": p_obj.sprint,
                "dev_poc": p_obj.dev_poc,
                "qa_poc": p_obj.qa_poc,
                "tech_lead_name": getattr(p_obj, 'tech_lead_name', ''),
                "feedback_list": project_feedback
            }

    # Detailed User Profile View data — only computed for a single selected user
    user_profile = None
    single_user = user_name[0] if len(user_name) == 1 else None
    if single_user:
        user_reviews = [r for r in all_reviews if r.rated_person == single_user]
        poc_projects = []
        for p in all_projects:
            if p.dev_poc == single_user or p.qa_poc == single_user:
                poc_projects.append(p)

        # Calculate metric averages for this specific user
        u_s1 = u_s2 = u_s3 = 0
        if user_reviews:
            u_s1 = round(sum(r.score_1 for r in user_reviews) / len(user_reviews), 2)
            u_s2 = round(sum(r.score_2 for r in user_reviews) / len(user_reviews), 2)
            u_s3 = round(sum(r.score_3 for r in user_reviews) / len(user_reviews), 2)

        # Trend data for graph
        project_scores = {}
        for r in user_reviews:
            if r.project_id not in project_scores:
                project_scores[r.project_id] = []
            pj_score = (r.score_1 + r.score_2 + r.score_3) / 3
            if r.score_poc: pj_score = (pj_score + r.score_poc) / 2
            project_scores[r.project_id].append(pj_score)

        trend = []
        for p_id in sorted(project_scores.keys()):
            pj = session.get(Project, p_id)
            if pj:
                avg = sum(project_scores[p_id]) / len(project_scores[p_id])
                trend.append({"project": pj.name, "score": round(avg, 2), "date": pj.release_date.isoformat()})

        # Best project: highest avg score across all their reviews per project
        best_project = None
        if project_scores:
            best_pid = max(project_scores, key=lambda k: sum(project_scores[k]) / len(project_scores[k]))
            best_pj = session.get(Project, best_pid)
            best_score = round(sum(project_scores[best_pid]) / len(project_scores[best_pid]), 2)
            if best_pj:
                best_project = {"name": best_pj.name, "score": best_score, "sprint": best_pj.sprint}

        user_profile = {
            "name": single_user,
            "role": user_reviews[0].rated_role if user_reviews else current_user.role,
            "total_projects": len(set(r.project_id for r in user_reviews)),
            "poc_count": len(poc_projects),
            "s1_avg": u_s1,
            "s2_avg": u_s2,
            "s3_avg": u_s3,
            "reviews": user_reviews,
            "trend": trend,
            "all_projects": {p.id: p.name for p in all_projects},
            "best_project": best_project
        }

    # Tech Lead Support Average (on filtered data)
    tl_scores = [r.score_tech_lead for r in filtered_reviews if r.score_tech_lead is not None]
    avg_tl_score = round(sum(tl_scores) / len(tl_scores), 2) if tl_scores else 0

    # Smart filter maps for JS-driven dropdown auto-sync
    user_role_map = {u.name: u.role for u in all_users}

    user_projects_map = {}
    for p in all_projects:
        members = json.loads(p.dev_team) + json.loads(p.qa_team) + [p.product_owner, getattr(p, 'tech_lead_name', '')]
        for m in members:
            if m:
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
    })


# --- Admin Section (Goldy Only) ---

@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if not current_user: return RedirectResponse(url="/login")
    perms = json.loads(current_user.permissions)
    if not perms.get("is_superadmin"):
        return HTMLResponse("Unauthorized", status_code=403)
    
    users = session.exec(select(User)).all()
    return templates.TemplateResponse(request=request, name="admin_users.html", context={
        "request": request,
        "users": users
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
