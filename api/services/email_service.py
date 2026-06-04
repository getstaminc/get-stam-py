"""Brevo email service wrapper (brevo-python v4)."""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
_BREVO_LIST_ID_RAW = os.getenv("BREVO_LIST_ID", "0")
BREVO_LIST_ID = int(_BREVO_LIST_ID_RAW) if _BREVO_LIST_ID_RAW.isdigit() else 0
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "")
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "GetSTAM")


def _client():
    from brevo import Brevo
    return Brevo(api_key=BREVO_API_KEY)


class EmailService:

    @staticmethod
    def subscribe(email):
        """
        Subscribe an email to the list.
        Returns (True, None), (False, "already_subscribed"), or (False, err_str).
        """
        try:
            _client().contacts.create_contact(
                email=email,
                list_ids=[BREVO_LIST_ID],
                update_enabled=True,
            )
            return True, None
        except Exception as e:
            logger.error("EmailService.subscribe error: %s", e)
            return False, str(e)

    @staticmethod
    def get_all_subscribers():
        """
        Return (list[str], error) — paginates in 500-contact batches.
        """
        try:
            client = _client()
            all_emails = []
            offset = 0
            limit = 500

            while True:
                response = client.contacts.get_contacts(
                    limit=limit,
                    offset=offset,
                    list_ids=BREVO_LIST_ID,
                )
                contacts = response.contacts or []
                for contact in contacts:
                    email = getattr(contact, 'email', None)
                    if email:
                        all_emails.append(email)
                if len(contacts) < limit:
                    break
                offset += limit

            return all_emails, None

        except Exception as e:
            logger.error("EmailService.get_all_subscribers error: %s", e)
            return [], str(e)

    @staticmethod
    def unsubscribe(email):
        """
        Remove an email from the list.
        Returns (True, None) or (False, err_str).
        """
        try:
            from brevo.contacts.types.remove_contact_from_list_request_body_emails import RemoveContactFromListRequestBodyEmails
            _client().contacts.remove_contact_from_list(
                list_id=BREVO_LIST_ID,
                request=RemoveContactFromListRequestBodyEmails(emails=[email]),
            )
            return True, None
        except Exception as e:
            logger.error("EmailService.unsubscribe error: %s", e)
            return False, str(e)

    @staticmethod
    def send_digest_to_one(email, subject, html_content):
        """
        Send a transactional email to a single recipient.
        Returns (True, None) or (False, err_str).
        """
        try:
            _client().transactional_emails.send_transac_email(
                sender={"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
                reply_to={"name": BREVO_SENDER_NAME, "email": BREVO_SENDER_EMAIL},
                to=[{"email": email}],
                subject=subject,
                html_content=html_content,
            )
            return True, None

        except Exception as e:
            logger.error("EmailService.send_digest_to_one error: %s", e)
            return False, str(e)
