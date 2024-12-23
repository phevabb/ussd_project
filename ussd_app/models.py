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

