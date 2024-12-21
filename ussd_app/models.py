from django.db import models

class ShoppingList(models.Model):
    session_id = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    list_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.list_name or "Unnamed List"
