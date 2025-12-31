from django.test import TestCase
from wrsm_app.models import Station

class StationModelTest(TestCase):
    def test_str_without_branch(self):
        station = Station.objects.create(name="Main Station")
        self.assertEqual(str(station), "Main Station")

    def test_str_with_branch(self):
        station = Station.objects.create(name="Main Station", branch="Downtown")
        self.assertEqual(str(station), "Main Station [Downtown]")
