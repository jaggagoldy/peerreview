import random
import json
from datetime import date, timedelta
from sqlmodel import Session, select
from models import engine, Project, Review, User, create_db_and_tables

# Team lists from main.py
DEV_TEAM_LIST = ["Yash Mangal", "Abhishek", "Ashish Karn", "Jatin Nehlani", "Nikhil Thakur", "Rushil", "Aditya", "Atul", "Hridyesh", "Manik Gandhi", "Niteesh Mahato"]
QA_TEAM_LIST = ["Anirudh Sharma", "Prateek Pandey", "Shaik Ameer Basha"]
PRODUCT_LIST = ["Abhinav Kapoor", "Prateek Sharma"]
# Include Management in the pool for assignments, even if they won't be rated
MGMT_LIST = ["Himanshu Gupta", "Hridayesh Gupta", "Goldy Jagga"]

TEAMS = ["Growth", "Retention", "Payments", "CRM", "Integration", "Platform", "UI/UX", "API", "Mobile", "Security"]
FEATURES = ["Module", "Service", "Workflow", "Engine", "Dashboard", "Connector", "Automation"]

def generate_random_project(i):
    team = random.choice(TEAMS)
    feature = random.choice(FEATURES)
    name = f"{team} {feature} {i+1}"
    sprint = f"Sprint {random.randint(10, 50)}"
    
    # Dates
    start_offset = random.randint(-100, 0)
    release_date = date.today() + timedelta(days=start_offset + random.randint(30, 90))
    
    # Assign teams - sometimes include management for testing exclusion
    pool_devs = DEV_TEAM_LIST + random.sample(MGMT_LIST, random.randint(0, 1))
    devs = random.sample(pool_devs, random.randint(2, 5))
    qas = random.sample(QA_TEAM_LIST, random.randint(1, 2))
    product = random.choice(PRODUCT_LIST + MGMT_LIST)
    tech_lead = random.choice(["Niteesh Mahato", "Goldy Jagga", "Himanshu Gupta"])
    
    return Project(
        name=name,
        sprint=sprint,
        design_date=release_date - timedelta(days=60),
        dev_start=release_date - timedelta(days=45),
        qa_start=release_date - timedelta(days=20),
        qa_end=release_date - timedelta(days=5),
        release_date=release_date,
        dev_team=json.dumps(devs),
        qa_team=json.dumps(qas),
        product_owner=product,
        dev_poc=random.choice(devs),
        qa_poc=random.choice(qas),
        tech_lead_name=tech_lead
    )

def seed_data():
    create_db_and_tables()
    with Session(engine) as session:
        # Get user roles map
        users = session.exec(select(User)).all()
        user_roles = {u.name: u.role for u in users}
        EXCLUDED = ["CEO", "CTO", "Scrum Master"]

        print("Seeding 40 projects with higher/varied ratings...")
        for i in range(40):
            project = generate_random_project(i)
            session.add(project)
        session.commit()
        
        projects = session.exec(select(Project)).all()
        for p in projects[-40:]:
            devs = json.loads(p.dev_team)
            qas = json.loads(p.qa_team)
            members = [(d, "Dev") for d in devs] + [(q, "QA") for q in qas] + [(p.product_owner, "Product"), (p.tech_lead_name, "Tech Lead")]
            
            # Reviewers can be anyone
            reviewers = random.sample(members, min(len(members), random.randint(3, 5)))
            
            for reviewer_name, reviewer_role in reviewers:
                # Rate everyone else in the project EXCEPT excluded roles
                targets = [m for m in members if m[0] != reviewer_name and user_roles.get(m[0]) not in EXCLUDED]
                for rated_name, rated_role in targets:
                    # Higher scores (4-5) for "live rating little bit more"
                    score1 = random.randint(4, 5) if random.random() > 0.3 else 3
                    score2 = random.randint(4, 5) if random.random() > 0.3 else 3
                    score3 = random.randint(4, 5) if random.random() > 0.3 else 3
                    
                    review = Review(
                        project_id=p.id,
                        reviewer_name=reviewer_name,
                        reviewer_role=reviewer_role,
                        rated_person=rated_name,
                        rated_role=rated_role,
                        score_1=score1,
                        score_2=score2,
                        score_3=score3,
                        score_poc=random.randint(4, 5) if rated_name in [p.dev_poc, p.qa_poc] else None,
                        score_tech_lead=random.randint(4, 5) if rated_role == "Tech Lead" else None,
                        remarks=random.choice(["Excellent delivery.", "High quality output.", "Great collaboration.", "Very reliable.", "Strong technical skills."]),
                        improvement_feedback="Keep performing at this level.",
                        delay_reason="None"
                    )
                    session.add(review)
        session.commit()
        print("Data seeding complete.")

if __name__ == "__main__":
    seed_data()
