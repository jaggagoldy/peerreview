from sqlmodel import Session, select
from models import User, Review, Project, engine
import json

def migrate_data():
    with Session(engine) as session:
        # Create a mapping of email to name
        users = session.exec(select(User)).all()
        email_to_name = {u.email: u.name for u in users}
        
        print("Migrating Reviews...")
        reviews = session.exec(select(Review)).all()
        updated_count = 0
        for r in reviews:
            changed = False
            # Fix reviewer_name
            if "@" in r.reviewer_name:
                name = email_to_name.get(r.reviewer_name)
                if name:
                    print(f"Updating Review ID {r.id}: Reviewer email '{r.reviewer_name}' -> '{name}'")
                    r.reviewer_name = name
                    changed = True
            
            # Fix rated_person
            if "@" in r.rated_person:
                name = email_to_name.get(r.rated_person)
                if name:
                    print(f"Updating Review ID {r.id}: Rated person email '{r.rated_person}' -> '{name}'")
                    r.rated_person = name
                    changed = True
            
            if changed:
                session.add(r)
                updated_count += 1
        
        print(f"Updated {updated_count} reviews.")
        
        # Also check Projects just in case
        print("Checking Projects...")
        projects = session.exec(select(Project)).all()
        for p in projects:
            changed = False
            if "@" in p.product_owner:
                name = email_to_name.get(p.product_owner)
                if name:
                    p.product_owner = name
                    changed = True
            if "@" in p.dev_poc:
                name = email_to_name.get(p.dev_poc)
                if name:
                    p.dev_poc = name
                    changed = True
            if "@" in p.qa_poc:
                name = email_to_name.get(p.qa_poc)
                if name:
                    p.qa_poc = name
                    changed = True
            
            # Fix teams (JSON strings)
            dev_team = json.loads(p.dev_team)
            new_dev_team = [email_to_name.get(m, m) if "@" in m else m for m in dev_team]
            if dev_team != new_dev_team:
                p.dev_team = json.dumps(new_dev_team)
                changed = True
            
            qa_team = json.loads(p.qa_team)
            new_qa_team = [email_to_name.get(m, m) if "@" in m else m for m in qa_team]
            if qa_team != new_qa_team:
                p.qa_team = json.dumps(new_qa_team)
                changed = True
                
            if changed:
                session.add(p)
                print(f"Updated Project ID {p.id}")

        session.commit()
        print("Migration complete!")

if __name__ == "__main__":
    migrate_data()
