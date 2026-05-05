from sqlmodel import Session, select
from models import engine, Review

def fix_niteesh_role():
    with Session(engine) as session:
        reviews = session.exec(select(Review).where(Review.rated_person == "Niteesh Mahato")).all()
        count = 0
        for r in reviews:
            if r.rated_role == "Dev":
                r.rated_role = "Tech Lead"
                session.add(r)
                count += 1
        if count > 0:
            session.commit()
            print(f"Updated {count} reviews for Niteesh Mahato to Tech Lead role.")
        else:
            print("No old reviews needed fixing.")

if __name__ == "__main__":
    fix_niteesh_role()
