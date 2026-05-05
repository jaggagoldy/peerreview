from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import List, Optional
from datetime import date
import json

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    role: str # Dev, QA, Product, Management
    is_admin: bool = False
    password_hash: str
    permissions: str = Field(default="{}") # JSON string for granular access

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sprint: str
    design_date: Optional[date] = None
    dev_start: Optional[date] = None
    qa_start: Optional[date] = None
    qa_end: Optional[date] = None
    release_date: date # Release date remains mandatory as the project 'end'
    dev_team: str # Stored as JSON string
    qa_team: str # Stored as JSON string
    product_owner: str
    dev_poc: str
    qa_poc: str
    tech_lead_name: str = Field(default="Niteesh Mahato")

    def get_dev_team(self) -> List[str]:
        return json.loads(self.dev_team)
    
    def get_qa_team(self) -> List[str]:
        return json.loads(self.qa_team)

class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int
    reviewer_name: str
    reviewer_role: str
    rated_person: str
    rated_role: str
    
    # Generic scores based on role:
    # Dev: Accountability, Productivity, Coordination
    # QA: Test Coverage, Bug Quality, Communication
    # Product: Req Clarity, Support, Change Handling
    # Tech Lead: Technical Guidance, Code Quality Support, Team Mentorship
    score_1: int 
    score_2: int 
    score_3: int 
    
    score_poc: Optional[int] = None
    score_tech_lead: Optional[int] = None # Legacy: Only used if 1-score TL rating is submitted
    remarks: str
    improvement_feedback: str = Field(default="")
    delay_reason: str

class DeletedProject(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int
    name: str
    deleted_by: str
    deleted_at: date = Field(default_factory=date.today)
    data_json: str # Store full project data as JSON for recovery

sqlite_file_name = "data/database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
