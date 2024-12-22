from http.client import responses

from django.http import HttpResponse
from.models import ShoppingList
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import urllib.parse


from django.core.cache import cache

# Default timeout for session states (in seconds)
SESSION_TIMEOUT = 900  # 5 minutes

def get_session_state(session_id):
    """
    Retrieve the session state for a given session ID.
    Defaults to 'START' if no state is found.
    """
    return cache.get(session_id, "START")

def update_session_state(session_id, state):
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
            all_lists = ShoppingList.objects.filter(phone_number=phone_number)
            last_3_items = all_lists.order_by('-id')[:3]  # Get the last 3 items based on ID

            response = "CON Last 3 shopping lists.\n"
            response += f"1. {last_3_items[0]}\n"
            response += f"2. {last_3_items[1]}\n"
            response += f"3. {last_3_items[2]}\n"
            update_session_state(session_id, "PREVIOUS_LIST")

            return HttpResponse(response, content_type="text/plain")
        else:
            response = "END Invalid input.\n"
            return HttpResponse(response, content_type="text/plain")

    elif state == "PREVIOUS_LIST":
        update_session_state(session_id, "ORDER_THIS_LIST")
        selected_option = text.split('*')

        actual_option =selected_option[1]
        all_lists = ShoppingList.objects.filter(phone_number=phone_number)
        last_3_items = all_lists.order_by('created_at')[:3]  # Get the last 3 items based on ID

        if actual_option == "1":
            ShoppingList.objects.create(
                session_id=session_id,
                phone_number=phone_number,
                list_name=last_3_items[0]
            )
            response = "CON Order this list? .\n"
            response += f"{last_3_items[0]}\n"
            update_session_state(session_id, "ORDER_THIS_LIST")
            response += "1. Confirm \n"
            response += "2. Edit \n"
            response += "3. Cancel"
            return HttpResponse(response, content_type="text/plain")

        elif actual_option == "2":
            ShoppingList.objects.create(
                session_id=session_id,
                phone_number=phone_number,
                list_name=last_3_items[1]
            )
            response = "CON Order this list? .\n"
            response += f"{last_3_items[1]}\n"
            response += "1. Confirm \n"
            response += "2. Edit \n"
            response += "3. Cancel"
            return HttpResponse(response, content_type="text/plain")


        elif actual_option == "3":
            ShoppingList.objects.create(
                session_id=session_id,
                phone_number=phone_number,
                list_name=last_3_items[2]
            )
            response = "CON Order this list? .\n"
            response += f"{last_3_items[2]}\n"
            response += "1. Confirm \n"
            response += "2. Edit \n"
            response += "3. Cancel"
            return HttpResponse(response, content_type="text/plain")


    elif state == "ORDER_THIS_LIST":
        number = text.split('*', 2)
        actual_option =number[-1]

        if actual_option == "1":
            response = "END List Ordered Successfully .\n"
            return HttpResponse(response, content_type="text/plain")

        elif actual_option == "2":
            update_session_state(session_id, "EDITED_PREVIOUS_LIST")
            response = "CON Please make changes .\n"
            response += "eg. rice 4kg, fish 3kg, milk 1tin.\n"
            return HttpResponse(response, content_type="text/plain")


        elif actual_option == "3":
            ShoppingList.objects.filter(session_id=session_id).delete()
            response = "END List Order Canceled .\n"
            return HttpResponse(response, content_type="text/plain")
        else:
            response = "END Invalid input.\n"
            return HttpResponse(response, content_type="text/plain")

    elif state == "EDITED_PREVIOUS_LIST":
        print(f"the current state is {state}")
        edited_stuff = text.split('*', 3)
        print(f"the edited stuff is {edited_stuff}")
        final_stuff = edited_stuff[3]
        print(f"the final stuff is {final_stuff}")
        obj = get_object_or_404(ShoppingList, session_id=session_id)
        obj.list_name = final_stuff
        obj.save()
        response = "END Selected List Successfully updated .\n"
        return HttpResponse(response, content_type="text/plain")




    elif state == "WAITING_FOR_LIST_NAME":

        inputs = text.split('*')
        if len(inputs) > 1:
            items = inputs[1]
            ShoppingList.objects.create(
                session_id=session_id,
                phone_number=phone_number,
                list_name=items
                )
        else:
            response = "END list not made.\n"
            return HttpResponse(response, content_type="text/plain")
        response = f"CON Your List:\n"
        update_session_state(session_id, "DISPLAY_LIST")
        response += f"Your List:({items}).\n"
        response += "1. Confirm and Save\n"
        response += "2. Edit\n"
        response += "3. Cancel list\n"
        return HttpResponse(response, content_type="text/plain")

    elif state == "DISPLAY_LIST":

        inputs = text.split('*')
        selected_option = inputs[-1]
        if selected_option == "1":

            response = "END Items saved :\n"
            return HttpResponse(response, content_type="text/plain")

        elif selected_option == "2":

            response = "CON Edit list :\n"
            response += "eg. rice 4kg, fish 3kg, milk 1tin"
            update_session_state(session_id, "LIST_EDIT")
            return HttpResponse(response, content_type="text/plain")
        elif selected_option == "3":
            ShoppingList.objects.filter(session_id=session_id).delete()
            response = "END list successfully deleted :\n"
            return HttpResponse(response, content_type="text/plain")



    elif state == "LIST_EDIT":

        inputs = text.split('*', 3)
        if len(inputs) > 1:
            updated_items = inputs[3]            # Update the list name for the object with the matching session_id
            obj = get_object_or_404(ShoppingList, session_id=session_id)

            obj.list_name = updated_items
            obj.save()
            response = "END List updated successfully.\n"
            return HttpResponse(response, content_type="text/plain")
























    elif text == "1":
        return create_new_shopping_list_1(payload)


    elif text == "2":
        response = "CON last three lists:\n"
        response += "1. [List Date: 12/12/2024] \n"
        response += "2. [List Date: 10/12/2024] \n"
        response += "3. [List Date: 08/12/2024] \n"

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



