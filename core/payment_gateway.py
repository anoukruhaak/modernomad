from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.core import urlresolvers
from models import Reservation, Payment
from django.conf import settings
from django.utils import timezone
import stripe

import logging

logger = logging.getLogger(__name__)

class PaymentException(Exception):
	pass

def charge_card(reservation):
	if settings.STRIPE_SECRET_KEY:
		return stripe_charge_card(reservation)
	elif settings.USA_E_PAY_KEY:
		return usaepay_charge_card(reservation)
	else:
		raise PaymentException("No payment system configured")

def issue_refund(payment):
	if payment.payment_service == "Stripe" and settings.STRIPE_SECRET_KEY:
		return stripe_issue_refund(payment)
	elif payment.payment_service == "USAePay" and settings.USA_E_PAY_KEY:
		return usaepay_issue_refund(payment)
	elif not payment.payment_service == "Stripe" and not payment.payment_service == "USAePay":
		logger.info("issue_refund: Payment not issued through service so we can't refund it.")
		return Payment.objects.create(reservation=payment.reservation,
			payment_service = payment.payment_service,
			paid_amount = -1 * payment.paid_amount,
			payment_method = "Refund",
			transaction_id = "Manual",
		)
	else:
		raise PaymentException("No payment system configured")

###################################################################
# Stripe Methods
###################################################################

def stripe_charge_card(reservation):
	logger.debug("stripe_charge_card(reservation=%s)" % reservation.id)
	
	# stripe will raise a stripe.CardError if the charge fails. this
	# function purposefully does not handle that error so the calling
	# function can decide what to do.
	reservation_url = "https://" + Site.objects.get_current().domain + urlresolvers.reverse('reservation_detail', args=(reservation.location.slug, reservation.id))
	descr = "%s from %s - %s. Details: %s." % (reservation.user.get_full_name(),
			str(reservation.arrive), str(reservation.depart), reservation_url)

	amt_owed = reservation.total_owed()
	amt_owed_cents = int(amt_owed * 100)
	stripe.api_key = settings.STRIPE_SECRET_KEY
	charge = stripe.Charge.create(
			amount=amt_owed_cents,
			currency="usd",
			customer = reservation.user.profile.customer_id,
			description=descr
		)

	# Store the charge details in a Payment object
	return Payment.objects.create(reservation=reservation,
		payment_service = "Stripe",
		payment_method = charge.card.brand,
		paid_amount = amt_owed,
		transaction_id = charge.id
	)

def stripe_issue_refund(payment):
	logger.debug("stripe_issue_refund(payment=%s)" % payment.id)
	
	stripe.api_key = settings.STRIPE_SECRET_KEY
	charge = stripe.Charge.retrieve(payment.transaction_id)
	refund = charge.refunds.create()

	# Store the charge details in a Payment object
	return Payment.objects.create(reservation=reservation,
		payment_service = "Stripe",
		payment_method = "Refund",
		paid_amount = -1 * payment.paid_amount,
		transaction_id = refund.id
	)
	
###################################################################
# USAePay Methods
###################################################################

def usaepay_charge_card(reservation):
	logger.debug("usaepay_charge_card(reservation=%s)" % reservation.id)
	return None

def usaepay_issue_refund(payment):
	logger.debug("usaepay_issue_refund(payment=%s)" % payment.id)
	return None