from bam_core.functions.update_website_request_data import (
    UpdateWebsiteRequestData,
)


def main(event, context):
    update_website_output = UpdateWebsiteRequestData().main(event, context)
    return {
        "update_website_request_data": update_website_output,
    }


if __name__ == "__main__":
    main(None, None)
