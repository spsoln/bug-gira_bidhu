# 🐈‍⬛ Bug-Gira

A lightweight project management and ticket tracking tool — a self-hosted alternative to Test Management for small teams.

Built from scratch as a personal project by **[Bidhu Tiwari]** ([June 2026]).

---

## Why I Built This

My team didn't have Jira access, so I built our own. Bug-Gira covers the 80% of Jira that teams actually use — projects, tickets, sprints, a Kanban board with swimlanes, comments — without the licensing cost, complexity, or feature bloat.

## Features

- **Projects** with custom keys (e.g., `BAT-123`)
- **Tickets** — full CRUD with type, priority, status, assignee, reporter, and due date
- **Kanban board** with drag-and-drop status updates
- **Swimlanes** — board grouped by assignee, collapsible per user
- **Sprints** — planned / active / completed lifecycle with progress tracking
- **Backlog** — bidirectional ticket movement between sprint and backlog
- **Comments** — inline ticket discussion with author attribution
- **Cancellation workflow** with mandatory reason and full audit trail (who/when/why)
- **Permanent deletion** with confirmation dialog
- **Authentication** — login / logout with protected routes
- **Admin-only sprint management** — only staff users can create/start/complete sprints
- **Dashboard home page** — personal stats, "my tickets," active sprint progress
- **Context-aware sidebar** — global navigation outside projects, project navigation when inside one
- **Search** on backlog and all-tickets views
- **Due date tracking** with overdue highlighting

## Tech Stack

- **Backend:** Python 3.11, Django 4.2 LTS
- **Database:** PostgreSQL 15
- **Frontend:** Django templates, vanilla JavaScript, SortableJS for drag-and-drop
- **Styling:** Custom CSS with Inter font, no framework

## Screenshots

*(Add screenshots here — Dashboard, Kanban board, Ticket detail)*

## Local Setup

```bash
# Clone the repo
git clone https://github.com/spsoln/bug-gira_mgmt_bidhu
cd bug-gira

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install django==4.2 psycopg2-binary

# Set up the database (assumes PostgreSQL is running locally)
createdb jiraclone_db

# Run migrations
python manage.py migrate

# Create a superuser
python manage.py createsuperuser

# Run it
python manage.py runserver
```

Visit http://127.0.0.1:8000

## Project Status

Fully functional. Currently being used as a personal/team tool. Production hosting pending.

## Author

**[Your Full Name]**
- Personal project, built on personal time and equipment
- Contact: solutionssp000@gmail.com 
- GitHub: @spsoln

## License

MIT License — see [LICENSE](LICENSE) for details.