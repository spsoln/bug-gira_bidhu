"""
Bug-Gira — Email notifications.

Copyright (c) [2026] [Bidhu Tiwari]
Licensed under the MIT License. See LICENSE for details.

Notifications are sent inline but wrapped safely: a mail failure is
logged and never breaks the user's action. For scale, move sending
to a background task (Celery + Redis).
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("projects")


def notify_ticket_assigned(ticket):
    """Email the assignee that a ticket has been assigned to them."""
    assignee = ticket.assignee

    # Nothing to do if there's no assignee or they have no email
    if not assignee or not assignee.email:
        return

    ticket_ref = f"{ticket.project.key}-{ticket.id}"
    subject = f"[{ticket_ref}] Assigned to you: {ticket.title}"

    ticket_url = f"{settings.SITE_URL}/projects/tickets/{ticket.id}/"
    body = (
        f"Hi {assignee.username},\n\n"
        f"A ticket has been assigned to you on Bug-Gira:\n\n"
        f"  {ticket_ref}: {ticket.title}\n"
        f"  Priority: {ticket.get_priority_display()}\n"
        f"  Status: {ticket.get_status_display()}\n"
    )
    if ticket.due_date:
        body += f"  Due: {ticket.due_date.strftime('%b %d, %Y')}\n"
    body += f"\nView it here: {ticket_url}\n\n— Bug-Gira"

    _safe_send(subject, body, [assignee.email])


def _safe_send(subject, body, recipients):
    """Send an email, but never let a failure break the caller's action."""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        logger.info(f"Sent notification email to {recipients}: {subject}")
    except Exception as e:
        # Log it, but don't raise — the user's action must still succeed
        logger.error(f"Failed to send notification email to {recipients}: {e}")