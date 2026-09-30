# Internship Finder & Application Tracker

A Django application for finding US software internships and tracking applications in one place.

Built with Python, Django, SQLite, and HTML/CSS.

## Features

- Search Summer 2027 internship listings by company.
- Filter locations across 25 US metro areas.
- Hide roles listed as requiring only a master's degree or PhD.
- Skip companies you have already applied to.
- View tracked applications alongside company search results.
- Save opportunities without submitting an application.
- Prevent duplicate saves using posting links, company and role, and matching numeric job IDs.
- Track Saved, Applied, Interview, Rejected, and Offer statuses.
- Search tracked applications by company, role, and status.
- Paste recruiting emails or upload `.eml` files.
- Review extracted email details before creating an application or updating its status.
- Manage application records through Django admin.

## Setup

Requires Python 3.11 or newer. These commands use Windows PowerShell.

### 1. Clone the repository

```powershell
git clone https://github.com/davenje1-star/internship-finder-tracker.git
cd internship-finder-tracker
```

### 2. Create a virtual environment and install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Activating the virtual environment is optional when using its Python executable directly.

### 3. Configure the secret key

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

Keep `.env` in the project root, beside `manage.py`. Do not commit it.

### 4. Set up the database and administrator account

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
```

### 5. Start the application

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in with your administrator account.

## Pages

| Page | Path |
| --- | --- |
| My applications | `/` |
| Find internships | `/finder/` |
| Add application | `/add/` |
| Import email | `/import-email/` |
| Django admin | `/admin/` |

## Using the Finder

Leave the company field blank to search all companies, or enter a company name.

Leave all locations unchecked to search all recognized US locations. Company searches also display your tracked history, including postings no longer available in the source.

Click **View application** to open the employer's posting. Click **Save** to add it to your tracker with the Saved status. Saving does not apply to the job.

After submitting an application on the employer's website, update its status through Django admin.

## Importing Emails

Paste the subject, sender, date, and body, or upload an `.eml` file up to 2 MB.

Review the preview, correct any extracted details, and choose an existing application or create a new one before saving.

In Gmail, an `.eml` file can be downloaded using **More → Download message**.

## Data Source and Limitations

Internship listings are provided by [Pitt CSC & Simplify](https://github.com/SimplifyJobs/Summer2027-Internships).

The finder uses source records marked active and visible, categorized as Software, tagged Summer 2027, and containing recognized US locations. It does not search every employer's careers website.

Source information may be incomplete or outdated. Zero results do not prove that a company has no openings. Confirm availability, degree requirements, and eligibility on the employer's posting.

The degree filter retains listings that accept bachelor's students or have missing degree information. Remote listings without a recognized US location are excluded.

Email extraction may require corrections. Live email forwarding and automatic inbox monitoring are not connected; website email imports require review and confirmation.

## Checks

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

## Local Development

This project uses SQLite and Django's development server. Production deployment requires separate configuration.

Personal environment files, the local database, and imported email data should remain outside version control.