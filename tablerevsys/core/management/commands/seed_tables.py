from django.core.management.base import BaseCommand
from core.models import Branch, Table

class Command(BaseCommand):
    help = 'Seeds the database with initial branches and tables'

    def handle(self, *args, **kwargs):
        Table.objects.all().delete()
        Branch.objects.all().delete()
        
        branch_names = [
            "The Bellington at The Fort",
            "The Bellington at The Triangle",
            "The Bellington at The Podium"
        ]

        branch_codes = {
            'The Bellington at The Fort': 'F',
            'The Bellington at The Triangle': 'T',
            'The Bellington at The Podium': 'P',
        }

        table_layout = {
            'A': (2, 11),
            'B': (4, 10),
            'C': (6, 5),
            'D': (8, 1),
            }

        for branch in Branch.objects.all():
            prefix = branch_codes.get(branch.name)
            if not prefix:
                print(f"Skipping unknown branch: {branch.name}")
                continue

            for table_type, (capacity, count) in table_layout.items():
                for i in range(1, count + 1):
                    code = f"{prefix}{table_type}{i}" 
                    
                    if Table.objects.filter(code=code).exists():
                        continue
                    
                    Table.objects.create(branch=branch, code=code, capacity=capacity)
