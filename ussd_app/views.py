from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import Passenger, Route, Trip, Reservation, Payment

SESSION_TIMEOUT = 15 * 60  # 15 minutes
SEAT_PAGE_SIZE = 4         # show 4 seats per page like your example

def get_state(session_id, default="START"):
    return cache.get(f"{session_id}:state", default)

def set_state(session_id, state):
    cache.set(f"{session_id}:state", state, SESSION_TIMEOUT)

def get_data(session_id):
    return cache.get(f"{session_id}:data", {})

def set_data(session_id, data):
    cache.set(f"{session_id}:data", data, SESSION_TIMEOUT)

def end(text):
    return HttpResponse(f"END {text}", content_type="text/plain")

def cont(text):
    return HttpResponse(f"CON {text}", content_type="text/plain")


def ensure_passenger(phone_number):
    p, _ = Passenger.objects.get_or_create(phone_number=phone_number)
    return p


def ensure_trip(route_id, window, dep_time_str):
    """Get or create today's trip for route/window/time."""
    route = get_object_or_404(Route, id=route_id)
    service_date = timezone.localdate()
    # Parse simple HH:MM string
    hour, minute = map(int, dep_time_str.split(":"))
    from datetime import time as t
    return Trip.objects.get_or_create(
        route=route,
        service_date=service_date,
        window=window,
        departure_time=t(hour, minute),
        defaults={"capacity": 36}
    )[0]


def list_routes_text():
    routes = Route.objects.all().order_by("id")
    lines = []
    for idx, r in enumerate(routes, start=1):
        lines.append(f"{idx}. {r.origin} ➡ {r.destination}")
    return "\n".join(lines), list(routes)


def list_times_text(window):
    # Mirror your example
    times = ["05:30", "06:00", "06:30"]
    title = "Select Departure Time" if window == Trip.MORNING else "Select Departure Time"
    lines = [title]
    for i, t in enumerate(times, start=1):
        lines.append(f"{i}. {t}")
    return "\n".join(lines), times


def format_confirm_screen(route, time_str, seat, price):
    return (
        "Confirm Booking\n"
        f"Route: {route.origin} – {route.destination}\n"
        f"Time: {time_str}\n"
        f"Seat: {seat}\n"
        f"Price: {int(price) if price == int(price) else price}\n"
        "1. Confirm & Pay (MoMo)\n"
        "2. Cancel"
    )


@csrf_exempt
def ussd(request):
    session_id = request.POST.get("sessionId")
    phone_number = request.POST.get("phoneNumber")
    text = request.POST.get("text") or ""
    steps = text.split("*") if text else []
    last = steps[-1] if steps else ""

    state = get_state(session_id)
    data = get_data(session_id)

    # START / MAIN MENU
    if state == "START":
        set_state(session_id, "MAIN_MENU")
        menu = (
            "Welcome to Smart Shuttle\n"
            "1. Morning & Evening Shuttle Services\n"
            "2. Check Schedule\n"
            "3. My Reservation\n"
            "4. Cancel Reservation\n"
            "5. Help"
        )
        return cont(menu)

    # MAIN MENU HANDLER
    if state == "MAIN_MENU":
        if last == "1":
            set_state(session_id, "BOOK_MENU")
            return cont(
                "1. Book Morning Shuttle Service\n"
                "2. Book Evening Shuttle Service"
            )
        elif last == "2":
            set_state(session_id, "CHECK_SCHEDULE")
            # Show routes, then times
            routes_txt, _ = list_routes_text()
            return cont("Select Route\n" + routes_txt)
        elif last == "3":
            # My Reservation (last confirmed)
            passenger = ensure_passenger(phone_number)
            r = (Reservation.objects
                 .filter(passenger=passenger, status=Reservation.CONFIRMED)
                 .order_by("-created_at").first())
            if not r:
                return end("No confirmed reservation found.")
            trip = r.trip
            t = trip.departure_time.strftime("%H:%M")
            return end(
                "Ticket Details:\n"
                f"{trip.route.origin} - {trip.route.destination}\n"
                f"Time: {t}\n"
                f"Seat: {r.seat_number}\n"
                f"Reservation Code: {r.reservation_code}"
            )
        elif last == "4":
            set_state(session_id, "CANCEL_FLOW_ROUTE")
            routes_txt, _ = list_routes_text()
            return cont("Cancel Reservation\nSelect Route\n" + routes_txt)
        elif last == "5":
            return end("Help: Dial *100*224# to book. For support call 030 xxxxxxx.")
        else:
            return end("Invalid selection.")

    # BOOK MENU (Morning/Evening)
    if state == "BOOK_MENU":
        if last == "1":
            data.update({"window": Trip.MORNING})
        elif last == "2":
            data.update({"window": Trip.EVENING})
        else:
            return end("Invalid selection.")
        set_data(session_id, data)
        set_state(session_id, "SELECT_ROUTE")
        routes_txt, _ = list_routes_text()
        return cont("Select Route\n" + routes_txt)

    # SELECT ROUTE
    if state == "SELECT_ROUTE":
        try:
            idx = int(last) - 1
        except ValueError:
            return end("Invalid selection.")

        routes_txt, routes = list_routes_text()
        if not (0 <= idx < len(routes)):
            return end("Invalid selection.")

        route = routes[idx]
        data.update({"route_id": route.id})
        set_data(session_id, data)

        set_state(session_id, "SELECT_TIME")
        times_txt, _ = list_times_text(data["window"])
        return cont(times_txt)

    # SELECT TIME
    if state == "SELECT_TIME":
        times_txt, times = list_times_text(data["window"])
        try:
            idx = int(last) - 1
        except ValueError:
            return end("Invalid selection.")
        if not (0 <= idx < len(times)):
            return end("Invalid selection.")

        time_str = times[idx]
        data.update({"time_str": time_str})
        set_data(session_id, data)

        # Build available seats & show first page
        trip = ensure_trip(data["route_id"], data["window"], time_str)
        av = trip.available_seats()
        if not av:
            set_state(session_id, "MAIN_MENU")
            return end("Sorry, this trip is fully booked.")

        data["seat_page"] = 0
        data["available_seats"] = av  # cache now for paging
        set_data(session_id, data)
        set_state(session_id, "SELECT_SEAT")
        return cont(render_seat_page(data))

    # SELECT SEAT (with paging)
    if state == "SELECT_SEAT":
        av = data.get("available_seats", [])
        page = data.get("seat_page", 0)
        page_count = (len(av) + SEAT_PAGE_SIZE - 1) // SEAT_PAGE_SIZE
        start = page * SEAT_PAGE_SIZE
        end_i = start + SEAT_PAGE_SIZE
        current_slice = av[start:end_i]
        options_count = len(current_slice)

        try:
            choice = int(last)
        except ValueError:
            return end("Invalid input.")

        # Next page option
        if options_count and choice == options_count + 1:
            if page + 1 < page_count:
                data["seat_page"] = page + 1
                set_data(session_id, data)
                return cont(render_seat_page(data))
            else:
                return end("No more seats.")
        # Seat picked
        elif 1 <= choice <= options_count:
            seat_number = current_slice[choice - 1]
            data["seat_number"] = seat_number
            set_data(session_id, data)

            # Prepare confirmation screen
            route = Route.objects.get(id=data["route_id"])
            price = route.price
            confirm_text = format_confirm_screen(route, data["time_str"], seat_number, price)
            set_state(session_id, "CONFIRM_BOOKING")
            return cont(confirm_text)
        else:
            return end("Invalid selection.")

    # CONFIRM_BOOKING
    if state == "CONFIRM_BOOKING":
        if last == "1":  # Confirm & Pay
            passenger = ensure_passenger(phone_number)
            route = Route.objects.get(id=data["route_id"])
            trip = ensure_trip(data["route_id"], data["window"], data["time_str"])
            seat_number = data["seat_number"]
            hold_for = timezone.now() + timedelta(minutes=5)

            # Atomic hold of the seat
            try:
                with transaction.atomic():
                    # Double-check seat availability at commit time
                    if seat_number in trip.taken_seats():
                        set_state(session_id, "MAIN_MENU")
                        return end("Seat just got taken. Please try another seat.")
                    res = Reservation.objects.create(
                        passenger=passenger,
                        trip=trip,
                        seat_number=seat_number,
                        amount=route.price,
                        status=Reservation.HELD,
                        hold_expires_at=hold_for,
                    )
                    # Create a pending payment (provider could depend on passenger preference)
                    provider = passenger.payment_preference or Payment.MTN
                    Payment.objects.create(
                        reservation=res,
                        provider=provider,
                        amount=route.price,
                        status=Payment.PENDING
                    )
            except Exception:
                return end("Could not place hold. Please try again.")

            # TODO: Integrate MoMo push here (PSP API call) and redirect to callback.
            # For USSD, we end the session and send an SMS on payment success.
            set_state(session_id, "MAIN_MENU")
            return end(
                "Payment prompt sent. Please approve on your phone.\n"
                "You will receive an SMS with your ticket after successful payment."
            )

        elif last == "2":
            set_state(session_id, "MAIN_MENU")
            return end("Reservation cancelled.")
        else:
            return end("Invalid selection.")

    # CHECK SCHEDULE
    if state == "CHECK_SCHEDULE":
        # flow: route -> time -> show available seats count
        # If route not chosen yet:
        if "sched_route_id" not in data:
            try:
                idx = int(last) - 1
            except ValueError:
                return end("Invalid selection.")
            routes_txt, routes = list_routes_text()
            if not (0 <= idx < len(routes)):
                return end("Invalid selection.")
            data["sched_route_id"] = routes[idx].id
            set_data(session_id, data)
            times_txt, _ = list_times_text(Trip.MORNING)  # same list; window neutral here
            set_state(session_id, "CHECK_SCHEDULE_TIME")
            return cont(times_txt)

    if state == "CHECK_SCHEDULE_TIME":
        times_txt, times = list_times_text(Trip.MORNING)
        try:
            idx = int(last) - 1
        except ValueError:
            return end("Invalid selection.")
        if not (0 <= idx < len(times)):
            return end("Invalid selection.")
        time_str = times[idx]
        # Show both windows for this route & time
        route = Route.objects.get(id=data["sched_route_id"])
        morn = ensure_trip(route.id, Trip.MORNING, time_str)
        eve = ensure_trip(route.id, Trip.EVENING, time_str)
        out = (
            f"Schedule for {route.origin} - {route.destination} at {time_str}\n"
            f"Morning: {len(morn.available_seats())} seats available\n"
            f"Evening: {len(eve.available_seats())} seats available"
        )
        set_state(session_id, "MAIN_MENU")
        return end(out)

    # CANCEL RESERVATION FLOW (by route → show last held/confirmed → cancel)
    if state == "CANCEL_FLOW_ROUTE":
        try:
            idx = int(last) - 1
        except ValueError:
            return end("Invalid selection.")
        routes_txt, routes = list_routes_text()
        if not (0 <= idx < len(routes)):
            return end("Invalid selection.")
        data["cancel_route_id"] = routes[idx].id
        set_data(session_id, data)
        set_state(session_id, "CANCEL_PICK")
        return cont("Enter Reservation Code to cancel:")

    if state == "CANCEL_PICK":
        code = last.strip().upper()
        passenger = ensure_passenger(phone_number)
        res = (Reservation.objects
               .filter(passenger=passenger, reservation_code=code)
               .exclude(status=Reservation.CANCELLED)
               .first())
        if not res:
            set_state(session_id, "MAIN_MENU")
            return end("Reservation not found.")
        # If payment is pending, just cancel hold. If confirmed, mark cancelled and (optionally) refund flow.
        res.status = Reservation.CANCELLED
        res.save()
        set_state(session_id, "MAIN_MENU")
        return end("Reservation cancelled.")

    # default fallback
    set_state(session_id, "MAIN_MENU")
    return end("Session reset. Please try again.")


def render_seat_page(data):
    av = data["available_seats"]
    page = data["seat_page"]
    start = page * SEAT_PAGE_SIZE
    end_i = start + SEAT_PAGE_SIZE
    slice_ = av[start:end_i]
    lines = ["Select Seat Number"]
    for i, seat in enumerate(slice_, start=1):
        lines.append(f"{i}. Seat {seat}")
    # Next page
    if end_i < len(av):
        lines.append(f"{len(slice_) + 1}. Next page")
    return "\n".join(lines)