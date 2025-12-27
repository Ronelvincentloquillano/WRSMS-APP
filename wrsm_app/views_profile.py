from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms_profile import UserProfileUpdateForm, StationProfileUpdateForm
from account.models import StationSubscription
from . import models

@login_required
def profile_view(request):
    user = request.user
    station = user.profile.station
    
    # Forms
    if request.method == 'POST':
        user_form = UserProfileUpdateForm(request.POST, instance=user)
        station_form = StationProfileUpdateForm(request.POST, instance=station)
        
        if user_form.is_valid() and station_form.is_valid():
            user_form.save()
            station_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('wrsm_app:profile')
    else:
        user_form = UserProfileUpdateForm(instance=user)
        station_form = StationProfileUpdateForm(instance=station)

    # Subscription Info
    subscription = None
    if hasattr(station, 'subscription'):
        subscription = station.subscription
    
    # Check Setup Completeness
    setup_complete = False
    if station:
        setup_complete = (
            models.JugSize.objects.filter(station=station).exists() and
            models.JugType.objects.filter(station=station).exists() and
            models.OrderType.objects.filter(station=station).exists() and
            models.PaymentType.objects.filter(station=station).exists()
        )
        
    context = {
        'user_form': user_form,
        'station_form': station_form,
        'subscription': subscription,
        'setup_complete': setup_complete,
    }
    return render(request, 'wrsm_app/profile.html', context)
