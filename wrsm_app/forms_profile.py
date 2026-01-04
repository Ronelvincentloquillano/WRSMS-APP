from django import forms
from django.contrib.auth.models import User
from .models import Station

class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        
class StationProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = ['name', 'address', 'contact_number',]
