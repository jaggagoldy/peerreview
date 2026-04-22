from sqlmodel import Session, select
from models import Project, Review, engine
from datetime import date
json_team = '["Yash Mangal", "Abhishek"]'
json_qa = '["Anirudh Sharma"]'

def seed():
    with Session(engine) as session:
        # Create Project
        p = Project(
            name="Test Alpha",
            sprint="Sprint 1",
            design_date=date(2023, 10, 1),
            dev_start=date(2023, 10, 5),
            qa_start=date(2023, 10, 15),
            qa_end=date(2023, 10, 20),
            release_date=date(2023, 10, 25),
            dev_team=json_team,
            qa_team=json_qa,
            product_owner="Abhinav Kapoor",
            dev_poc="Yash Mangal",
            qa_poc="Anirudh Sharma"
        )
        session.add(p)
        session.commit()
        session.refresh(p)
        
        # Create Review (Yash Mangal rating others)
        r1 = Review(
            project_id=p.id,
            reviewer_name="Yash Mangal",
            reviewer_role="Dev",
            rated_person="Abhishek",
            rated_role="Dev",
            score_1=4,
            score_2=5,
            score_3=4,
            remarks="Great work",
            delay_reason="None"
        )
        r2 = Review(
            project_id=p.id,
            reviewer_name="Yash Mangal",
            reviewer_role="Dev",
            rated_person="Anirudh Sharma",
            rated_role="QA",
            score_1=5,
            score_2=5,
            score_3=5,
            score_poc=5,
            remarks="Excellent QA support",
            delay_reason="None"
        )
        session.add(r1)
        session.add(r2)
        session.commit()
        print("Seed successful!")

if __name__ == "__main__":
    seed()
