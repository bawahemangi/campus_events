"""
Payment views — Razorpay integration for paid events.

Flow:
  1. Student clicks "Register & Pay" on a paid event
  2. create_payment_order() → creates Razorpay order, returns order_id + key
  3. Frontend Razorpay checkout opens (no redirect, all in browser)
  4. On success, Razorpay calls verify_payment() with payment_id + signature
  5. We verify signature, mark payment complete, create Registration, send emails
"""
import json
import hmac
import hashlib

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import Event, Payment, Registration
from .utils import (
    send_registration_email, send_payment_confirmation_email,
    generate_certificate, create_notification
)


def _razorpay_client():
    """Return a Razorpay client, or None if library not installed."""
    try:
        import razorpay
        return razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    except ImportError:
        return None


@login_required
def initiate_payment(request, event_pk):
    """
    Step 1 — Create a Razorpay order and show the payment page.
    GET  → show payment confirmation page
    POST → already handled in payment_page template via JS
    """
    event = get_object_or_404(Event, pk=event_pk, status='approved', is_paid=True)

    if not request.user.is_student:
        messages.error(request, 'Only students can register for events.')
        return redirect('event_detail', pk=event_pk)

    if event.is_full:
        messages.error(request, 'Sorry, this event is full!')
        return redirect('event_detail', pk=event_pk)

    if event.is_past:
        messages.error(request, 'Registration is closed for past events.')
        return redirect('event_detail', pk=event_pk)

    # Check already registered
    if Registration.objects.filter(event=event, student=request.user).exists():
        messages.warning(request, 'You are already registered for this event.')
        return redirect('event_detail', pk=event_pk)

    # Check pending/completed payment already exists
    existing_payment = Payment.objects.filter(
        event=event, student=request.user, status__in=['completed']
    ).first()
    if existing_payment:
        messages.info(request, 'You have already paid for this event.')
        return redirect('event_detail', pk=event_pk)

    client = _razorpay_client()
    amount_paise = int(event.registration_fee * 100)

    if client:
        try:
            order = client.order.create({
                'amount':   amount_paise,
                'currency': settings.RAZORPAY_CURRENCY,
                'payment_capture': 1,
                'notes': {
                    'event_id':   str(event.pk),
                    'student_id': str(request.user.pk),
                    'event_name': event.title,
                }
            })
            order_id = order['id']
        except Exception as e:
            messages.error(request, f'Payment gateway error: {e}')
            return redirect('event_detail', pk=event_pk)
    else:
        # Razorpay not installed — use a mock order for demo/testing
        order_id = f'order_DEMO_{event.pk}_{request.user.pk}'

    # Save a pending payment record
    payment = Payment.objects.create(
        student=request.user,
        event=event,
        razorpay_order_id=order_id,
        amount=event.registration_fee,
        amount_paise=amount_paise,
        status='pending',
    )

    context = {
        'event':          event,
        'payment':        payment,
        'razorpay_key':   settings.RAZORPAY_KEY_ID,
        'amount_paise':   amount_paise,
        'order_id':       order_id,
        'student_name':   request.user.get_full_name() or request.user.username,
        'student_email':  request.user.email,
        'student_phone':  request.user.phone or '',
        'demo_mode':      client is None,
    }
    return render(request, 'events/payment_page.html', context)


@login_required
def verify_payment(request):
    """
    Step 2 — Called via AJAX after Razorpay checkout completes.
    Verifies the HMAC signature and finalises registration.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})

    data               = json.loads(request.body)
    razorpay_order_id  = data.get('razorpay_order_id', '')
    razorpay_payment_id= data.get('razorpay_payment_id', '')
    razorpay_signature = data.get('razorpay_signature', '')
    demo_mode          = data.get('demo_mode', False)

    payment = get_object_or_404(
        Payment, razorpay_order_id=razorpay_order_id, student=request.user
    )

    # Verify signature (skip in demo mode)
    if not demo_mode:
        try:
            expected_sig = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
                hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected_sig, razorpay_signature):
                payment.status = 'failed'
                payment.save()
                return JsonResponse({'success': False, 'error': 'Payment verification failed. Please contact support.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # Mark payment complete
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature  = razorpay_signature
    payment.status = 'completed'
    payment.save()

    # Create registration
    event = payment.event
    reg, created = Registration.objects.get_or_create(
        event=event, student=request.user,
        defaults={'payment': payment}
    )
    if created:
        reg.payment = payment
        reg.generate_qr_code()
        reg.save()

        # Emails
        send_registration_email(reg)
        send_payment_confirmation_email(payment)

        # In-app notifications
        create_notification(
            request.user,
            f'Payment Confirmed: {event.title}',
            f'Your payment of ₹{payment.amount} is confirmed. You are now registered!',
            'payment',
            link=f'/events/{event.pk}/'
        )

    return JsonResponse({
        'success': True,
        'message': f'Payment successful! You are now registered for {event.title}.',
        'redirect': f'/events/{event.pk}/'
    })


@login_required
def payment_failed(request, event_pk):
    """Handle payment failure / cancellation."""
    event = get_object_or_404(Event, pk=event_pk)
    # Mark any pending payments as failed
    Payment.objects.filter(
        event=event, student=request.user, status='pending'
    ).update(status='failed')
    messages.error(request, 'Payment was cancelled or failed. You have not been registered.')
    return redirect('event_detail', pk=event_pk)


@login_required
def payment_history(request):
    """Student's payment history page."""
    payments = Payment.objects.filter(
        student=request.user
    ).select_related('event').order_by('-created_at')
    return render(request, 'events/payment_history.html', {'payments': payments})
