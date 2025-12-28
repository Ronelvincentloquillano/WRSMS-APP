from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group
from django.contrib.auth import login
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.contrib import messages
from django.template.loader import render_to_string
from .forms import StationOwnerSignupForm
from .models import PendingRegistration, StationSubscription, SubscriptionPlan
from wrsm_app.models import Station, Profile
from django.contrib.auth.hashers import make_password
import datetime

def signup_view(request):
    if request.method == 'POST':
        form = StationOwnerSignupForm(request.POST)
        if form.is_valid():
            # Mock Payment Integration
            # In a real scenario, we would redirect to a payment gateway here if a paid plan was selected.
            # For now, we assume the user is signing up for a trial or payment is handled elsewhere.
            
            data = form.cleaned_data
            email = data['email']
            
            # Create Pending Registration
            pending_user, created = PendingRegistration.objects.update_or_create(
                email=email,
                defaults={
                    'station_name': data['station_name'],
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'phone_number': data['phone_number'],
                    'password': make_password(data['password']), # Hash password for storage
                    'plan_name': data.get('plan', 'Trial'),
                    'activation_key': get_random_string(32)
                }
            )

            # Send Email
            activation_link = request.build_absolute_uri(
                reverse('account:activate', kwargs={'key': pending_user.activation_key})
            )
            
            subject = "Confirm your WRSM Account"
            message = f"Hi {data['first_name']},\n\nPlease confirm your account by clicking the link below:\n{activation_link}\n\nThank you!"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            
            try:
                send_mail(subject, message, from_email, recipient_list)
                return render(request, 'account/register_done.html', {'email': email})
            except Exception as e:
                # In production, handle email errors gracefully
                print(f"Email error: {e}")
                messages.error(request, "Error sending confirmation email. Please try again.")
    else:
        initial_plan = request.GET.get('plan', 'Trial')
        form = StationOwnerSignupForm(initial={'plan': initial_plan})

    return render(request, 'account/register.html', {'form': form})

def activate_account(request, key):
    pending_reg = get_object_or_404(PendingRegistration, activation_key=key)
    
    # 1. Create User
    username = pending_reg.email # Use email as username
    if User.objects.filter(username=username).exists():
        messages.error(request, "User already exists.")
        return redirect('account:login')

    user = User.objects.create(
        username=username,
        email=pending_reg.email,
        first_name=pending_reg.first_name,
        last_name=pending_reg.last_name,
        password=pending_reg.password # Already hashed
    )
    # Since we set the password directly as a hash, we might need to adjust. 
    # User.objects.create handles raw passwords usually if using create_user. 
    # But here we are passing a hashed password to 'password' field. 
    # Actually, create() saves raw. We should use:
    user.password = pending_reg.password
    user.save()

    # Grant Permissions
    group, _ = Group.objects.get_or_create(name='station owner/admin')
    user.groups.add(group)

    # 2. Create Station
    station = Station.objects.create(
        name=pending_reg.station_name,
        contact_number=pending_reg.phone_number
        # Station code logic handled in Station.save if present or we can generate
    )

    # 3. Create Profile
    profile = Profile.objects.create(
        user=user,
        station=station,
        station_code=station.station_code 
    )
    # Link profile to station (allowed_stations logic in Profile.save handles this?)
    # Profile.save calls self.allowed_stations.add(self.station)
    profile.save()

    # 4. Subscription (Trial)
    # Calculate 30 days trial
    end_date = datetime.date.today() + datetime.timedelta(days=30)
    StationSubscription.objects.create(
        station=station,
        is_trial=True,
        end_date=end_date
    )

    # 5. Create Station Settings (Prevent 404 on update)
    from wrsm_app.models import StationSetting
    StationSetting.objects.create(
        station=station,
        default_delivery_rate=0,
        default_unit_price=0,
        default_minimum_delivery_qty=0
    )

    # 6. Cleanup
    pending_reg.delete()

    # 7. Send Welcome Email & Notify Admin
    try:
        subject = "Welcome to SmartDynamic Refilling!"
        message = render_to_string('account/welcome_email.txt', {'user': user})
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        send_mail(subject, message, from_email, recipient_list)

        # Notify Admin
        admin_subject = f"New Station Activation: {station.name}"
        admin_message = f"New station activated!\n\nUser: {user.first_name} {user.last_name} ({user.email})\nStation: {station.name}\nContact: {station.contact_number}\nTime: {datetime.datetime.now()}"
        send_mail(admin_subject, admin_message, from_email, ['admin@wrsms.online'])
    except Exception as e:
        print(f"Email Error: {e}")

    # 8. Login and Redirect
    # We need to authenticate. Since we have the user object:
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    return redirect('wrsm_app:setup-wizard') # Redirect to setup wizard
