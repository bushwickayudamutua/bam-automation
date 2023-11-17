from typing import TypedDict

# datetime format in Airtable
AIRTABLE_DATETIME_FORMAT = r"%Y-%m-%dT%H:%M:%S.%fZ"

# Airtable table/view names
ASSISTANCE_REQUESTS_TABLE_NAME = "Assistance Requests: Main"
VOLUNTEERS_TABLE_NAME = "Volunteers: Main"
ESSENTIAL_GOODS_TABLE_NAME = "Essential Good Donations: Main"
MESH_VIEW_NAME = "MESH - Pending installs, by address (Lu)"

# Airtable field name for phone numbers
PHONE_FIELD = "Phone Number"

# Airtable field names for EG requests/statuses
EG_REQUESTS_FIELD = "Essential Goods Requests?"
EG_STATUS_FIELD = "Essential Goods Requests Status"

# a mapping of EG requests/statuses
EG_REQUESTS_SCHEMA = {
    "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品": {
        "delivered": "Soap & Shower Products Delivered",
        "timeout": "Soap & Shower Products Timeout",
    },
    "Productos Femenino - Toallitas / Feminine Products - Pads / 卫生巾": {
        "delivered": "Pads Delivered",
        "timeout": "Pads Timeout",
    },
    "Pañales / Baby Diapers / 婴儿纸尿裤": {
        "delivered": "Baby Diapers Delivered",
        "timeout": "Baby Diapers Timeout",
    },
    "Pañales de adultos / Adult Diapers / 成人纸尿裤": {
        "delivered": "Baby Diapers Delivered",
        "timeout": "Baby Diapers Timeout",
    },
    "Ropa / Clothing / 服装协助": {
        "delivered": "Clothing Assistance Delivered",
        "timeout": "Clothing Assistance Timeout",
    },
    "Cosas de Escuela / School Supplies / 学校用品": {
        "delivered": "School Supplies Delivered",
        "timeout": "School Supplies Timeout",
    },
    "Cosas de Cocina / Kitchen Supplies / 厨房用品": {
        "delivered": "Kitchen Supplies Delivered",
        "timeout": "Kitchen Supplies Timeout",
    },
    "Muebles / Furniture / 家俱": {
        "delivered": "Furniture Delivered",
        "timeout": "Furniture Timeout",
    },
    "Historical: Mascaras / Masks / 口罩": {
        "delivered": "Masks Delivered",
        "timeout": "Masks Timeout",
        "active": False,
    },
    "Historical: Productos Femenino - Tampones / Feminine Products - Tampons / 卫生棉条": {
        "delivered": "Tampons Delivered",
        "timeout": "Tampons Timeout",
        "active": False,
    },
}

KITCHEN_REQUESTS_SCHEMA = {
    "Microondas / Microwave / 微波": {
        "delivered": "Microwave Delivered",
        "timeout": "Microwave Timeout",
    },
    "Ollas y Sartenes / Pots & Pans / 锅碗瓢盆": {
        "delivered": "Pots & Pans Delivered",
        "timeout": "Pots & Pans Timeout",
    },
    "Platos / Plates / 板块": {
        "delivered": "Plates Delivered",
        "timeout": "Plates Timeout",
    },
    "Tazas / Cups / 杯具": {
        "delivered": "Cups Delivered",
        "timeout": "Cups Timeout",
    },
    "Utensilios / Utensils / 餐具": {
        "delivered": "Utensils Delivered",
        "timeout": "Utensils Timeout",
    },
    "Cafetera / Coffee Maker / 咖啡机": {
        "delivered": "Coffee Maker Delivered",
        "timeout": "Coffee Maker Timeout",
    },
    "Otras / Other / 其他东西": {
        "delivered": None,
        "timeout": None,
    },
    "Licuadora / Blender / 攪拌機": {
        "delivered": "Blender / Food Processor Delivered",
        "timeout": "Blender / Food Processor Timeout",
    },
}


# Airtable Views
# These are used in the dedupe_views automation.


class View(TypedDict):
    name: str
    status_field_name: str
    timeout_flag_value: str


MESH_VIEW_NAME = "MESH - Pending installs, by address (Lu)"

FOOD_VIEWS = [
    View(
        name="Food Distro - Open Groceries requests",
        status_field_name="Food Request Status",
        timeout_flag_value="Groceries Request Timeout",
    ),
    View(
        name="Food Distro - Open Hot Food requests",
        status_field_name="Food Request Status",
        timeout_flag_value="Hot Food Request Timeout",
    ),
]

CLOTHING_VIEWS = [
    View(
        name="Essential Goods: Clothing Requests",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Clothing Assistance Timeout",
    ),
]

FURNITURE_VIEWS = [
    View(
        name="Essential Goods: AC",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="AC Timeout",
    ),
    View(
        name="Essential Goods: Desks",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Desk Timeout",
    ),
    View(
        name="Essential Goods: King Beds",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Furniture Timeout",
    ),
    View(
        name="Essential Goods: Queen Beds",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Furniture Timeout",
    ),
    View(
        name="Essential Goods: Full Beds",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Furniture Timeout",
    ),
    View(
        name="Essential Goods: Twin Beds",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Furniture Timeout",
    ),
    View(
        name="Essential Goods: Cribs",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Furniture Timeout",
    ),
]

SCHOOL_SUPPLIES_VIEWS = [
    View(
        name="Essential Goods: School Supplies",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="School Supplies Timeout",
    ),
]

KITCHEN_VIEWS = [
    View(
        name="Essential Goods: Refrigerators",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Fridge Timeout",
    ),
    View(
        name="Essential Goods: Microwaves",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Microwave Timeout",
    ),
    View(
        name="Essential Goods: Pots & Pans",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Pots & Pans Timeout",
    ),
    View(
        name="Essential Goods: Plates + Cups",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Kitchen Supplies Timeout",
    ),
]

TOILETRIES_VIEWS = [
    View(
        name="Essential Goods: Pads",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Pads Timeout",
    ),
    View(
        name="Essential Goods: Baby Diapers",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Baby Diapers Timeout",
    ),
    View(
        name="Essential Goods: Adult Diapers",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Adult Diapers Timeout",
    ),
    View(
        name="Essential Goods: Soap & Shower Products",
        status_field_name="Essential Goods Requests Status",
        timeout_flag_value="Soap & Shower Products Timeout",
    ),
]

SOCIAL_SERVICES_VIEWS = [
    View(
        name="Social Services: WIC / SNAP / P-EBT",
        status_field_name="Social Services Request Status",
        timeout_flag_value="Food Benefits Assistance Timeout",
    ),
    View(
        name="Social Services: K-12 Assistance",
        status_field_name="Social Services Request Status",
        timeout_flag_value="In School Services Assistance Timeout",
    ),
    View(
        name="Social Services: Immigration Legal Assistance",
        status_field_name="Social Services Request Status",
        timeout_flag_value="Immigration Assistance Timeout",
    ),
    View(
        name="Social Services: Housing Assistance",
        status_field_name="Social Services Request Status",
        timeout_flag_value="Tenant Legal Assistance Timeout",
    ),
    View(
        name="Social Services: Health Insurance",
        status_field_name="Social Services Request Status",
        timeout_flag_value="Health Insurance Assistance Timeout",
    ),
    View(
        name="Social Services: Low-Cost Internet Access",
        status_field_name="Social Services Request Status",
        timeout_flag_value="Low-Cost Internet Access TImeout",
    ),
    View(
        name="Social Services: Small Business Support",
        status_field_name="Social Services Request Status",
        timeout_flag_value="Small Business Support Timeout",
    ),
    View(
        name="Social Services: English Classes",
        status_field_name="Social Services Request Status",
        timeout_flag_value="English Classes Timeout",
    ),
    View(
        name="Social Services: Disabled children",
        status_field_name="Social Services Request Status",
        timeout_flag_value="Child Disability Assistance Timeout",
    ),
]

VIEWS: list[View] = (
    FOOD_VIEWS
    + CLOTHING_VIEWS
    + FURNITURE_VIEWS
    + KITCHEN_VIEWS
    + TOILETRIES_VIEWS
    + SOCIAL_SERVICES_VIEWS
    + SCHOOL_SUPPLIES_VIEWS
    # + OTHER_VIEWS
)

# # Uncomment to test with a single view
# VIEWS: list[View] = [
#     View(
#         name="Atty view",
#         status_field_name="Food Request Status",
#         timeout_flag_value="Groceries Request Timeout",
#     )
# ]
