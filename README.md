# Internship Finder & Application Tracker

A Django application for finding US software internships, organizing recruiting emails, and tracking application progress.

I built this project to keep opportunities, application statuses, and recruiting follow-ups organized during my internship search. It started as Python scripts using JSON files and grew into a Django web application with a hosted PostgreSQL database.

## Try the Demo

[Open the public demo](https://internship-finder-tracker.onrender.com/demo/)

Explore the sample dashboard, then use **Find internships** in the demo navigation to search real listings. No login is required.

No login is required. The public demo is read-only: the dashboard uses fictional applications, and the finder displays real source listings. Visitors cannot save opportunities, modify applications, or import emails. Personal application records remain behind authentication.

Hosted on Render with Neon PostgreSQL. The first visit may take about a minute to load while the service wakes up.

## Features

### Internship Finder

- Search listings by company and filter recognized US locations.
- Narrow results to software engineering and development titles.
- Optionally hide roles whose stated requirements are exclusively master's or PhD.
- Browse results in pages of 25 and open employer postings.
- In the authenticated tracker, save opportunities, detect duplicates, and filter companies already applied to.

### Application Tracking

- Store companies, roles, locations, posting links, application dates, and statuses.
- Track Saved, Applied, Assessment, Interview, First Interview, Second Interview, Final Interview, Rejected, and Offer stages.
- Search and filter application records.
- Keep a recorded history of status changes.

### Progress Dashboard

- Show current status counts and branching application paths.
- Sort applications by company or application date.
- Expand each application's recorded history.
- Update statuses in the authenticated tracker.

### Recruiting Email Import

- Paste recruiting email details or upload an `.eml` file.
- Extract suggested company, role, and status information.
- Review and correct suggestions before creating or updating an application.
- Detect repeated imports using stored email identifiers.

Saving opportunities, updating records, and importing emails are available in the authenticated tracker. The public pages demonstrate search and progress visualization without providing editing access.

## Technology

| Area | Tools |
| --- | --- |
| Backend | Python, Django |
| Database | PostgreSQL through Neon; SQLite for local development |
| Interface | HTML, CSS, SVG |
| Listing retrieval | Requests, Beautiful Soup |
| Deployment | Render, Gunicorn, WhiteNoise |
| Database configuration | dj-database-url, Psycopg |
| Development | Git, GitHub, python-dotenv |

## How the Chart Works

Wider lines represent more applications. Recruiting stages stay aligned, and **Current** identifies the latest status. Saved opportunities remain in the table and counts but are excluded from the chart.

Only recorded stages are shown. Earlier events are not reconstructed for applications that predate history tracking. Corrections and repeated rounds remain visible in the expanded history, while the chart summarizes the current application path. History timestamps indicate when changes were recorded in the tracker.

## Local Development Setup

The following commands use Windows PowerShell and Python 3.11. Run them from the repository root. Local setup is for developers who want to run or modify the code; it is not required to visit the hosted website.

### 1. Clone the repository

```powershell
git clone https://github.com/davenje1-star/internship-finder-tracker.git
cd internship-finder-tracker
```

### 2. Create the virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

These commands call the virtual environment's Python directly, so activation is optional.

### 3. Configure the environment

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated key in `.env`:

```dotenv
DJANGO_SECRET_KEY="your-generated-secret-key"
```

Keep `.env` beside `manage.py`. Do not commit it. Leave `DATABASE_URL` unset to use local SQLite. If `DATABASE_URL` is set, the project connects to that PostgreSQL database instead.

### 4. Initialize the database and create an account

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

### 5. Run the local server

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Open the [local demo](http://127.0.0.1:8000/demo/) without signing in. For the private tracker, open [Django admin](http://127.0.0.1:8000/admin/) to sign in, then visit the [tracker](http://127.0.0.1:8000/). Keep the terminal running while using the local website. Press Ctrl+C to stop it.

## Render and Neon Deployment

The hosted application uses a Render Python web service connected to a Neon PostgreSQL database. Local SQLite and hosted PostgreSQL are separate databases; updates do not automatically synchronize between them.

Configure the Render service with:

| Setting | Value |
| --- | --- |
| Language | Python 3 |
| Branch | `main` |
| Root Directory | Leave blank |
| Build Command | `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput` |
| Start Command | `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT` |

Add these private environment variables in Render:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | A generated production secret key |
| `DATABASE_URL` | The Neon PostgreSQL connection string, including its SSL parameters |

The settings detect Render through its `RENDER` environment variable, disable debug mode there, add the supplied `RENDER_EXTERNAL_HOSTNAME` to allowed hosts and trusted origins, and enable HTTPS redirects and secure cookies. WhiteNoise serves collected static files.

Database tables are created by migrations. Existing local records must be transferred separately; deploying the code does not upload `db.sqlite3`. Django fixtures can be used to transfer existing records when needed.

Keep `.env`, `db.sqlite3`, `private_backups/`, and generated `staticfiles/` outside version control. Maintain a private database backup, and review hosting and database plan limits before relying on them long term.

Provider documentation: [Render Django deployment](https://render.com/docs/deploy-django), [Render free service limits](https://render.com/docs/free), and [Neon plans](https://neon.com/pricing).

## Data Source and Limitations

Listings come from [Pitt CSC & Simplify's Summer 2027 internship repository](https://github.com/SimplifyJobs/Summer2027-Internships).

- The finder uses the public source rather than searching every employer's careers website.
- Listings and classifications may be incomplete or outdated. Confirm availability and eligibility on the employer's posting.
- Remote listings without a recognized US location are excluded.
- Title and degree filters depend on the information supplied by the source.
- Email extraction uses patterns and may require corrections. Live inbox monitoring is not connected.
- Opening an employer posting does not submit an application.

## Development Checks

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

## Lessons Learned

- Moving from JSON files to Django models gave the web workflows a shared database.
- Adding status history made it possible to visualize recorded recruiting paths without inventing earlier stages.
- Aligning chart stages avoided unnecessary columns for corrections and repeated events.
- Deployment required production database configuration, static-file handling, and environment variables.
- Windows database exports needed UTF-8 encoding before importing into PostgreSQL.
- Separate public views made it possible to demonstrate the project using fictional dashboard data and public listings.

## Future Improvements

- Add a fictional email-import walkthrough to the demo.
- Support additional listing sources and search options.
- Improve email extraction and validation.
