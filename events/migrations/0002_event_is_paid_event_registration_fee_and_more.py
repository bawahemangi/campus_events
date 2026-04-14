"""
Migration: Add payment/paid-event fields to Event and Registration,
and create the Payment model.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Event: paid-event fields ──────────────────────────────────────
        migrations.AddField(
            model_name='event',
            name='is_paid',
            field=models.BooleanField(default=False, help_text='Check if this is a paid event'),
        ),
        migrations.AddField(
            model_name='event',
            name='entry_fee',
            field=models.DecimalField(
                decimal_places=2, default=0.00, max_digits=8,
                help_text='Entry fee in INR (0 for free events)'
            ),
        ),
        # ── Registration: payment status ──────────────────────────────────
        migrations.AddField(
            model_name='registration',
            name='payment_status',
            field=models.CharField(
                choices=[
                    ('not_required', 'Not Required'),
                    ('pending', 'Pending Payment'),
                    ('paid', 'Paid'),
                    ('failed', 'Payment Failed'),
                    ('refunded', 'Refunded'),
                ],
                default='not_required',
                max_length=20,
            ),
        ),
        # ── Payment model ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('razorpay_order_id', models.CharField(max_length=100, unique=True)),
                ('razorpay_payment_id', models.CharField(blank=True, max_length=100)),
                ('razorpay_signature', models.CharField(blank=True, max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, help_text='Amount in INR')),
                ('currency', models.CharField(default='INR', max_length=10)),
                ('status', models.CharField(
                    choices=[
                        ('created', 'Order Created'),
                        ('paid', 'Paid'),
                        ('failed', 'Failed'),
                        ('refunded', 'Refunded'),
                    ],
                    default='created',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('registration', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payment',
                    to='events.registration',
                )),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-created_at']},
        ),
        # ── Notification: new types ───────────────────────────────────────
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('registration', 'Registration Confirmed'),
                    ('reminder', 'Event Reminder'),
                    ('approval', 'Event Approved'),
                    ('rejection', 'Event Rejected'),
                    ('certificate', 'Certificate Available'),
                    ('payment', 'Payment Confirmed'),
                    ('payment_failed', 'Payment Failed'),
                    ('general', 'General'),
                ],
                default='general',
                max_length=20,
            ),
        ),
    ]