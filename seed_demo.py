from sqlmodel import Session, select
from models import Project, Review, User, engine
from datetime import date, timedelta
import json
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def seed_demo():
    with Session(engine) as session:
        # 1. Create Projects
        projects = [
            Project(
                name="WhatsApp Integration",
                sprint="Q1 - Sprint 2",
                design_date=date(2024, 1, 10),
                dev_start=date(2024, 1, 15),
                qa_start=date(2024, 1, 25),
                qa_end=date(2024, 1, 30),
                release_date=date(2024, 2, 5),
                dev_team=json.dumps(["Yash Mangal", "Abhishek", "Ashish Karn"]),
                qa_team=json.dumps(["Anirudh Sharma", "Prateek Pandey"]),
                product_owner="Abhinav Kapoor",
                dev_poc="Yash Mangal",
                qa_poc="Anirudh Sharma"
            ),
            Project(
                name="Payment Gateway 2.0",
                sprint="Q1 - Sprint 4",
                design_date=date(2024, 2, 10),
                dev_start=date(2024, 2, 15),
                qa_start=date(2024, 2, 28),
                qa_end=date(2024, 3, 5),
                release_date=date(2024, 3, 10),
                dev_team=json.dumps(["Jatin Nehlani", "Nikhil Thakur", "Rushil"]),
                qa_team=json.dumps(["Prateek Pandey", "Shaik Ameer Basha"]),
                product_owner="Prateek Sharma",
                dev_poc="Jatin Nehlani",
                qa_poc="Prateek Pandey"
            ),
            Project(
                name="AI Chatbot Beta",
                sprint="Q2 - Sprint 1",
                design_date=date(2024, 3, 20),
                dev_start=date(2024, 3, 25),
                qa_start=date(2024, 4, 10),
                qa_end=date(2024, 4, 15),
                release_date=date(2024, 4, 20),
                dev_team=json.dumps(["Yash Mangal", "Niteesh Mahato", "Aditya"]),
                qa_team=json.dumps(["Anirudh Sharma"]),
                product_owner="Abhinav Kapoor",
                dev_poc="Yash Mangal",
                qa_poc="Anirudh Sharma"
            )
        ]
        
        for p in projects:
            session.add(p)
        session.commit()
        for p in projects:
            session.refresh(p)

        # 2. Add Reviews
        # Yash Mangal - Showing High Performance & Upward Trend
        p1, p2, p3 = projects
        reviews = [
            # Project 1 reviews for Yash
            Review(
                project_id=p1.id, reviewer_name="Abhinav Kapoor", reviewer_role="Product",
                rated_person="Yash Mangal", rated_role="Dev",
                score_1=4, score_2=4, score_3=3, score_poc=5, score_tech_lead=4,
                remarks="Great accountability and code quality.", improvement_feedback="Optimize build pipeline.", delay_reason="None"
            ),
            Review(
                project_id=p1.id, reviewer_name="Anirudh Sharma", reviewer_role="QA",
                rated_person="Yash Mangal", rated_role="Dev",
                score_1=4, score_2=5, score_3=4, score_poc=4,
                remarks="Highly productive developer.", improvement_feedback="Better unit test coverage.", delay_reason="None"
            ),
            
            # Project 3 reviews for Yash (Better scores to show growth)
            Review(
                project_id=p3.id, reviewer_name="Abhinav Kapoor", reviewer_role="Product",
                rated_person="Yash Mangal", rated_role="Dev",
                score_1=5, score_2=5, score_3=5, score_poc=5, score_tech_lead=5,
                remarks="Exceptional coordination and delivery.", improvement_feedback="None", delay_reason="None"
            ),

            # Anirudh Sharma reviews
            Review(
                project_id=p1.id, reviewer_name="Yash Mangal", reviewer_role="Dev",
                rated_person="Anirudh Sharma", rated_role="QA",
                score_1=5, score_2=4, score_3=5, score_poc=5,
                remarks="Comprehensive test coverage.", improvement_feedback="Automation can be improved.", delay_reason="None"
            ),

            # Jatin Nehlani reviews (Project 2)
            Review(
                project_id=p2.id, reviewer_name="Prateek Sharma", reviewer_role="Product",
                rated_person="Jatin Nehlani", rated_role="Dev",
                score_1=3, score_2=3, score_3=4, score_poc=3, score_tech_lead=3,
                remarks="Average accountability, needs more focus on edge cases.", improvement_feedback="Focus on edge cases.", delay_reason="API Downtime"
            )
        ]

        for r in reviews:
            session.add(r)
        
        session.commit()
        print("Demo data seeded successfully!")

if __name__ == "__main__":
    seed_demo()
