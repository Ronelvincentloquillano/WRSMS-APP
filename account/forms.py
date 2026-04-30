from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.db.models import Q
from wrsm_app.models import Station

class StationOwnerSignupForm(forms.Form):
    station_name = forms.CharField(max_length=100, label="Name of Water Refilling Station")
    first_name = forms.CharField(max_length=30, label="Owner's First Name")
    last_name = forms.CharField(max_length=30, label="Owner's Last Name")
    phone_number = forms.CharField(max_length=15, label="Owner's Phone Number")
    email = forms.EmailField(label="Owner's Email Address")
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    plan = forms.CharField(
        widget=forms.TextInput(attrs={
            'readonly': 'readonly',
            'class': 'mt-1 block w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm dark:bg-slate-600 dark:border-slate-500 dark:text-gray-200'
        }), 
        label="Selected Plan", 
        initial='Trial'
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        
        return cleaned_data


class UsernameOrEmailPasswordResetForm(PasswordResetForm):
    """
    Allow forgot-password lookup by either email field or username.
    This project often stores login email in username.
    """
    def get_users(self, email):
        email_field_name = User.get_email_field_name()
        return User._default_manager.filter(
            Q(**{f"{email_field_name}__iexact": email}) | Q(username__iexact=email),
            is_active=True,
        )
