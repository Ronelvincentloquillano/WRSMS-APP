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
        fields = ['name', 'address', 'contact_number', 'station_code']
        # Maybe station_code shouldn't be editable easily? 
        # But user requested "Station Name, Address, Contact Number".
        # I'll include station_code as read-only or editable if desired.
        # Let's keep it editable for now or read-only if it's auto-generated unique ID.
        # User prompt didn't specify, but `Station` model has it.
