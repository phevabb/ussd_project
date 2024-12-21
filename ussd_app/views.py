from http.client import responses

from django.http import HttpResponse
from.models import ShoppingList
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import urllib.parse


from django.core.cache import cache

# Default timeout for session states (in seconds)
SESSION_TIMEOUT = 300  # 5 minutes

def get_session_state(session_id):
    """
    Retrieve the session state for a given session ID.
    Defaults to 'START' if no state is found.
    """
    return cache.get(session_id, "START")

def update_session_state(session_id, state, extra_data=None):

    if extra_data is None:
        extra_data = {}

    cache.set(session_id, state, timeout=SESSION_TIMEOUT)






@csrf_exempt
def ussd(request):

    # Get the USSD request parameters
    session_id = request.POST.get('sessionId')
    phone_number = request.POST.get('phoneNumber')
    text = request.POST.get('text')
    payload = request.POST.dict()

    # check the current state of the session.
    state = get_session_state(session_id)

    if state == "START":
        if text == "":
            response = "CON Welcome to Friend's Market\n"
            response += "1. Create New Shopping List\n"
            response += "2. Use Previous List\n"
            response += "3. Track Order\n"
            response += "4. Manage Account\n"
            response += "5. Help\n"
            response += "0. Exit\n"
            update_session_state(session_id, "MENU_SELECTED")
            return HttpResponse(response)
        else:
            response = "Invalid selection"
            return HttpResponse(response)

    elif state == "MENU_SELECTED":
        if text == "1":
            response = "CON Enter list name :\n"
            response += "eg. rice 4kg, fish 3kg, milk 1tin"
            update_session_state(session_id, "WAITING_FOR_LIST_NAME")
            return HttpResponse(response, content_type="text/plain")
        elif text == "2":
            response = "END Viewing shopping lists is not implemented yet.\n"
            return HttpResponse(response, content_type="text/plain")
        else:
            response = "END Invalid input.\n"
            return HttpResponse(response, content_type="text/plain")

    elif state == "WAITING_FOR_LIST_NAME":

        inputs = text.split('*')
        if len(inputs) > 1:
            user_list = inputs[1]  # This contains the shopping list
        else:
            user_list = text

        response = f"CON Your List:\n"
        update_session_state(session_id, "DISPLAY_LIST", {"user_list": user_list})
        response += f"Your List:({user_list}).\n"
        response += "1. Confirm and Save\n"
        response += "3. Edit\n"
        response += "4. Cancel list\n"
        return HttpResponse(response, content_type="text/plain")

    elif state == "DISPLAY_LIST":
        session_data = get_session_state(session_id)
        user_list = session_data.get("user_list", "")
        print(f"Reach here .........State: {state}, Text: {text} user_list: {user_list}")

        if text == "1":
            ShoppingList.objects.create(
                session_id=session_id,
                phone_number=phone_number,
                list_name=user_list
            )
            update_session_state(session_id, "ITEMS_ADDED")
            response = f"END Your Items Added Successfully:\n"
            return HttpResponse(response, content_type="text/plain")




















    elif text == "1":
        return create_new_shopping_list_1(payload)


    elif text == "2":
        response = "CON last three lists:\n"
        response += "1. [List Date: 12/12/2024] \n"
        response += "2. [List Date: 10/12/2024] \n"
        response += "3. [List Date: 08/12/2024] \n"
        response += "0. Back \n"
    else:
        response = "END Invalid selection."

    return HttpResponse(response, content_type='text/plain')


def create_new_shopping_list_1(payload):
    # Process payload
    session_id = payload.get('sessionId')
    phone_number = payload.get('phoneNumber')
    text = payload.get('text')

    # Example response
    response = "CON Enter the name of your shopping list:\n"
    response += "Enter your input \n"
    input_data = response.data

    return HttpResponse(response, content_type="text/plain")



