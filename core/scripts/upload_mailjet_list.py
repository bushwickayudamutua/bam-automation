import csv
import argparse
import logging

from bam_core.lib.mailjet import Mailjet

log = logging.getLogger(__name__)

mj = Mailjet()


def get_parser():
    parser = argparse.ArgumentParser(description="Upload a list of emails to Mailjet")
    parser.add_argument(
        "-l", "--list-names", nargs="+", help="The names of the lists to upload to"
    )
    parser.add_argument("-c", "--csv", help="The csv file to upload")
    parser.add_argument(
        "-e", "--email", default="email", help="The column name of the email addresses"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Do not actually create the contacts",
    )
    parser.add_argument(
        "-s",
        "--sort-by",
        default="email",
        help="The column to sort by before uploading",
    )
    parser.add_argument(
        "-r", "--reverse", action="store_true", help="Reverse the sort order"
    )
    parser.add_argument(
        "-b",
        "--boolean-props",
        nargs="+",
        default=[],
        help="The names of the columns that should be treated as boolean properties",
    )
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    emails = set()
    with open(args.csv, "r") as f:
        data = [row for row in csv.DictReader(f)]
        for properties in sorted(
            data, key=lambda x: x[args.sort_by], reverse=args.reverse
        ):
            email = properties.pop(args.email)
            if email in emails:
                log.warning(f"Duplicate email: {email}")
                continue
            for prop in args.boolean_props or []:
                if prop in properties:
                    properties[prop] = properties[prop].lower() == "true"
            for list_name in args.list_names:
                log.info(f"Adding {email} to {list_name} with properties: {properties}")
                if not args.dry_run:
                    mj.add_contact_to_list(email, list_name, **properties)
            emails.add(email)


if __name__ == "__main__":
    main()
