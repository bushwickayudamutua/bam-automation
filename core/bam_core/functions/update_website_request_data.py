import os
import tempfile
from datetime import UTC, datetime, timedelta
from typing import NotRequired, TypedDict

from pyairtable.formulas import AND, OR, Field
from pyairtable.orm import Model

from bam_core.functions.base import Function
from bam_core.functions.params import Param, Params
from bam_core.lib.airtable_v2 import FurnitureRequest, Request, count_table
from bam_core.utils.serde import obj_to_json


def request_status_is(s: str):
    return Field("Status").eq(s)


def request_type_is(t: str):
    return Field("Type").eq(t)


OPEN_REQUEST_FILEPATH = "website-data/open-requests.json"
FULFILLED_REQUEST_FILEPATH = "website-data/fulfilled-requests.json"


class MetricConfig(TypedDict):
    name: str
    translations: dict[str, str]
    count_columns: NotRequired[list[str]]
    model: type[Model]
    types: list[str]


METRIC_CONFIGS: list[MetricConfig] = [
    {
        "name": "Pots and Pans",
        "translations": {
            "span": "Ollas y sartenes",
            "eng": "Pots and Pans",
        },
        "count_columns": ["Pots & Pans"],
        "model": Request,
        "types": ["Ollas y Sartenes / Pots & Pans / 鍋碗瓢盆"],
    },
    {
        "name": "Beds",
        "translations": {"span": "Camas", "eng": "Beds"},
        "count_columns": [
            "Twin Mattress + Frame",
            "Full Mattress + Frame",
            "Queen Mattress + Frame",
            "King Mattress + Frame",
        ],
        "model": FurnitureRequest,
        "types": [
            "Cama individual / Twin Mattress + Frame / 單人床墊+床架",
            "Cama matrimonio / Full Mattress + Frame / 雙人床墊+床架",
            "Cama tamaño Queen / Queen Mattress + Frame / 雙人加大床墊+床架",
            "Cama tamaño King / King Mattress + Frame / 雙人特大床墊+床架",
        ],
    },
    {
        "name": "Pads",
        "translations": {"span": "Toallas sanitarias", "eng": "Pads"},
        "model": Request,
        "count_columns": ["Feminine Products - Pads"],
        "types": ["Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾"],
    },
    {
        "name": "Baby Diapers",
        "translations": {"span": "Pañales para Bebé", "eng": "Baby Diapers"},
        "model": Request,
        "types": ["Pañales / Baby Diapers / 嬰兒紙尿褲"],
    },
    {
        "name": "Adult Diapers",
        "translations": {"span": "Pañales para Adultos", "eng": "Adult Diapers"},
        "model": Request,
        "types": ["Pañales de adultos / Adult Diapers / 成人紙尿褲"],
    },
    {
        "name": "Clothing Assistance",
        "translations": {"span": "Ropa", "eng": "Clothing Assistance"},
        "count_columns": ["Clothing"],
        "model": Request,
        "types": ["Ropa / Clothing / 服裝"],
    },
    {
        "name": "School Supplies",
        "translations": {
            "span": "Útiles escolares",
            "eng": "School Supplies",
        },
        "model": Request,
        "types": ["Cosas de Escuela / School Supplies / 學校用品"],
    },
    {
        "name": "Plates or Cups",
        "translations": {"span": "Platos o Tazas", "eng": "Plates or Cups"},
        "model": Request,
        "types": ["Platos o Tazas / Plates or Cups / 盘子或杯子"],
    },
    {
        "name": "Soap",
        "translations": {"span": "Jabón", "eng": "Soap"},
        "count_columns": ["Soap & Shower Products"],
        "model": Request,
        "types": [
            "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品"
        ],
    },
]


class UpdateWebsiteRequestData(Function):
    """
    Update the request counts on the website
    """

    params = Params(
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, data will not be written to the digital ocean space.",
        )
    )

    def _write_data_to_s3(self, data: object, s3_filepath: str):
        td = tempfile.gettempdir()
        tf = os.path.join(td, "data.json")
        with open(tf, "w") as f:
            f.write(obj_to_json(data))
        fp = self.s3.upload(tf, s3_filepath, mimetype="application/json")
        self.s3.set_public(fp)
        self.s3.purge_cdn_cache(s3_filepath)
        self.log.info(f"Purged CDN cache for file: {s3_filepath}")

    def run(self, params, context):
        """"""
        now = datetime.now(UTC)

        end_date = datetime.now().date().isoformat()
        start_date = (datetime.now().date() - timedelta(days=31)).isoformat()
        fulfillment_counts = count_table.all(
            formula=AND(
                Field("Date").gte(start_date),
                Field("Date").lte(end_date),
            )
        )

        open_request_data = {
            "metrics": [],
            "updated_at": now.strftime(r"%Y-%m-%dT%H:%M:%S.%fZ"),
        }

        fulfilled_request_data = {
            "start_date": start_date,
            "end_date": end_date,
            "metrics": [],
        }
        for metric in METRIC_CONFIGS:
            self.log.info(f"Generating metric:\n\t{metric}")
            name = metric["name"]
            translations = metric["translations"]
            model = metric["model"]
            types = metric["types"]
            count_columns = metric.get("count_columns", [name])
            is_correct_type = (
                request_type_is(types[0])
                if len(types) == 1
                else OR(*[request_type_is(t) for t in types])
            )

            # Count open requests
            open_formula = AND(
                is_correct_type,
                request_status_is("Open"),
            )
            open_request_count = len(model.all(formula=open_formula))

            open_request_data["metrics"].append(
                {
                    "name": name,
                    "translations": translations,
                    "value": open_request_count,
                }
            )

            # Count closed requests
            old_fulfilled_request_count = sum(
                [
                    count["fields"].get(column, 0)
                    for count in fulfillment_counts
                    for column in count_columns
                ]
            )

            fulfilled_formula = AND(
                is_correct_type,
                request_status_is("Delivered"),
            )
            new_fulfilled_request_count = len(model.all(formula=fulfilled_formula))

            fulfilled_request_data["metrics"].append(
                {
                    "name": name,
                    "translations": translations,
                    "value": old_fulfilled_request_count + new_fulfilled_request_count,
                }
            )

        self.log.info(
            f"Generated metrics:\n\tOPEN {open_request_data['metrics']}\n\tFULFILLED {fulfilled_request_data['metrics']}"
        )

        if params["dry_run"]:
            self.log.info("Dry run enabled. Skipping upload to digital ocean space.")
            return open_request_data, fulfilled_request_data
        self._write_data_to_s3(open_request_data, OPEN_REQUEST_FILEPATH)
        self.log.info(
            f"Uploaded open request data with updated ts: {now.isoformat()} to digital ocean space: {OPEN_REQUEST_FILEPATH}"
        )
        self._write_data_to_s3(fulfilled_request_data, FULFILLED_REQUEST_FILEPATH)
        self.log.info(
            f"Uploaded fulfilled request data from {start_date} to {end_date} to digital ocean space: {FULFILLED_REQUEST_FILEPATH}"
        )

        return open_request_data, fulfilled_request_data


if __name__ == "__main__":
    UpdateWebsiteRequestData().run_cli()
