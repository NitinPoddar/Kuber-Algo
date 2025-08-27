from django import forms
from django.contrib.auth.forms import UserCreationForm, get_user_model
from .models import User,AlgoList
# forms.py
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
import re

User = get_user_model()

_PHONE_RE = re.compile(r'^\+?\d{7,15}$')

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["name", "username", "email", "phone"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise ValidationError("Email is required.")
        qs = User.objects.filter(email__iexact=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not _PHONE_RE.match(phone):
            raise ValidationError("Enter a valid phone number (include country code if applicable).")
        qs = User.objects.filter(phone=phone)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise ValidationError("This phone is already registered.")
        return phone


# forms.py
from django import forms
from django.contrib.auth import get_user_model
import re

User = get_user_model()
_PHONE_RE = re.compile(r"^\+?\d{7,15}$")

class SimpleSignupForm(forms.Form):
    email = forms.EmailField(label="Email")
    phone = forms.CharField(label="Mobile", max_length=20)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not _PHONE_RE.match(phone):
            raise ValidationError("Enter a valid mobile number (7–15 digits, optional +).")
        if User.objects.filter(phone=phone).exists():
            raise ValidationError("This mobile number is already registered.")
        return phone

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1") or ""
        p2 = cleaned.get("password2") or ""
        if p1 != p2:
            self.add_error("password2", "Passwords do not match.")

        # strength: at least 8 chars + letters + digits (you can add special-char check if you want)
        if len(p1) < 8 or not re.search(r"[A-Za-z]", p1) or not re.search(r"\d", p1):
            self.add_error("password1", "Use at least 8 characters with letters and numbers.")
        return cleaned

class AlgorithmForm(forms.ModelForm):
    class Meta:
        model = AlgoList
        fields = ['algo_name', 'minimum_fund_reqd', 'algo_description']
