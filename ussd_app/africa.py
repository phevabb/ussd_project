import africastalking
from django.conf import settings

# Initialize Africa's Talking
africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)

