from django.db import models

class ShoppingList(models.Model):
    session_id = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    list_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True, default='processing order')

    def __str__(self):
        return self.list_name or "Unnamed List"

class UserInfo(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    digital_address = models.CharField(max_length=255,null=True, blank=True)
    area_name = models.CharField(max_length=255,null=True, blank=True)
    payment_preference = models.CharField(max_length=255,null=True, blank=True)



from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.crypto import get_random_string

class Passenger(models.Model):
    """Equivalent to your old UserInfo, mapped by phone number."""
    name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, unique=True)  # USSD identity
    digital_address = models.CharField(max_length=255, null=True, blank=True)
    area_name = models.CharField(max_length=255, null=True, blank=True)
    payment_preference = models.CharField(
        max_length=50, null=True, blank=True,
        choices=[("MTN MoMo", "MTN MoMo"), ("Vodafone Cash", "Vodafone Cash")]
    )

    def __str__(self):
        return self.name or self.phone_number


class Route(models.Model):
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=10.00)

    class Meta:
        unique_together = ("origin", "destination")

    def __str__(self):
        return f"{self.origin} ➡ {self.destination}"


class Trip(models.Model):
    MORNING = "MORN"
    EVENING = "EVE"
    WINDOW_CHOICES = [(MORNING, "Morning"), (EVENING, "Evening")]

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="trips")
    service_date = models.DateField(default=timezone.localdate)
    window = models.CharField(max_length=4, choices=WINDOW_CHOICES)
    departure_time = models.TimeField()
    capacity = models.PositiveIntegerField(default=36, validators=[MinValueValidator(1), MaxValueValidator(100)])

    class Meta:
        unique_together = ("route", "service_date", "window", "departure_time")

    def __str__(self):
        date = self.service_date.strftime("%Y-%m-%d")
        t = self.departure_time.strftime("%H:%M")
        return f"{self.route} | {date} {t} ({self.get_window_display()})"

    def taken_seats(self):
        now = timezone.now()
        qs = Reservation.objects.filter(
            trip=self,
            status__in=[Reservation.HELD, Reservation.CONFIRMED]
        ).filter(
            models.Q(hold_expires_at__isnull=True) | models.Q(hold_expires_at__gt=now)
        )
        return set(qs.values_list("seat_number", flat=True))

    def available_seats(self):
        taken = self.taken_seats()
        return [i for i in range(1, self.capacity + 1) if i not in taken]


def generate_reservation_code():
    # Example: 7-char uppercase alphanumeric, like ADD4525
    return get_random_string(7, allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ23456789")


class Reservation(models.Model):
    HELD = "HELD"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    STATUS_CHOICES = [(HELD, "Held"), (CONFIRMED, "Confirmed"), (CANCELLED, "Cancelled")]

    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE, related_name="reservations")
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="reservations")
    seat_number = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    reservation_code = models.CharField(max_length=12, default=generate_reservation_code, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=HELD)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("trip", "seat_number")  # prevents double-booking

    def __str__(self):
        return f"{self.reservation_code} | Seat {self.seat_number} | {self.status}"


class Payment(models.Model):
    MTN = "MTN MoMo"
    VODA = "Vodafone Cash"
    PROVIDER_CHOICES = [(MTN, "MTN MoMo"), (VODA, "Vodafone Cash")]

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STATUS_CHOICES = [(PENDING, "Pending"), (SUCCESS, "Success"), (FAILED, "Failed")]

    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name="payment")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    external_reference = models.CharField(max_length=255, blank=True, null=True)  # PSP txn id
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)