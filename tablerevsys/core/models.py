from django.db import models
from django.utils import timezone
from datetime import timedelta
import uuid 

# Create your models here.

class Branch(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()

    def __str__(self):
        return self.name

class Table(models.Model):
    TABLE_TYPES = (
        ('A', '2-seater'),
        ('B', '4-seater'),
        ('C', '6-seater'),
        ('D', '8-seater'),
    )

    code = models.CharField(max_length=5, unique=True)
    table_type = models.CharField(max_length=1, choices=TABLE_TYPES)
    capacity = models.PositiveIntegerField()
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='tables')
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.branch.name} - Table {self.code}"

class Reservation(models.Model):
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE)
    table = models.ForeignKey('Table', on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    date = models.DateField()
    time = models.TimeField()

    adults = models.PositiveIntegerField(default=0)
    seniors = models.PositiveIntegerField(default=0)
    children = models.PositiveIntegerField(default=0)
    babies = models.PositiveIntegerField(default=0)

    purpose = models.CharField(max_length=100, blank=True)
    allergies = models.TextField(blank=True)
    requests = models.TextField(blank=True)

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No‑Show'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

 
    created_at = models.DateTimeField(auto_now_add=True)
    paymongo_session_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    paid = models.BooleanField(default=False)

    cancel_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=False)

    class Meta:
        unique_together = ('table', 'date', 'time')

    def __str__(self):
        return f"{self.customer_name} - {self.table.code} on {self.date} at {self.time}"

    def reservation_end_time(self):
        return (timezone.datetime.combine(self.date, self.time) + timedelta(hours=2)).time()

    def total_guests(self):
        return self.adults + self.seniors + self.children + self.babies

    def effective_guests(self):
        return max(0, self.total_guests() - 1) if self.babies >= 1 else self.total_guests()

class WaitlistEntry(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    phone = models.CharField(max_length=20)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    guest_total = models.PositiveIntegerField()
    preferred_time = models.TimeField()
    date = models.DateField()
    purpose = models.CharField(max_length=100, blank=True)
    allergies = models.TextField(blank=True)
    requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} ({self.guest_total} guests) on {self.date} at {self.preferred_time}"
