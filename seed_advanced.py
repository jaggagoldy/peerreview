from sqlmodel import Session, select
from models import Project, Review, User, engine
from datetime import date, timedelta
import json
import hashlib

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def seed():
    with Session(engine) as session:
        # 1. Create a project
        p1 = Project(
            name="Project Alpha",
            sprint="Sprint 1",
            design_date=date(2023, 1, 1),
            dev_start=date(2023, 1, 5),
            qa_start=date(2023, 1, 15),
            qa_end=date(2023, 1, 20),
            release_date=date(2023, 1, 25),
            dev_team=json.dumps(["Yash Mangal", "Abhishek"]),
            qa_team=json.dumps(["Anirudh Sharma"]),
            product_owner="Abhinav Kapoor",
            dev_poc="Yash Mangal",
            qa_poc="Anirudh Sharma"
        )
        p2 = Project(
            name="Project Beta",
            sprint="Sprint 2",
            design_date=date(2023, 2, 1),
            dev_start=date(2023, 2, 5),
            qa_start=date(2023, 2, 15),
            qa_end=date(2023, 2, 20),
            release_date=date(2023, 2, 25),
            dev_team=json.dumps(["Yash Mangal", "Ashish Karn"]),
            qa_team=json.dumps(["Prateek Pandey"]),
            product_owner="Abhinav Kapoor",
            dev_poc="Yash Mangal",
            qa_poc="Prateek Pandey"
        )
        session.add(p1)
        session.add(p2)
        session.commit()
        session.refresh(p1)
        session.refresh(p2)

        # 2. Add reviews for Yash Mangal in both projects to show trend
        r1 = Review(
            project_id=p1.id,
            reviewer_name="Abhinav Kapoor", reviewer_role="Product",
            rated_person="Yash Mangal", rated_role="Dev",
            score_1=3, score_2=3, score_3=3,
            score_poc=3, # He was POC
            remarks="Began well, scope for improvement", delay_reason="None"
        )
        r2 = Review(
            project_id=p2.id,
            reviewer_name="Abhinav Kapoor", reviewer_role="Product",
            rated_person="Yash Mangal", rated_role="Dev",
            score_1=5, score_2=5, score_3=5,
            score_poc=5, # He was POC
            remarks="Outstanding progress!", delay_reason="None"
        )
        
        # Add a review for Anirudh
        r3 = Review(
            project_id=p1.id,
            reviewer_name="Yash Mangal", reviewer_role="Dev",
            rated_person="Anirudh Sharma", rated_role="QA",
            score_1=4, score_2=4, score_3=4,
            remarks="Good QA support", delay_reason="None"
        )

        session.add(r1)
        session.add(r2)
        session.add(r3)
        session.commit()
        print("Test data seeded successfully!")

if __name__ == "__main__":
    seed()
