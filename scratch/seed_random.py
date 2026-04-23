import json
import random
from datetime import date, timedelta
from sqlmodel import Session, select
from models import User, Project, Review, engine

# Sample remarks to keep it realistic
GOOD_REMARKS = [
    "Great collaboration and timely delivery.",
    "Showed strong ownership of the feature.",
    "Very helpful during the QA phase.",
    "Code quality was exceptional.",
    "Managed dependencies very well.",
    "Always available for technical guidance.",
    "Handled change requests smoothly.",
    "Exceptional performance in this sprint.",
    "Communicated issues clearly and early."
]

AVG_REMARKS = [
    "Good work, but can improve on communication.",
    "Needs to focus more on unit testing.",
    "Met the deadlines but code needs refactoring.",
    "Average contribution to the project.",
    "Did the task well, but accountability was missing at times.",
    "Requires more guidance on complex tasks."
]

def seed_random_data():
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        projects = session.exec(select(Project)).all()
        
        if not projects:
            print("No projects found. Creating a sample project first...")
            p = Project(
                name="System Overhaul 2024",
                sprint="Q3 - Sprint 1",
                design_date=date.today() - timedelta(days=30),
                dev_start=date.today() - timedelta(days=25),
                qa_start=date.today() - timedelta(days=10),
                qa_end=date.today() - timedelta(days=2),
                release_date=date.today() + timedelta(days=5),
                dev_team=json.dumps(["Yash Mangal", "Abhishek", "Ashish Karn", "Jatin Nehlani"]),
                qa_team=json.dumps(["Anirudh Sharma", "Prateek Pandey"]),
                product_owner="Abhinav Kapoor",
                dev_poc="Yash Mangal",
                qa_poc="Anirudh Sharma",
                tech_lead_name="Niteesh Mahato"
            )
            session.add(p)
            session.commit()
            session.refresh(p)
            projects = [p]

        print(f"Seeding random reviews for {len(users)} users across {len(projects)} projects...")
        
        review_count = 0
        for project in projects:
            devs = json.loads(project.dev_team)
            qas = json.loads(project.qa_team)
            product = project.product_owner
            tech_lead = getattr(project, "tech_lead_name", "Niteesh Mahato")
            
            all_members = []
            for d in devs: all_members.append((d, "Dev"))
            for q in qas: all_members.append((q, "QA"))
            if product: all_members.append((product, "Product"))
            if tech_lead: all_members.append((tech_lead, "Tech Lead"))
            
            # For each project, let's have 3-5 users submit reviews
            reviewers = random.sample(users, min(len(users), 5))
            
            for reviewer in reviewers:
                # Reviewer role in this context
                reviewer_role = "Admin"
                for m_name, m_role in all_members:
                    if m_name == reviewer.name:
                        reviewer_role = m_role
                        break
                
                # Review 3-5 people in this project
                to_rate = random.sample(all_members, min(len(all_members), 6))
                
                for rated_name, rated_role in to_rate:
                    if rated_name == reviewer.name: continue # Don't rate self
                    
                    # Already reviewed?
                    existing = session.exec(select(Review).where(
                        Review.project_id == project.id,
                        Review.reviewer_name == reviewer.name,
                        Review.rated_person == rated_name
                    )).first()
                    if existing: continue
                    
                    score_range = [3, 4, 5] if random.random() > 0.2 else [1, 2, 3] # Most are good
                    remarks = random.choice(GOOD_REMARKS if max(score_range) > 3 else AVG_REMARKS)
                    
                    review = Review(
                        project_id=project.id,
                        reviewer_name=reviewer.name,
                        reviewer_role=reviewer_role,
                        rated_person=rated_name,
                        rated_role=rated_role,
                        score_1=random.choice(score_range),
                        score_2=random.choice(score_range),
                        score_3=random.choice(score_range),
                        score_poc=random.choice([4, 5]) if (rated_name == project.dev_poc or rated_name == project.qa_poc) else None,
                        remarks=remarks,
                        improvement_feedback="Keep up the good work." if random.random() > 0.5 else "Better communication needed.",
                        delay_reason="None" if random.random() > 0.8 else ""
                    )
                    session.add(review)
                    review_count += 1
        
        session.commit()
        print(f"Generated {review_count} random review entries successfully!")

if __name__ == "__main__":
    seed_random_data()
