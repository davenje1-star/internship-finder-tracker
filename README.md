# Internship Finder & Application Tracker

A Django web application for finding US software internships, organizing recruiting emails, and tracking application progress.

I built this project to solve a problem in my own internship search: keeping opportunities, application statuses, and recruiting follow-ups organized in one place.

The project began as Python scripts using JSON files. I transitioned to Django and SQLite to learn database models, forms, authentication, migrations, and web development while building a tool I could use.

## Technology

- Python
- Django
- SQLite
- HTML and CSS
- Requests
- Beautiful Soup
- python-dotenv
- Git and GitHub

## Features

### Internship Search

- Search Summer 2027 software internships by company.
- Filter locations across 25 US metro areas.
- Hide listings whose stated degree requirements are exclusively master's or PhD.
- Skip companies you have already applied to.
- View tracked application history alongside company search results.
- Browse results in pages of 25.
- Save opportunities to the tracker.
- Detect duplicates using posting links, company and role, and matching long numeric job IDs.

### Application Tracking

- Search applications by company or role.
- Filter applications by status.
- Track Saved, Applied, Assessment, Interview, First Interview, Second Interview, Final Interview, Rejected, and Offer statuses.
- Store application dates, posting links, and locations.
- Manage application records through Django admin.
- Scope website application records to the signed-in user.

### Email Import

- Paste recruiting email text or upload an `.eml` file up to 2 MB.
- Extract suggested company, role, and status information.
- Review and correct the preview before saving.
- Create an application or update an existing application.
- Detect repeated imports using stored email identifiers.
- Preserve the application date when updating an existing record.

### Progress Dashboard

- Visualize recorded application paths with a branching flow diagram.
- See current application counts by status.
- Change statuses directly from the dashboard.
- Expand each application's recorded status history.
- Preserve interview stages when an application is later rejected.
- Avoid duplicate history entries when saving an unchanged status.

## Setup

Requires Python 3.11 or newer. The commands below use Windows PowerShell.

### 1. Clone the repository

```powershell
git clone https://github.com/davenje1-star/internship-finder-tracker.git
cd internship-finder-tracker
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Install dependencies

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

These commands call the virtual environment's Python executable directly, so activation is optional.

### 4. Configure the environment

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Generate a secret key:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated value in `.env`:

```dotenv
DJANGO_SECRET_KEY="your-generated-secret-key"
```

Keep `.env` in the project root, beside `manage.py`. Do not commit the private key.

### 5. Apply migrations

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

### 6. Create an administrator account

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

### 7. Start the server

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/admin/ and sign in with the account you created. Then open the tracker.

Keep the server running while using the website.

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

Enter a company name or leave the field blank to search all companies.

Select metro areas, or leave all locations unchecked to search all recognized US locations.

Uncheck **Skip companies I have already applied to** when looking for additional roles at those companies.

The graduate-degree filter keeps listings that accept bachelor's students and listings with missing degree information. Always confirm requirements on the employer's posting.

Click **View application** to open the employer's website. Click **Save** to add the opportunity with the Saved status.

Saving an opportunity does not submit an application. After applying on the employer's website, change its status to Applied.

## Importing Recruiting Emails

Open **Import email** and either:

- Paste the subject, sender, email date, and body.
- Upload an `.eml` file.

In Gmail, use the message's **More → Download message** option to download an `.eml` file.

Review the suggested details before saving. Choose an existing application to update its status, or create a new application.

An assessment invitation does not necessarily mean an interview. A rejection date is not the original application date.

## Tracking Progress

Open **My progress** to view the flow diagram and current status counts.

Choose a new status beside an application and click **Save**. The dashboard reloads with the updated history and graph.

Line widths represent application counts. Hover over a line to see its count. Longer histories can be viewed by scrolling horizontally.

Applications that existed before history tracking began receive a starting snapshot. Earlier stages are unknown and are not reconstructed.

**Awaiting recorded update** means the current status is Applied. It does not establish that an employer has ghosted the applicant.

History timestamps show when changes were recorded in the tracker, which may differ from when the employer sent an update.

Status history is recorded through individual application saves. Bulk database updates using `QuerySet.update()` bypass that recording.

## Data Source and Limitations

Listings are provided by [Pitt CSC & Simplify](https://github.com/SimplifyJobs/Summer2027-Internships).

The finder includes source records that are:

- Marked active and visible.
- Categorized as Software.
- Tagged Summer 2027.
- Associated with a recognized US location.

The application does not search every employer's careers website. Source listings and classifications may be incomplete or outdated.

Zero results do not prove that a company has no internships. Check the employer's careers website for complete availability and eligibility information.

Remote listings without a recognized US location are excluded. Duplicate detection can miss postings with different links or titles when no matching numeric job ID is available.

Email extraction uses patterns and may require corrections. Live email forwarding and automatic inbox monitoring are not connected. Website imports require review and confirmation.

## Checks

Run Django's system checks:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Check for model changes missing migration files:

```powershell
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Inspect migration status:

```powershell
.\.venv\Scripts\python.exe manage.py showmigrations applications
```

## Debugging and Lessons Learned

### PowerShell blocked virtual environment activation

PowerShell's execution policy blocked `Activate.ps1`.

I used the virtual environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

This runs the project with its installed dependencies without requiring activation.

### Running Django files directly caused import errors

Running `views.py` or `urls.py` directly produced errors such as:

```text
ImportError: attempted relative import with no known parent package
```

These modules depend on Django's project initialization. I used `manage.py` commands to load the application correctly.

### JSON and SQLite showed different application counts

The original scripts read `applications.json`, while the website used SQLite. Changes in one store did not automatically appear in the other.

I updated the tracker and finder workflows to use Django models, making the database the shared application store.

### A page returned a 404

The `/finder/` and `/import-email/` pages initially had no matching URL patterns.

I added the application routes and included `applications.urls` in the project's main URL configuration. I also ensured each route referenced an implemented view.

### Environment configuration raised a KeyError

Django raised:

```text
KeyError: 'DJANGO_SECRET_KEY'
```

The `.env` file existed, but it did not contain the expected variable name.

I corrected the variable to `DJANGO_SECRET_KEY` and loaded `.env` before reading it in `config/settings.py`.

### Long location lists needed a larger field

Some listings contained many locations, making a short character field unsuitable.

I changed the application's location field to `TextField` and added a migration.

### Company search displayed unfiltered results

Adding a company input to the template did not filter results until the view processed it.

I added company filtering, preserved the search in the session, and displayed matching tracked applications separately from available listings.

### Duplicate detection missed a differently titled posting

An RTX posting had a simplified source title, while the tracked application contained its requisition number. Exact title matching missed the duplicate.

I added matching for long numeric job IDs within the same company, while excluding four-digit years.

### Existing applications had no recorded status history

A current status alone could not show whether a rejected application had reached an interview.

I added a status-history model, starting snapshots for existing records, and automatic recording of future status changes. I kept earlier stages unknown rather than inventing them.

## Updating the Project on GitHub

For README changes:

```powershell
git add README.md
git commit -m "Update README"
git push
```

For application changes, review the files before committing:

```powershell
git status --short
git add applications
git diff --cached --name-only
git commit -m "Describe the application changes"
git push
```

Keep private environment files, the local database, and personal email data outside version control.

## Development Scope

This project is configured for local development with SQLite and Django's development server.

Production hosting requires separate deployment configuration. Django admin and command-line tools have their own access scope; website filtering does not make every management workflow a multiuser service.