# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .models import Table, Branch, Reservation, WaitlistEntry
from datetime import datetime, timedelta
from django.utils.timezone import make_aware, now
import requests
import uuid
from django.http import HttpResponse, HttpResponseForbidden


def reservation_preface(request):
    return render(request, "core/reservation_preface.html")

def reserve_init(request):
    return render(request, "core/reserve_init.html")

def details(request):
    branch_id = request.session.get('branch_id')
    branch_name = request.session.get('branch_name')
    reservation_date = request.session.get('reservation_date')
    reservation_time = request.session.get('reservation_time')
    guest_total = request.session.get('guest_total')
    table_code = request.session.get('table_code')

    if not all([branch_name, reservation_date, reservation_time, guest_total, table_code]):
        return render(request, 'core/error.html', {"message": "Reservation data missing."})

    return render(request, 'core/details.html', {
        'branch': {
            'id': branch_id,
            'name': branch_name
        },
        'reservation_date': reservation_date,
        'reservation_time': reservation_time,
        'guest_total': guest_total,
        'table_code': table_code
    })

def reserve_alt(request):
    return render(request, "core/reserve_alt.html")

def success_final(request):
    return render(request, "core/success_final.html")

def check_availability(request):
    if request.method != 'POST':
        return render(request, 'core/error.html', {"message": "Invalid request method."})

    branch_name = request.POST.get('branch')
    date_str = request.POST.get('date')
    time_str = request.POST.get('time')

    try:
        reservation_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %I:%M %p")
    except ValueError:
        return render(request, 'core/error.html', {"message": "Invalid date/time format."})

    reservation_date = reservation_datetime.date()
    reservation_end = reservation_datetime + timedelta(hours=2)
    adults = int(request.POST.get('adults', 0))
    seniors = int(request.POST.get('seniors', 0))
    children = int(request.POST.get('children', 0))
    babies = int(request.POST.get('babies', 0))
    total_guests = adults + seniors + children + babies
    allow_overbook = babies > 0

    try:
        branch = Branch.objects.get(name=branch_name)
    except Branch.DoesNotExist:
        return render(request, 'core/error.html', {"message": "Branch not found."})

    all_tables = Table.objects.filter(branch=branch)

    day_reservations = Reservation.objects.filter(
        table__branch=branch,
        date=reservation_date
    )

    overlapping_table_ids = []
    for res in day_reservations:
        existing_start = datetime.combine(res.date, res.time)
        existing_end = existing_start + timedelta(hours=2)
        if existing_start < reservation_end and reservation_datetime < existing_end:
            overlapping_table_ids.append(res.table_id)

    available_tables = all_tables.exclude(id__in=overlapping_table_ids)

    suitable_table = None
    for table in sorted(available_tables, key=lambda t: t.capacity):
        if allow_overbook and table.capacity + 1 >= total_guests:
            suitable_table = table
            break
        elif not allow_overbook and table.capacity >= total_guests:
            suitable_table = table
            break

    if suitable_table:
        request.session['branch_id'] = branch.id
        request.session['branch_name'] = branch.name
        request.session['reservation_date'] = reservation_datetime.strftime('%Y-%m-%d')
        request.session['reservation_time'] = reservation_datetime.strftime('%I:%M %p')
        request.session['guest_total'] = total_guests
        request.session['table_code'] = suitable_table.code

        return render(request, 'core/success.html', {
            'table': suitable_table,
            'branch': branch,
            'start_time': reservation_datetime,
            'guest_data': {
                'adults': adults,
                'seniors': seniors,
                'children': children,
                'babies': babies,
                'total': total_guests
            }
    })
    else:
        return render(request, 'core/no_availability.html', {
            'original_branch': branch,
            'original_time': time_str,
            'original_date': date_str,
            'guest_data': {
                'adults': adults,
                'seniors': seniors,
                'children': children,
                'babies': babies,
                'total': total_guests
            }
        })

def submit_reservation(request):
    if request.method != 'POST':
        return render(request, 'core/error.html', {"message": "Invalid request method."})

    try:
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        phone = request.POST['phone']
        branch = get_object_or_404(Branch, pk=request.POST['branch_id'])
        table = get_object_or_404(Table, code=request.POST['table_code'], branch=branch)
        guest_total = int(request.POST['guest_total'])
        reservation_dt = make_aware(datetime.strptime(
            f"{request.POST['reservation_date']} {request.POST['reservation_time']}",
            "%Y-%m-%d %I:%M %p"
        ))
    except Exception:
        return render(request, 'core/error.html', {"message": "Invalid form submission."})

    overlapping = Reservation.objects.filter(
        table=table,
        date=reservation_dt.date(),
        time__lt=(reservation_dt + timedelta(hours=2)).time(),
        time__gt=(reservation_dt - timedelta(hours=2)).time()
    )
    if overlapping.exists():
        return render(request, 'core/error.html', {"message": "This table is no longer available."})

    reservation = Reservation.objects.create(
        branch=branch,
        table=table,
        customer_name=f"{first_name} {last_name}",
        customer_email=email,
        customer_phone=phone,
        date=reservation_dt.date(),
        time=reservation_dt.time(),
        purpose=request.POST.get('purpose'),
        allergies=request.POST.get('allergies', ''),
        requests=request.POST.get('requests', ''),
        status="pending",
        adults=guest_total,
    )

    return redirect('success_final', reservation_id=reservation.id)

def success_final(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    return render(request, 'core/success_final.html', {
        'reservation': reservation
    })


def reservation_success(request):
    session_id = request.GET.get("session_id")
    reservation = Reservation.objects.filter(paymongo_session_id=session_id).first()

    if not reservation:
        return render(request, "error.html", {"message": "Reservation not found."})

    if not reservation.paid:
        reservation.paid = True
        reservation.save()

        cancel_url = request.build_absolute_uri(
            reverse("cancel_reservation", args=[reservation.cancel_token])
        )

        send_mail(
            subject='Reservation Confirmed',
            message=f"""Hi {reservation.customer_name},

Your reservation is confirmed!

Branch: {reservation.branch.name}
Table: {reservation.table.code}
Date: {reservation.date}
Time: {reservation.time}
Guests: {reservation.total_guests()} (Adults: {reservation.adults})
Purpose: {reservation.purpose}
Allergies: {reservation.allergies}
Requests: {reservation.requests}

To cancel your reservation, click this link:
{cancel_url}

We look forward to seeing you!
""",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[reservation.customer_email],
            fail_silently=False,
        )

    return render(request, "reservation_success.html", {"reservation": reservation})

def cancel_reservation(request, token):
    reservation = get_object_or_404(Reservation, cancel_token=token)
    table = reservation.table
    reservation_date = reservation.date
    reservation_time = reservation.time
    branch = reservation.branch

    table.is_available = True
    table.save()
    reservation.delete()

    waitlist_matches = WaitlistEntry.objects.filter(
        branch=branch,
        date=reservation_date,
        guest_total__lte=table.capacity
    ).order_by('created_at')

    if waitlist_matches.exists():
        entry = waitlist_matches.first()
        new_reservation = Reservation.objects.create(
            branch=entry.branch,
            table=table,
            customer_name=entry.customer_name,
            customer_email=entry.customer_email,
            customer_phone=entry.phone,
            date=entry.date,
            time=entry.preferred_time,
            purpose=entry.purpose,
            allergies=entry.allergies,
            requests=entry.requests,
            status="pending",
            adults=entry.guest_total,
            cancel_token=uuid.uuid4()
        )
        table.is_available = False
        table.save()
        cancel_url = request.build_absolute_uri(reverse('cancel_reservation', args=[new_reservation.cancel_token]))
        send_mail(
            subject="A Table Just Opened Up for You at The Bellington",
            message=f"""Hi {new_reservation.customer_name},

A table just became available and we've reserved it for you!

Date: {new_reservation.date}
Time: {new_reservation.time}
Guests: {new_reservation.adults}
Table: {new_reservation.table.code}

To cancel, click here:
{cancel_url}

Enjoy your meal!

- Your Restaurant Team
""",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[new_reservation.customer_email],
            fail_silently=False,
        )
        entry.delete()

    return render(request, 'core/cancelled.html', {'table': table})

def join_waitlist(request):
    if request.method == 'POST':
        branch = get_object_or_404(Branch, pk=request.POST.get('branch_id'))
        name = request.POST.get('customer_name')
        email = request.POST.get('customer_email')
        phone = request.POST.get('phone')
        date = request.POST.get('reservation_date')
        time = request.POST.get('reservation_time')
        guests = int(request.POST.get('guest_total'))

        WaitlistEntry.objects.create(
            customer_name=name,
            customer_email=email,
            phone=phone,
            branch=branch,
            guest_total=guests,
            date=date,
            preferred_time=time
        )
        return render(request, "core/waitlist_success.html")

    return render(request, "error.html", {"message": "Invalid request method."})