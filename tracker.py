from django.core.exceptions import ValidationError
from django.utils import timezone

from applications.models import Application


valid_statuses = ("Saved", "Applied", "Interview", "Rejected", "Offer")

while True:
    choice = input(
        "Add an application, view the list, update, delete, or quit?: "
    ).strip().lower()

    if choice == "quit":
        break

    if choice not in ("add", "view", "update", "delete"):
        print("Please enter add, view, update, delete, or quit.")
        continue

    if choice == "add":
        company = input("Company name: ").strip()
        role = input("Role title: ").strip()
        link = input("Application link: ").strip()

        if not company or not role:
            print("Company and role are required.")
            continue

        duplicate = Application.objects.filter(
            company__iexact=company,
            role__iexact=role,
        ).exists()

        if duplicate or (
            link and Application.objects.filter(link=link).exists()
        ):
            print("That application is already in your tracker.")
            continue

        status = input(
            "Status (Saved/Applied/Interview/Rejected/Offer): "
        ).strip().capitalize()

        if status not in valid_statuses:
            print("Choose Saved, Applied, Interview, Rejected, or Offer.")
            continue

        application = Application(
            company=company,
            role=role,
            status=status,
            date_applied=timezone.localdate() if status == "Applied" else None,
            link=link,
        )

        try:
            application.full_clean()
            application.save()
        except ValidationError as error:
            print(f"Could not save application: {error}")
            continue

        print("Application saved.")

    applications = list(Application.objects.order_by("pk"))

    if not applications:
        print("Your tracker is empty.")
        continue

    print(f"\nTracker contains {len(applications)} applications.")

    for number, item in enumerate(applications, start=1):
        print(f"{number}. {item.company} - {item.role} ({item.status})")

    if choice not in ("update", "delete"):
        continue

    answer = input("Which application number? ").strip()

    if not answer.isdigit() or not 1 <= int(answer) <= len(applications):
        print("Please enter a number from the list.")
        continue

    selected = applications[int(answer) - 1]

    if choice == "update":
        new_status = input(
            "New status (Saved/Applied/Interview/Rejected/Offer): "
        ).strip().capitalize()

        if new_status not in valid_statuses:
            print("Choose Saved, Applied, Interview, Rejected, or Offer.")
            continue

        selected.status = new_status

        if new_status == "Applied" and not selected.date_applied:
            selected.date_applied = timezone.localdate()

        metadata = dict(selected.email_metadata)
        metadata["last_update_email_date"] = timezone.localdate().isoformat()
        selected.email_metadata = metadata

        try:
            selected.full_clean()
            selected.save()
        except ValidationError as error:
            print(f"Could not update application: {error}")
            continue

        print("Status updated.")

    else:
        confirm = input(
            f"Delete {selected.company} - {selected.role}? (yes/no): "
        ).strip().lower()

        if confirm != "yes":
            print("Deletion cancelled.")
            continue

        selected.delete()
        print("Application deleted.")