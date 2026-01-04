from django.core.management.base import BaseCommand
from django.db.models import Count
from wrsm_app.models import Customer
import sys

class Command(BaseCommand):
    help = 'Fixes duplicate customer names per station by appending a suffix.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the deduplication without making changes.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("Running in DRY RUN mode. No changes will be saved."))

        # Find duplicates: Group by station and name, filter where count > 1
        duplicates = (
            Customer.objects.values('station', 'name')
            .annotate(name_count=Count('id'))
            .filter(name_count__gt=1)
        )

        total_duplicates_groups = duplicates.count()
        self.stdout.write(f"Found {total_duplicates_groups} groups of duplicate customers.")

        for entry in duplicates:
            station_id = entry['station']
            name = entry['name']
            
            # Fetch all customers with this station and name, ordered by ID (oldest first)
            customers = Customer.objects.filter(station_id=station_id, name=name).order_by('id')
            
            # Skip the first one (keep original)
            customers_to_update = customers[1:]
            
            self.stdout.write(f"Processing duplicates for '{name}' in station ID {station_id}: {len(customers_to_update)} to rename.")

            for i, customer in enumerate(customers_to_update, start=1):
                new_name = f"{name} ({i})"
                
                # Ensure the new name doesn't conflict (edge case where 'Name (1)' already exists)
                while Customer.objects.filter(station_id=station_id, name=new_name).exists():
                    i += 1
                    new_name = f"{name} ({i})"

                if dry_run:
                     self.stdout.write(f"  [DRY RUN] Would rename ID {customer.id} from '{customer.name}' to '{new_name}'")
                else:
                    old_name = customer.name
                    customer.name = new_name
                    customer.save()
                    self.stdout.write(self.style.SUCCESS(f"  Renamed ID {customer.id} from '{old_name}' to '{new_name}'"))

        self.stdout.write(self.style.SUCCESS("Deduplication complete."))
