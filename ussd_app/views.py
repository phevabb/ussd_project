from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def ussd(request):
    # Get the USSD request parameters
    session_id = request.POST.get('sessionId')
    phone_number = request.POST.get('phoneNumber')
    text = request.POST.get('text')

    # Logic to handle the USSD session
    if text == "":
        response = "CON Welcome to My USSD Service\n"
        response += "1. Option 1\n"
        response += "2. Option 2\n"
    elif text == "1":
        response = "CON You selected Option 1\n"
        response += "Enter your input:"
    elif text == "2":
        response = "CON You selected Option 2\n"
        response += "Enter your input:"
    else:
        response = "END Invalid selection."

    return HttpResponse(response, content_type='text/plain')



