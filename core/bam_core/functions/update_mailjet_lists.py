from typing import Any, Dict, List

from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param


class UpdateMailjetLists(Function):
    """
    Sync contacts from Airtable to Mailjet
    """

    CONFIG = [
        {
            "table_name": "Volunteers: Main",
            "view_name": "Raw Data: DO NOT EDIT",
            "lists": ["Volunteers", "All Contacts"],
            "sort": "createdTime",
            "fields": {
                "name": "First Name",
                "email": "Email",
                "error": "Email Error",
            },
        },
        {
            "table_name": "Assistance Requests: Main",
            "view_name": "Raw Data: DO NOT EDIT OR CHANGE FILTERS!",
            "lists": ["Families", "All Contacts"],
            "sort": "createdTime",
            "fields": {
                "name": "First Name",
                "email": "Email",
                "error": "Email Error",
            },
        },
    ]

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
        view: Dict[str, Any],
        all_contacts: List[Dict[str, Any]],
        current_contacts: List[str],
    ):
        """
        Filter contacts to only include new contacts
        Args:
            view: the view configuration
            all_contacts: the list of all contacts
            current_contacts: the list of current contacts
        Returns:
            a list of new contacts
        """
        all_contacts = sorted(
            all_contacts, key=lambda x: x[view["sort"]], reverse=True
        )
        all_contacts = filter(
            lambda x: not x["fields"].get(view["fields"]["error"], None),
            all_contacts,
        )
        # dedupe subscribers by email address
        new_contacts = {}
        for contact in all_contacts:
            email = contact["fields"].get(view["fields"]["email"], "").lower()
            if (
                email
                and email not in current_contacts
                and email not in new_contacts
            ):
                new_contacts[email] = {
                    "email": email,
                }
                firstname = contact["fields"].get(view["fields"]["name"], None)
                if firstname:
                    new_contacts[email]["firstname"] = firstname

        return list(new_contacts.values())

    def run(self, params, context):
        results = []
        current_contacts = set(self.mailjet.get_all_emails())
        for view in self.CONFIG:
            self.log.info(f"Syncing contacts from {view['table_name']}")
            fields = view.get("fields")
            all_contacts = self.airtable.get_view(
                table_name=view["table_name"],
                view_name=view["view_name"],
                fields=list(fields.values()),
            )
            new_contacts = self._filter_new_contacts(
                view, all_contacts, current_contacts
            )
            n_new_contacts = len(new_contacts)
            self.log.info(
                f"Syncing {n_new_contacts} new contacts from {view['table_name']} to mailjet lists: {view['lists']}"
            )

            # sync to all lists
            n_failures = 0
            for contact in new_contacts:
                for list_name in view["lists"]:
                    kwargs = {**contact, "list_name": list_name}
                    self.log.info(
                        f"Adding contact {contact} to list {list_name}"
                    )
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

            results.append(
                {
                    "view": view,
                    "n_new": n_new_contacts,
                    "n_failures": n_failures,
                }
            )
        return results


if __name__ == "__main__":
    UpdateMailjetLists().run_cli()
