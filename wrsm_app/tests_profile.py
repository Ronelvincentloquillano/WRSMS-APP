from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from wrsm_app.models import Station, Profile

class ProfilePageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.station = Station.objects.create(name='Test Station')
        self.profile = Profile.objects.create(user=self.user, station=self.station)
        
        # Create a group (role)
        self.group = Group.objects.create(name='Station Manager')
        self.user.groups.add(self.group)
        
        self.client.login(username='testuser', password='password')

    def test_profile_page_displays_role(self):
        url = reverse('wrsm_app:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Check if the role name is in the response
        self.assertContains(response, 'User Role')
        self.assertContains(response, 'Station Manager')
