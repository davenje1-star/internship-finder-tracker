from django import forms

from .models import Application


class PastedEmailForm(forms.Form):
    subject = forms.CharField(max_length=500)
    sender = forms.CharField(
        max_length=300,
        help_text="Paste the sender's name or email address.",
    )
    email_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    body = forms.CharField(
        max_length=100000,
        widget=forms.Textarea(attrs={"rows": 12}),
    )


class EmailPreviewForm(forms.Form):
    application = forms.ModelChoiceField(
        queryset=Application.objects.none(),
        required=False,
        empty_label="Create a new application",
    )
    company = forms.CharField(max_length=200)
    role = forms.CharField(max_length=300)
    status = forms.ChoiceField(
        choices=[("", "Choose a status")] + Application.STATUS_CHOICES
    )
    date_applied = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=(
            "For new applications only. "
            "A rejection date is not the application date."
        ),
    )

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None and owner.is_authenticated:
            self.fields["application"].queryset = (
                Application.objects.filter(owner=owner)
                .order_by("company", "role")
            )


class EmailUploadForm(forms.Form):
    email_file = forms.FileField(
        label="Upload an email",
        help_text="Choose a .eml file, up to 2 MB.",
        widget=forms.ClearableFileInput(attrs={"accept": ".eml"}),
    )

    def clean_email_file(self):
        uploaded = self.cleaned_data["email_file"]
        if not uploaded.name.lower().endswith(".eml"):
            raise forms.ValidationError("Choose a .eml file.")
        if uploaded.size > 2 * 1024 * 1024:
            raise forms.ValidationError("The file must be 2 MB or smaller.")
        return uploaded
