from bam_core.functions.update_website_request_data import (
    UpdateWebsiteRequestData,
)
from bam_core.functions.base import Function


def main(event, context):
    return Function.run_do_functions(event, context, UpdateWebsiteRequestData)


if __name__ == "__main__":
    from pprint import pprint

    output = main({}, {})
    pprint(output)
