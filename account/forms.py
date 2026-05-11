from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template import loader
from django.utils.translation import gettext_lazy as _

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
    Django's default PasswordResetForm uses EmailField, which rejects plain
    usernames — many users only know their login name, not their stored email.
    """
    email = forms.CharField(
        label=_("Email or username"),
        max_length=254,
        strip=True,
        widget=forms.TextInput(
            attrs={"autocomplete": "username", "autocapitalize": "none"}
        ),
    )

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip()

    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """
        Django's PasswordResetForm.send_mail catches all exceptions and only logs
        them, so the reset view always redirects to "done" even when SMTP fails.
        Re-raise so the view can show a clear error and operators can fix EMAIL_*.
        """
        subject = loader.render_to_string(subject_template_name, context)
        subject = "".join(subject.splitlines())
        body = loader.render_to_string(email_template_name, context)
        email_message = EmailMultiAlternatives(subject, body, from_email, [to_email])
        if html_email_template_name is not None:
            html_email = loader.render_to_string(html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")
        email_message.send(fail_silently=False)

    def get_users(self, email):
        if not email:
            return ()
        email_field_name = User.get_email_field_name()
        qs = User._default_manager.filter(
            Q(**{f"{email_field_name}__iexact": email}) | Q(username__iexact=email),
            is_active=True,
        )
        return (u for u in qs if u.has_usable_password())
