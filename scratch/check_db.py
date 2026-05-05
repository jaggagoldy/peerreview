from sqlmodel import Session, select
from models import Project, Review, User, engine

def check_db():
    with Session(engine) as session:
        print("--- USERS ---")
        users = session.exec(select(User)).all()
        for u in users:
            print(f"ID: {u.id}, Email: {u.email}, Name: {u.name}")
        
        print("\n--- PROJECTS ---")
        projects = session.exec(select(Project)).all()
        for p in projects:
            print(f"ID: {p.id}, Name: {p.name}, POCs: {p.dev_poc} / {p.qa_poc}")
        
        print("\n--- REVIEWS ---")
        reviews = session.exec(select(Review)).all()
        for r in reviews:
            print(f"ID: {r.id}, ProjectID: {r.project_id}, Reviewer: {r.reviewer_name}, Rated: {r.rated_person}")

if __name__ == "__main__":
    check_db()
