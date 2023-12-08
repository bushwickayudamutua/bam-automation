import os
import logging
import tempfile
from datetime import datetime

from .base import Function
from bam_core.utils.serde import obj_to_json

log = logging.getLogger(__name__)


class UpdateWebsiteRequestData(Function):
    """
    Update the request counts on the website
    """

    CONFIG = {
        "filepath": "website-data/open-requests.json",
        "metrics": [
            {
                "name": "Groceries",
                "translations": {"span": "Comida", "eng": "Groceries"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Grocery Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "Pots and Pans",
                "translations": {
                    "span": "Ollas y sartenes",
                    "eng": "Pots and Pans",
                },
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Pots & Pans Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "Beds",
                "translations": {"span": "Camas", "eng": "Beds"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Bed Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "Pads",
                "translations": {"span": "Toallas sanitarias", "eng": "Pads"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Pads Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "Diapers",
                "translations": {"span": "Pañales", "eng": "Diapers"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Baby Diaper Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "Clothing Assistance",
                "translations": {"span": "Ropa", "eng": "Clothing Assistance"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Clothing Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "School Supplies",
                "translations": {
                    "span": "Útiles escolares",
                    "eng": "School Supplies",
                },
                "table": "Assistance Requests: Main",
                "view": "P2W - Open School Supplies Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
        ],
    }

    def run(self, event, context):
        """"""
        now = datetime.utcnow()
        output_data = {
            "metrics": [],
            "updated_at": now.strftime(r"%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        for metric in self.CONFIG.get("metrics"):
            metric_name = metric.pop("name")
            translations = metric.pop("translations", {})
            log.info(f"Generating metric:\n\t{metric}")
            output = {
                "name": metric_name,
                "translations": translations,
                "value": None,
            }
            output["value"] = self.airtable.get_view_count(**metric)
            output_data["metrics"].append(output)
        log.info(f"Generated metrics:\n\t{output_data['metrics']}")
        td = tempfile.gettempdir()
        tf = os.path.join(td, "request-counts.json")
        with open(tf, "w") as f:
            f.write(obj_to_json(output_data))
        prefix = self.CONFIG["filepath"]
        fp = self.s3.upload(tf, prefix, mimetype="application/json")
        self.s3.set_public(fp)
        log.info(
            f"Uploaded file with updated ts: {now.isoformat()} to s3: {fp}"
        )
        self.s3.purge_cdn_cache(prefix)
        log.info(f"Purged CDN cache for file: {prefix}")
        return output_data


if __name__ == "__main__":
    UpdateWebsiteRequestData().cli()
