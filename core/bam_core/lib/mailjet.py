import time
from typing import Any, Dict, List
import requests

from bam_core import settings


class Mailjet(object):
    # a list of contact lists and their IDs
    # these were manually created in the Mailjet dashboard
    # If we delete them, we'll need to update this list
    CONTACT_LISTS = {
        "All Contacts": 10332279,
        "Families": 10331737,
        "Volunteers": 10331731,
    }

    ACTION_ADD = "addnoforce"
    ACTION_REMOVE = "remove"
    ACTION_UNSUBSCRIBE = "unsub"

    def __init__(
        self,
        api_key=settings.MAILJET_API_KEY,
        api_secret=settings.MAILJET_API_SECRET,
    ):
        self.auth = (api_key, api_secret)
        self.base_url = "https://api.mailjet.com/v3/REST/"

    def _make_request(self, method, endpoint, data=None, params={}):
        """
        Make a request to the Mailjet API
        """
        url = self.base_url + endpoint
        nb_tries = 10
        while True:
            nb_tries -= 1
            try:
                # Request url
                return requests.request(
                    method, url, auth=self.auth, json=data, params=params
                )
            except Exception as err:
                if nb_tries == 0:
                    raise err
                else:
                    time.sleep(1 + 10 / nb_tries)

    def add_contact(self, email: str, name=None):
        """
        Add a contact to mailjet
        """
        data = {"Email": email}
        if name:
            data["Name"] = name
        result = self._make_request("POST", "contact", data=data)

        # handle errors and check if the contact already exists
        if not str(result.status_code).startswith("2"):
            try:
                data = result.json()
                error_message = (
                    f"{data.get('ErrorMessage')}: {data.get('ErrorInfo')}"
                )
            except:
                error_message = result.content or "Unknown error"
            if "already exists" in error_message and email in error_message:
                return None
            raise Exception(error_message)

        # return the new contact
        data = result.json().get("Data", [])[0]
        return data

    def manage_list_for_contact(
        self, email: str, list_name: str, action: str, **properties
    ):
        """
        Add or remove a contact from a list
        Args:
            email: the email address of the contact
            list_name: the name of the list to add the contact to
            action: either 'addnoforce' or 'remove' or 'unsub'
        """
        list_id = self.CONTACT_LISTS.get(list_name)
        if not list_id:
            raise Exception(f"Invalid list name: {list_name}")
        data = {
            "Email": email,
            "Action": action,
            "Properties": properties,
        }
        endpoint = f"contactslist/{list_id}/managecontact"
        result = self._make_request("POST", endpoint, data=data)

        if not str(result.status_code).startswith("2"):
            try:
                data = result.json()
                error_message = (
                    f"{data.get('ErrorMessage')}: {data.get('ErrorInfo')}"
                )
            except:
                error_message = result.content or "Unknown error"
            raise Exception(error_message)
        return result.json().get("Data", [])[0]

    def add_contact_to_list(
        self, email: str, list_name: str, **properties
    ) -> Dict[str, Any]:
        """
        Add a contact to a list
        Args:
            email: the email address of the contact
            list_name: the name of the list to add the contact to
        """
        return self.manage_list_for_contact(
            email, list_name, self.ACTION_ADD, **properties
        )

    def remove_contact_from_list(
        self, email: str, list_name: str, **properties
    ) -> Dict[str, Any]:
        """
        Remove a contact from a list
        Args:
            email: the email address of the contact
            list_name: the name of the list to add the contact to
        """
        return self.manage_list_for_contact(
            email, list_name, self.ACTION_REMOVE, **properties
        )

    def unsubscribe_contact_from_list(
        self, email: str, list_name: str, **properties
    ) -> Dict[str, Any]:
        """
        Unsubscribe a contact from a list
        Args:
            email: the email address of the contact
            list_name: the name of the list to add the contact to
        """
        return self.manage_list_for_contact(
            email, list_name, self.ACTION_UNSUBSCRIBE, **properties
        )

    def get_contacts(
        self, limit: int = 1000, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get a list of contacts
        Args:
            limit: the number of contacts to return
            offset: the number of contacts to skip
        Returns:
            a list of contacts
        """
        result = self._make_request(
            "GET", "contact", params={"Limit": limit, "Offset": offset}
        )
        if not str(result.status_code).startswith("2"):
            try:
                data = result.json()
                error_message = (
                    f"{data.get('ErrorMessage')}: {data.get('ErrorInfo')}"
                )
            except:
                error_message = result.content or "Unknown error"
            raise Exception(error_message)
        return result.json().get("Data", [])

    def get_all_contacts(self) -> List[Dict[str, Any]]:
        """
        Get all contacts
        """
        contacts = []
        limit = 1000
        offset = 0
        while True:
            result = self.get_contacts(limit=limit, offset=offset)
            if not result:
                break
            contacts.extend(result)
            offset += limit
        return contacts

    def get_all_emails(self) -> List[str]:
        """
        Get all emails
        """
        emails = []
        contacts = self.get_all_contacts()
        for contact in contacts:
            emails.append(contact.get("Email"))
        return emails
