# 360° Project Review System

A premium, lightweight internal web app to capture project timelines and peer-to-peer ratings.

## Features
- **Project Setup**: Track sprint details, timelines, and team selection.
- **Dynamic Peer Reviews**: Role-based rating logic (Dev, QA, Product) with automated question adjustment.
- **POC Logic**: Extra performance tracking for Team POCs.
- **Insights Dashboard**: Aggregate scores and individual performance leaderboard.
- **Premium Design**: Modern glassmorphism UI with smooth transitions.

## Tech Stack
- **Backend**: FastAPI (Python 3.8+)
- **Database**: SQLite with SQLModel (SQLAlchemy + Pydantic)
- **Frontend**: Vanilla CSS + Jinja2 Templates (Modern Glassmorphism)

## Quick Start
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python run.py
   ```
3. Open [http://localhost:8000](http://localhost:8000) in your browser.

## Project Structure
- `main.py`: API routes and logic.
- `models.py`: Database schema and models.
- `templates/`: HTML views.
- `static/`: CSS and assets.
- `data/`: SQLite database storage.
