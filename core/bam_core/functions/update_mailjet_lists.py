from pyairtable.api.types import RecordDict

from bam_core.constants import (
    VOLUNTEER_EMAIL_ERROR_FIELD,
    VOLUNTEER_EMAIL_FIELD,
    VOLUNTEER_NAME_FIELD,
    VOLUNTEERS_TABLE_NAME,
)
from bam_core.functions.base import Function
from bam_core.functions.params import Param, Params

MAILJET_LISTS = ["Volunteers", "All Contacts"]


class UpdateMailjetLists(Function):
    """
    Sync volunteer contacts from Airtable to Mailjet
    """

    params = Params(
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, data will not be written to Mailjet.",
        )
    )

    def _filter_new_contacts(
        self,
        all_contacts: list[RecordDict],
        current_contacts: set[str],
    ):
        """
        Filter contacts to only include new contacts
        Args:
            all_contacts: the list of all contacts
            current_contacts: the list of current contacts
        Returns:
            a list of new contacts
        """
        all_contacts = [
            contact
            for contact in all_contacts
            if not contact["fields"].get(VOLUNTEER_EMAIL_ERROR_FIELD)
        ]
        all_contacts = sorted(
            all_contacts, key=lambda x: x["createdTime"], reverse=True
        )
        # dedupe subscribers by email address
        new_contacts = {}
        for contact in all_contacts:
            email = contact["fields"].get(VOLUNTEER_EMAIL_FIELD, "").lower()
            if email and email not in current_contacts and email not in new_contacts:
                new_contacts[email] = {
                    "email": email,
                }
                firstname = contact["fields"].get(VOLUNTEER_NAME_FIELD)
                if firstname:
                    new_contacts[email]["firstname"] = firstname

        return list(new_contacts.values())

    def run(self, params):
        current_contacts = set(self.mailjet.get_all_emails())
        self.log.info(f"Syncing contacts from {VOLUNTEERS_TABLE_NAME}")
        all_contacts = self.airtable.volunteers.all(
            fields=[
                VOLUNTEER_NAME_FIELD,
                VOLUNTEER_EMAIL_FIELD,
                VOLUNTEER_EMAIL_ERROR_FIELD,
            ]
        )
        new_contacts = self._filter_new_contacts(all_contacts, current_contacts)
        n_new_contacts = len(new_contacts)
        self.log.info(
            f"Syncing {n_new_contacts} new contacts from {VOLUNTEERS_TABLE_NAME} to mailjet lists: {MAILJET_LISTS}"
        )

        # sync to all lists
        n_failures = 0
        for contact in new_contacts:
            for list_name in MAILJET_LISTS:
                kwargs = {**contact, "list_name": list_name}
                self.log.info(f"Adding contact {contact} to list {list_name}")
                if params["dry_run"]:
                    self.log.info("Dry run enabled. Skipping...")
                    continue
                try:
                    self.mailjet.add_contact_to_list(**kwargs)
                except Exception as e:
                    n_failures += 1
                    self.log.error(
                        f"Failed to add contact {contact} to list {list_name}: {e}. Continuing..."
                    )

        return {
            "n_new": n_new_contacts,
            "n_failures": n_failures,
        }


if __name__ == "__main__":
    UpdateMailjetLists().run_cli()
