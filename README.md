# Internship Finder & Application Tracker

A Django web application for finding US software internships, organizing recruiting emails, and tracking application progress.

I built this project to solve a problem in my own internship search: keeping opportunities, application statuses, and recruiting follow-ups organized in one place. It began as Python scripts using JSON files. I moved to Django and SQLite to learn database models, forms, authentication, migrations, and web development while building a tool I could use. The hosted version now uses PostgreSQL through Neon.

## Live Website

[Open Internship Finder & Application Tracker](https://internship-finder-tracker.onrender.com/)

The hosted website runs without starting a local server or opening VS Code. It currently requires an authorized Django staff account and is intended for personal use. Public registration and a recruiter demo are not implemented. Visitors can review the source code in this repository; the live link alone does not grant access to the tracker.

The application is hosted on Render with a Neon PostgreSQL database. Render's free web service sleeps after inactivity, so the first visit may take about a minute to load.

## Technology

- Python and Django
- PostgreSQL through Neon for the hosted database
- SQLite for local development
- HTML, CSS, and SVG for the interface and progress chart
- Requests and Beautiful Soup for listing retrieval and text processing
- WhiteNoise for production static files
- Gunicorn for the production web server
- dj-database-url and Psycopg for PostgreSQL connections
- python-dotenv for local environment configuration
- Git, GitHub, and Render for version control and deployment

## Features

### Internship Search

- Search Summer 2027 software internships by company.
- Filter locations across 25 US metro areas.
- Optionally restrict results to software engineering and development titles.
- Hide listings whose stated degree requirements are exclusively master's or PhD.
- Skip companies you have already applied to, or explore additional roles at those companies.
- View tracked applications alongside company search results.
- Browse results in pages of 25 and save opportunities.
- Detect duplicates using posting links, company and role, and matching long numeric job IDs.

### Application Tracking

- Search applications by company or role and filter by status.
- Track Saved, Applied, Assessment, Interview, First Interview, Second Interview, Final Interview, Rejected, and Offer statuses.
- Store application dates, posting links, and locations.
- Manage application records through Django admin.
- Scope website application records to the signed-in user.

### Recruiting Email Import

- Paste recruiting email details or upload an `.eml` file up to 2 MB.
- Extract suggested company, role, and status information.
- Review and correct an editable preview before saving.
- Create an application or update an existing application.
- Detect repeated imports using stored email identifiers.
- Preserve the application date when updating an existing record.

### Progress Dashboard

- Visualize recorded application paths with a branching flow diagram.
- Show current application counts by status.
- Update statuses directly from the dashboard.
- Expand each application's complete recorded status history.
- Sort company names A–Z or Z–A, and application dates earliest or latest; missing dates stay last.
- Align recruiting stages instead of adding columns for every history event.
- Label the latest stage as Current without duplicating it.
- Exclude Saved opportunities from the chart while retaining them in the table and status counts.
- Avoid duplicate history entries when saving an unchanged status.

## Using the Hosted Tracker

1. Open the [live website](https://internship-finder-tracker.onrender.com/).
2. Sign in with an authorized account. The [admin login](https://internship-finder-tracker.onrender.com/admin/) can also be used to sign in.
3. Search for internships and save relevant opportunities.
4. Submit applications on the employer's website.
5. Mark submitted applications Applied and update their stages as follow-ups arrive.

Saving an opportunity or opening its posting does not submit an application or automatically mark it Applied. Status changes are saved to the hosted database and do not require a Git commit or redeployment.

## Pages

| Page | Path |
| --- | --- |
| My applications | `/` |
| Find internships | `/finder/` |
| Add application | `/add/` |
| Import email | `/import-email/` |
| My progress | `/progress/` |
| Django admin | `/admin/` |

## Using the Finder

Enter a company name or leave the field blank to search all companies. Select metro areas, or leave all locations unchecked to search all recognized US locations.

Uncheck **Skip companies I have already applied to** when looking for additional roles at those companies. Company searches also show your tracked applications, even when their postings are no longer in the source.

The graduate-degree filter keeps listings that accept bachelor's students and listings with missing degree information. The software-title filter narrows results by title and may exclude broader technology internships. Always confirm eligibility and requirements on the employer's posting.

Click **View application** to open the employer's website. Click **Save** to add an opportunity with the Saved status. After submitting an application, change its status to Applied.

## Importing Recruiting Emails

Open **Import email** and either paste the subject, sender, email date, and body, or upload an `.eml` file. In Gmail, use the message's **More → Download message** option to obtain an `.eml` file.

Review the suggestions before saving. Choose an existing application to update its status, or create a new application. An assessment invitation does not necessarily mean an interview, and a rejection date is not the original application date.

Email extraction uses patterns and may need corrections. Live email forwarding and automatic inbox monitoring are not connected. Manual website imports require review and confirmation.

## Understanding the Progress Chart

Wider lines represent more applications. Recruiting stages stay aligned even when applications have different histories. **Current** marks an application's latest status.

Saved opportunities remain in the table but are excluded from the chart. Only recorded stages are shown; the chart does not assume that every application passed through an assessment or interview.

Applications that existed before history tracking began have a starting snapshot. Earlier stages are unknown and are not reconstructed. The chart summarizes the current application path; corrections and repeated rounds remain available in **View history**.

History timestamps show when changes were recorded in the tracker, which may differ from when an employer sent an update. Individual application saves record status changes. Bulk database updates using `QuerySet.update()` bypass this recording.

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

Open [Django admin](http://127.0.0.1:8000/admin/) to sign in, then visit the [tracker](http://127.0.0.1:8000/). Keep the terminal running while using the local website. Press Ctrl+C to stop it.

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

Database tables are created by migrations. Existing local records must be transferred separately; deploying the code does not upload `db.sqlite3`. The hosted account and application history were transferred through a private Django fixture.

Keep `.env`, `db.sqlite3`, `private_backups/`, and generated `staticfiles/` outside version control. Maintain a private database backup, and review hosting and database plan limits before relying on them long term.

Provider documentation: [Render Django deployment](https://render.com/docs/deploy-django), [Render free service limits](https://render.com/docs/free), and [Neon plans](https://neon.com/pricing).

## Data Source and Limitations

Listings are provided by [Pitt CSC & Simplify](https://github.com/SimplifyJobs/Summer2027-Internships). The finder selects source records that are active and visible, categorized as Software, tagged Summer 2027, and associated with a recognized US location.

The finder does not search every employer's careers website. Source listings and classifications may be incomplete or outdated. Zero results do not establish that a company has no internships; check its careers website for full availability.

Remote listings without a recognized US location are excluded. Duplicate detection can miss postings with different links or titles when no matching numeric job ID is available.

This is currently a personal tracker, not a public multiuser service. Website views use account-scoped records, while Django admin and management commands have their own permissions and access scope. Do not share administrator credentials as a demo account.

## Checks

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py showmigrations applications
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

These check Django configuration, detect missing migrations, show migration status, and verify static-file collection. They do not replace testing the website's workflows.

## Debugging and Lessons Learned

### PowerShell blocked virtual environment activation

PowerShell's execution policy blocked `Activate.ps1`. Calling `.\.venv\Scripts\python.exe` directly let me use the installed dependencies without changing the execution policy.

### Running Django modules directly caused import errors

Running `views.py` directly produced `ImportError: attempted relative import with no known parent package`. Django modules depend on project initialization, so I used `manage.py` commands instead.

### A circular import prevented startup

An accidental edit placed a forms import inside the forms module itself. I corrected the file contents and checked the project through `manage.py check`. This reinforced the importance of reviewing unsaved edits before closing the editor.

### JSON and SQLite showed different application counts

The original scripts read JSON while the website used SQLite. I moved the application workflows to Django models so they shared a database. Local SQLite and hosted PostgreSQL remain separate environments rather than automatically synchronized stores.

### A new page returned a 404

New pages needed URL patterns, implemented views, and an included application URL configuration. Adding navigation alone did not create a route.

### Environment configuration raised a KeyError

`KeyError: 'DJANGO_SECRET_KEY'` occurred because the environment file lacked the expected variable. I corrected the name and loaded `.env` before reading the key. On Render, the value is configured in the service's environment settings.

### Long location lists needed a larger field

Some postings contained many locations. I changed `location` to a `TextField` and added a migration rather than restricting the data to a short character field.

### Company search initially returned unfiltered results

The template's company input needed corresponding view logic. I added filtering, preserved search options in the session, and displayed tracked applications separately from available source listings.

### Duplicate detection missed a differently titled posting

An RTX source title differed from the tracked title containing its requisition number. I added matching for long numeric job IDs within the same company while excluding four-digit years.

### Existing records had no status history

A current status could not show earlier interview stages. I added a status-history model and starting snapshots, then recorded future changes without inventing earlier events.

### Saved status and duplicate nodes stretched the chart

Using each history event as a chart column made Saved → Applied paths longer than baseline Applied paths. I aligned recruiting stages, excluded Saved from the chart, and labeled the last active stage Current instead of creating a duplicate endpoint. The table retains the full history.

### A database export failed to load as UTF-8

A Windows-generated fixture produced a `UnicodeDecodeError` during the Neon import. I regenerated the export with `PYTHONUTF8=1`, imported it successfully, and verified application and history counts.

### Deployment required more than running the development server

I added Gunicorn, PostgreSQL connection settings, WhiteNoise, static-file collection, and production HTTPS settings. Separating configuration and secrets from source code allowed the same project to run locally and on Render.

## Updating the Project on GitHub

For README edits, save the file first, then run:

```powershell
git add README.md
git commit -m "Update README"
git push
```

For code changes, review the modified files and stage the intended changes:

```powershell
git status --short
git add applications config/settings.py requirements.txt .gitignore
git diff --cached --name-only
git commit -m "Describe the changes"
git push
```

Render can redeploy commits when automatic deployments are enabled. Application status changes are database updates, not code changes, and do not need to be pushed to GitHub.

## Future Improvements

- A public, read-only recruiter demo using sample data.
- Broader listing sources and more flexible search options.
- Additional email extraction patterns and validation.

Public registration and live inbox integration are outside the current scope.
