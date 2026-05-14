import os
from sqlmodel import SQLModel, Field, create_engine, Session, select
from typing import List, Optional
from datetime import date, datetime
import json

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    role: str # Dev, QA, Product, Management
    is_admin: bool = False
    password_hash: str
    permissions: str = Field(default="{}") # JSON string for granular access
    reminder_count: int = Field(default=0) # Track how many automated reminders sent

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sprint: str
    asana_link: Optional[str] = None # New Field
    design_date: Optional[date] = None
    dev_start: Optional[date] = None
    qa_start: Optional[date] = None
    qa_end: Optional[date] = None
    release_date: date
    dev_team: str # Stored as JSON string
    qa_team: Optional[str] = Field(default="[]") # Stored as JSON string
    product_owner: Optional[str] = Field(default="")
    dev_poc: str
    qa_poc: Optional[str] = Field(default="N/A")
    tech_lead_name: Optional[str] = Field(default="")
    project_size: int = Field(default=2) # Points/Weight for this project
    delivery_status: str = Field(default="On Time")
    qa_lead_name: Optional[str] = Field(default="Prateek")

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

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool = Field(default=False)
    created_at: date = Field(default_factory=date.today)

class ProjectEditHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    edited_by: str
    edited_at: datetime = Field(default_factory=datetime.utcnow)
    changes_json: str

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/database.db")

# Fix for Render/Supabase postgres:// vs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Ensure data directory exists for SQLite fallback
if DATABASE_URL.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
