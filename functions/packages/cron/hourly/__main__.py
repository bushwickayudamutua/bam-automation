from bam_core.functions.update_website_request_data import (
    UpdateWebsiteRequestData,
)
from bam_core.functions.base import Function


def main(event, context):
    return Function.run_do_functions(event, context, UpdateWebsiteRequestData)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        dry_run = True
    else:
        dry_run = False if sys.argv[1] == "false" else True
    from pprint import pprint
    output = main({"dry_run": dry_run}, {})
    pprint(output)
