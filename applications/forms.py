from django import forms
from .models import Application


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = [
            "company",
            "role",
            "status",
            "date_applied",
            "link",
            "location",
        ]
        widgets = {
            "date_applied": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d",
            ),
        }