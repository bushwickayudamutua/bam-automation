import os
import tempfile
from datetime import datetime

from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.utils.serde import obj_to_json


class UpdateWebsiteRequestData(Function):
    """
    Update the request counts on the website
    """

    CONFIG = {
        "filepath": "website-data/open-requests.json",
        "metrics": [
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
                "name": "Baby Diapers",
                "translations": {"span": "Pañales para Bebé", "eng": "Baby Diapers"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Baby Diaper Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "Adult Diapers",
                "translations": {"span": "Pañales para Adultos", "eng": "Adult Diapers"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Adult Diaper Requests",
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
            {
                "name": "Plates",
                "translations": {"span": "Platos", "eng": "Plates"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Plates Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "Cups",
                "translations": {"span": "Tazas", "eng": "Cups"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Cups Requests",
                "fields": ["Phone Number"],
                "unique": True,
            },
            {
                "name": "Soap",
                "translations": {"span": "Jabón", "eng": "Soap"},
                "table": "Assistance Requests: Main",
                "view": "P2W - Open Soap & Shower Products Requests",
                "fields": ["Phone Number"],
                "unique": True,
            }
        ],
    }

    params = Params(
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, data will not be written to the digital ocean space.",
        )
    )

    def run(self, params, context):
        """"""
        now = datetime.utcnow()
        output_data = {
            "metrics": [],
            "updated_at": now.strftime(r"%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        for metric in self.CONFIG.get("metrics"):
            metric_name = metric.pop("name")
            translations = metric.pop("translations", {})
            self.log.info(f"Generating metric:\n\t{metric}")
            output = {
                "name": metric_name,
                "translations": translations,
                "value": None,
            }
            output["value"] = self.airtable.get_view_count(**metric)
            output_data["metrics"].append(output)
        self.log.info(f"Generated metrics:\n\t{output_data['metrics']}")
        if params["dry_run"]:
            self.log.info(
                "Dry run enabled. Skipping upload to digital ocean space."
            )
            return output_data
        td = tempfile.gettempdir()
        tf = os.path.join(td, "request-counts.json")
        with open(tf, "w") as f:
            f.write(obj_to_json(output_data))
        prefix = self.CONFIG["filepath"]
        fp = self.s3.upload(tf, prefix, mimetype="application/json")
        self.s3.set_public(fp)
        self.log.info(
            f"Uploaded file with updated ts: {now.isoformat()} to digital ocean space: {fp}"
        )
        self.s3.purge_cdn_cache(prefix)
        self.log.info(f"Purged CDN cache for file: {prefix}")
        return output_data


if __name__ == "__main__":
    UpdateWebsiteRequestData().run_cli()
