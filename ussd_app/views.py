from http.client import responses

from django.http import HttpResponse
from.models import ShoppingList, UserInfo
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import uuid


def create_order_id():
    return f"{uuid.uuid4().hex[:8].upper()}"

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
    global obj_to_edit
    session_id = request.POST.get('sessionId')
    phone_number = request.POST.get('phoneNumber')
    text = request.POST.get('text')

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

        # Create New Shopping List
        if text == "1":
            response = "CON Enter list name :\n"
            response += "eg. rice 4kg, fish 3kg, milk 1tin"
            update_session_state(session_id, "WAITING_FOR_LIST_NAME")
            return HttpResponse(response, content_type="text/plain")

        # Use Previous List
        elif text == "2":
            obj = ShoppingList.objects.filter(phone_number=phone_number).first()
            if obj:
                all_lists = ShoppingList.objects.filter(phone_number=phone_number)
                if len(all_lists) >= 3:
                    last_3_items = all_lists.order_by('-created_at')[:3]  # Get the last 3 items based on ID
                    response = "CON Last 3 shopping lists.\n"
                    response += f"1. {last_3_items[0]}\n"
                    response += f"2. {last_3_items[1]}\n"
                    response += f"3. {last_3_items[2]}\n"
                    update_session_state(session_id, "PREVIOUS_LIST")
                    return HttpResponse(response, content_type="text/plain")
                elif len(all_lists) == 2:
                    last_2_items = all_lists.order_by('-created_at')[:2]
                    response = "CON Last 2 shopping lists.\n"
                    response += f"1. {last_2_items[0]}\n"
                    response += f"2. {last_2_items[1]}\n"
                    update_session_state(session_id, "PREVIOUS_LIST")
                    return HttpResponse(response, content_type="text/plain")
                else:
                    last_1_items = all_lists.order_by('-created_at')[:1]
                    response = "CON Last  shopping lists.\n"
                    response += f"1. {last_1_items[0]}\n"
                    update_session_state(session_id, "PREVIOUS_LIST")
                    return HttpResponse(response, content_type="text/plain")
            else:
                response = "END No lists Available"
                return HttpResponse(response, content_type="text/plain")
        # Track Order
        elif text == "3":
            update_session_state(session_id, "ORDER_ID")
            response = "CON please enter your Order_ID:\n"
            return HttpResponse(response, content_type="text/plain")
        # Manage Account
        elif text == "4":
            update_session_state(session_id, "ACCOUNT")
            response = "CON Please update your Account:\n"
            response += "1. Update Delivery Address\n"
            response += "2. Change Payment Preference\n"
            response += "3. View Profile\n"
            return HttpResponse(response, content_type="text/plain")




    elif state == "ACCOUNT":
        update_session_state(session_id, "DIGITAL_ADDRESS_ENTERED")
        full_text = text.split("*")
        actual_option = full_text[1]
        if actual_option == "1":

            response = "CON Enter your new Digital Address:"
            return HttpResponse(response, content_type="text/plain")

    elif state == "DIGITAL_ADDRESS_ENTERED":
        update_session_state(session_id, "AREA_NAME_ENTERED")
        all_text = text.split("*", 2)
        digital_address = all_text[2]
        obj = UserInfo.objects.filter(phone_number=phone_number).first()
        if obj:
            obj.digital_address = digital_address
            obj.save()
        else:
            UserInfo.objects.create(
                digital_address=digital_address,
                phone_number=phone_number,
            )

        response = "CON Please Enter Area Name:\n"
        return HttpResponse(response, content_type="text/plain")

    elif state == "AREA_NAME_ENTERED":
        print(f"this is the area name{text}")
        all_text = text.split("*", 3)
        area_name = all_text[3]
        obj = UserInfo.objects.filter(phone_number=phone_number).first()
        obj.area_name = area_name
        obj.save()
        response = "END Success! Address updated:\n"
        return HttpResponse(response, content_type="text/plain")




    elif state == "ORDER_ID":
        all_text = text.split("*")
        id_in_text = all_text[1]
        obj = ShoppingList.objects.filter(order_id=id_in_text).first()
        if obj:
            if obj.phone_number == phone_number:
                response = f"END Order Status: {obj.status}"
                return HttpResponse(response, content_type="text/plain")
            else:
                response = "END phone numbers do not match"
                return HttpResponse(response, content_type="text/plain")
        else:
            response = "END Invalid Order ID"
            return HttpResponse(response, content_type="text/plain")


    elif state == "PREVIOUS_LIST":
        update_session_state(session_id, "ORDER_THIS_LIST")

        selected_option = text.split('*')
        actual_option =selected_option[1]

        all_lists = ShoppingList.objects.filter(phone_number=phone_number)
        last_3_items = all_lists.order_by('-created_at')[:3]  # Get the last 3 items based on ID

        if actual_option == "1":

            response = "CON Order this list? .\n"
            response += f"{last_3_items[0]}\n"
            update_session_state(session_id, "ORDER_THIS_LIST")
            response += "1. Confirm \n"
            response += "2. Edit \n"
            response += "3. Cancel"
            return HttpResponse(response, content_type="text/plain")

        elif actual_option == "2":

            response = "CON Order this list? .\n"
            response += f"{last_3_items[1]}\n"
            response += "1. Confirm \n"
            response += "2. Edit \n"
            response += "3. Cancel"
            return HttpResponse(response, content_type="text/plain")


        elif actual_option == "3":

            response = "CON Order this list? .\n"
            response += f"{last_3_items[2]}\n"
            response += "1. Confirm \n"
            response += "2. Edit \n"
            response += "3. Cancel"
            return HttpResponse(response, content_type="text/plain")


    elif state == "ORDER_THIS_LIST":
        update_session_state(session_id, "THIS_LIST_ORDERED")

        all_lists = ShoppingList.objects.filter(phone_number=phone_number)
        last_3_items = all_lists.order_by('-created_at')[:3]

        number = text.split('*', 2)
        actual_option =number[-1]

        if actual_option == "1":
            chosen_list = text.split('*', 3)
            actual_chosen_list = chosen_list[1]
            if actual_chosen_list == "1":
                ShoppingList.objects.create(
                    session_id=session_id,
                    phone_number=phone_number,
                    list_name=last_3_items[0],
                    order_id=create_order_id()
                )
                obj = ShoppingList.objects.get(session_id=session_id)
                response = "END List Ordered Successfully .\n"
                response += "Order ID:\n"
                response += f"{obj.order_id}\n"
                response += "Please write it down \n"
                return HttpResponse(response, content_type="text/plain")
            elif actual_chosen_list == "2":
                ShoppingList.objects.create(
                    session_id=session_id,
                    phone_number=phone_number,
                    list_name=last_3_items[1],
                    order_id=create_order_id()
                )
                obj = ShoppingList.objects.get(session_id=session_id)
                response = "END List Ordered Successfully .\n"
                response += "Order ID:\n"
                response += f"{obj.order_id}\n"
                response += "Please write it down \n"
                return HttpResponse(response, content_type="text/plain")
            elif actual_chosen_list == "3":
                ShoppingList.objects.create(
                    session_id=session_id,
                    phone_number=phone_number,
                    list_name=last_3_items[2],
                    order_id=create_order_id()
                )
                obj = ShoppingList.objects.get(session_id=session_id)
                response = "END List Ordered Successfully .\n"
                response += "Order ID:\n"
                response += f"{obj.order_id}\n"
                response += "Please write it down \n"
                return HttpResponse(response, content_type="text/plain")
            else:
                response = "END Invalid selection"
                return HttpResponse(response)

        # editing a list
        elif actual_option == "2":
            update_session_state(session_id, "CONTAINS_EDITED_LIST")
            selected_option = text.split('*', 3)
            item_to_edit =selected_option[1]
            if item_to_edit == "1":
                obj_to_edit = last_3_items[0]
            if item_to_edit == "2":
                obj_to_edit = last_3_items[1]
            if item_to_edit == "3":
                obj_to_edit = last_3_items[2]


            response = "CON Please edit list and order .\n"
            response += f"({obj_to_edit}).\n"
            response += f"Edit list: \n"
            return HttpResponse(response, content_type="text/plain")


        elif actual_option == "3":
            ShoppingList.objects.filter(session_id=session_id).delete()
            response = "END List Order Canceled .\n"
            return HttpResponse(response, content_type="text/plain")
        else:
            response = "END Invalid input.\n"
            return HttpResponse(response, content_type="text/plain")

    elif state == "CONTAINS_EDITED_LIST":
        print(f"text is here: {text}")
        all_text = text.split('*', 3)
        new_list = all_text[3]
        ShoppingList.objects.create(
            session_id=session_id,
            phone_number=phone_number,
            list_name=new_list,
            order_id=create_order_id()
        )
        obj = ShoppingList.objects.get(session_id=session_id)
        order_id=obj.order_id
        response = "END Order Placed Successfully!  .\n"
        response += f"Order ID: {order_id}\n"
        response += f"Please write it down \n"
        return HttpResponse(response, content_type="text/plain")



    elif state == "EDITED_PREVIOUS_LIST":

        edited_stuff = text.split('*', 3)

        final_stuff = edited_stuff[3]

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
                list_name=items,
                order_id=create_order_id()
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
        obj= get_object_or_404(ShoppingList, session_id=session_id)
        order_id = obj.order_id

        inputs = text.split('*')
        selected_option = inputs[-1]
        if selected_option == "1":
            response = "END Items Added Successfully:\n"
            response += f"your order id: \n"
            response += f"{order_id} \n"
            response += "Please write it down \n"
            return HttpResponse(response, content_type="text/plain")

        elif selected_option == "2":
            print(f"check text: {text}")
            all_text = text.split('*', 2)
            actual_text = all_text[1]

            response = "CON Edit your list and Order :\n"
            response += f"({actual_text})\n"
            response += f"Edit list: \n"
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
            order_id=obj.order_id
            response = "END List updated & Ordered successfully! .\n"
            response += f"Order ID: {order_id}\n"
            response += f"please keep order_ID safe\n"
            return HttpResponse(response, content_type="text/plain")


























