from typing import TypedDict

# datetime format in Airtable
AIRTABLE_DATETIME_FORMAT = r"%Y-%m-%dT%H:%M:%S.%fZ"

# Airtable table/view names
ASSISTANCE_REQUESTS_TABLE_NAME = "Assistance Requests: Main"
VOLUNTEERS_TABLE_NAME = "Volunteers: Main"
ESSENTIAL_GOODS_TABLE_NAME = "Essential Good Donations: Main"
FULFILLED_REQUESTS_TABLE_NAME = "Fulfilled Requests: Main"

# Airtable field name for phone numbers
PHONE_FIELD = "Phone Number"

# Airtable field names for EG requests/statuses
EG_REQUESTS_FIELD = "Essential Goods Requests?"
EG_STATUS_FIELD = "Essential Goods Requests Status"
EG_MISSED_APPT_STATUS = "Missed EG Distro Appt"

# Airtable field names for food requests/statuses
FOOD_REQUESTS_FIELD = "Food Requests?"
FOOD_STATUS_FIELD = "Food Request Status"
FOOD_MISSED_APPT_STATUS = "Missed Food Distro Appt"

# Airtable field names for social services requests/statuses
SOCIAL_SERVICES_REQUESTS_FIELD = "Social Services Requests?"
SOCIAL_SERVICES_STATUS_FIELD = "Social Services Request Status"

# Kitchen Requests Field
KITCHEN_REQUESTS_FIELD = "Which Kitchen Items"

# Airtable field name for furniture requests
FURNITURE_REQUESTS_FIELD = "Which Furniture Items"

# Airtable field name for bed requests
BED_REQUESTS_FIELD = "Which Bed Size"

REQUEST_FIELDS = [
    PHONE_FIELD,
    EG_REQUESTS_FIELD,
    KITCHEN_REQUESTS_FIELD,
    FURNITURE_REQUESTS_FIELD,
    BED_REQUESTS_FIELD,
    EG_STATUS_FIELD,
    FOOD_REQUESTS_FIELD,
    FOOD_STATUS_FIELD,
    SOCIAL_SERVICES_REQUESTS_FIELD,
    SOCIAL_SERVICES_STATUS_FIELD,
]

# Mapping of bed requests to statuses
BED_REQUESTS_SCHEMA = {
    "request_field": BED_REQUESTS_FIELD,
    "status_field": EG_STATUS_FIELD,
    "items": {
        "Cuna / Crib / 婴儿床": {
            "delivered": "Crib Delivered",
            "timeout": "Crib Timeout",
        },
        "Colchón individual / Twin Mattress / 双人床垫": {
            "delivered": "Twin Mattress Delivered",
            "timeout": "Twin Mattress Timeout",
        },
        "Colchón matrimonio / Full Mattress / 全床垫": {
            "delivered": "Full Mattress Delivered",
            "timeout": "Full Mattress Timeout",
        },
        "Colchón tamaño Queen / Queen Mattress / 女王床垫": {
            "delivered": "Queen Mattress Delivered",
            "timeout": "Queen Mattress Timeout",
        },
        "Colchón tamaño King / King Mattress / 国王床垫": {
            "delivered": "King Mattress Delivered",
            "timeout": "King Mattress Timeout",
        },
        "Cama individual / Twin Mattress + Frame / 双人床垫+框架": {
            "delivered": "Twin Bed Set Delivered",
            "timeout": "Twin Bed Set Timeout",
        },
        "Cama matrimonio / Full Mattress + Frame / 完整的床垫和框架": {
            "delivered": "Full Bed Set Delivered",
            "timeout": "Full Bed Set Timeout",
        },
        "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架": {
            "delivered": "Queen Bed Set Delivered",
            "timeout": "Queen Bed Set Timeout",
        },
        "Cama tamaño King / King Mattress + Frame / 国王床垫+框架": {
            "delivered": "King Bed Set Delivered",
            "timeout": "King Bed Set Timeout",
        },
        "Bastidor individual / Twin Bed Frame 双人床垫框架": {
            "delivered": "Twin Bed Frame Delivered",
            "timeout": "Twin Bed Frame Timeout",
        },
        "Bastidor matrimonio / Full Bed Frame / 全床垫框架": {
            "delivered": "Full Bed Frame Delivered",
            "timeout": "Full Bed Frame Timeout",
        },
        "Bastidor tamaño Queen / Queen Bed Frame / 女王床垫框架": {
            "delivered": "Queen Bed Frame Delivered",
            "timeout": "Queen Bed Frame Timeout",
        },
        "Bastidor tamaño King / King Bed Frame / 国王床垫框架": {
            "delivered": "King Bed Frame Delivered",
            "timeout": "King Bed Frame Timeout",
        },
        "Litera / Loft or Bunk Bed": {
            "delivered": "Loft/Bunk Bed Delivered",
            "timeout": "Loft/Bunk Bed Timeout",
        },
    },
}

# Mapping of furniture requests to statuses.
# Note that bed requests are nested under furniture requests.
FURNITURE_REQUESTS_SCHEMA = {
    "request_field": FURNITURE_REQUESTS_FIELD,
    "status_field": EG_STATUS_FIELD,
    "items": {
        "Cama / Bed / 床": {
            "delivered": ["Mattress Delivered", "Bed Frame Delivered"],
            "timeout": ["Mattress Timeout", "Bed Frame Timeout"],
            "items": BED_REQUESTS_SCHEMA,
        },
        "Sofa / Sofa / 沙發": {
            "delivered": "Sofa Delivered",
            "timeout": "Sofa Timeout",
        },
        "Cajonera / Clothes Dresser / 衣服梳妆台": {
            "delivered": "Dresser Delivered",
            "timeout": "Dresser Timeout",
        },
        "Escritorio / Desk /  书桌": {
            "delivered": "Desk Delivered",
            "timeout": "Desk Timeout",
        },
        "Mesa de centro / Coffee Table / 咖啡桌": {
            "delivered": "Coffee Table Delivered",
            "timeout": "Coffee Table Timeout",
        },
        "Sillas / Chairs / 椅子": {
            "delivered": "Chairs Delivered",
            "timeout": "Chairs Timeout",
        },
        "Almacenamiento / Storage / 存储": {
            "delivered": "Storage Delivered",
            "timeout": "Storage Timeout",
        },
        "Mesa Para Comedor / Dining Room Table / 餐桌": {
            "delivered": "Dining Table Delivered",
            "timeout": "Dining Table Timeout",
        },
        "Nevera / Refrigerator / 冰箱": {
            "delivered": "Fridge Delivered",
            "timeout": "Fridge Timeout",
        },
        "Aire conditionador / Air Conditioner / 冷气机": {
            "delivered": "AC Delivered",
            "timeout": "AC Timeout",
        },
        "Otras / Other / 其他东西": {
            "delivered": "Other Furniture Delivered",
            "timeout": "Other Furniture Timeout",
        },
    },
}

# Mapping of kitchen requests to statuses
KITCHEN_REQUESTS_SCHEMA = {
    "request_field": KITCHEN_REQUESTS_FIELD,
    "status_field": EG_STATUS_FIELD,
    "items": {
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
            "delivered": "Kitchen Supplies Delivered",
            "timeout": "Kitchen Supplies Timeout",
        },
        "Licuadora / Blender / 攪拌機": {
            "delivered": "Blender / Food Processor Delivered",
            "timeout": "Blender / Food Processor Timeout",
        },
    },
}

# Mapping of EG requests to statuses
# Note that kitchen requests and furniture requests are nested under EG requests.
EG_REQUESTS_SCHEMA = {
    "request_field": EG_REQUESTS_FIELD,
    "status_field": EG_STATUS_FIELD,
    "items": {
        "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品": {
            "delivered": "Soap & Shower Products Delivered",
            "timeout": "Soap & Shower Products Timeout",
            "missed": EG_MISSED_APPT_STATUS,
        },
        "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾": {
            "delivered": "Pads Delivered",
            "timeout": "Pads Timeout",
            "missed": EG_MISSED_APPT_STATUS,
        },
        "Pañales / Baby Diapers / 婴儿纸尿裤": {
            "delivered": "Baby Diapers Delivered",
            "timeout": "Baby Diapers Timeout",
            "missed": EG_MISSED_APPT_STATUS,
        },
        "Pañales de adultos / Adult Diapers / 成人紙尿褲": {
            "delivered": "Adult Diapers Delivered",
            "timeout": "Adult Diapers Timeout",
            "missed": EG_MISSED_APPT_STATUS,
        },
        "Ropa / Clothing / 服装协助": {
            "delivered": "Clothing Assistance Delivered",
            "timeout": "Clothing Assistance Timeout",
            "missed": EG_MISSED_APPT_STATUS,
        },
        "Cosas de Escuela / School Supplies / 學校用品": {
            "delivered": "School Supplies Delivered",
            "timeout": "School Supplies Timeout",
            "missed": EG_MISSED_APPT_STATUS,
        },
        "Cosas de Cocina / Kitchen Supplies / 厨房用品": {
            "delivered": "Kitchen Supplies Delivered",
            "timeout": "Kitchen Supplies Timeout",
            "missed": EG_MISSED_APPT_STATUS,
            "items": KITCHEN_REQUESTS_SCHEMA,
        },
        "Muebles / Furniture / 家俱": {
            "delivered": "Furniture Delivered",
            "timeout": "Furniture Timeout",
            "missed": EG_MISSED_APPT_STATUS,
            "items": FURNITURE_REQUESTS_SCHEMA,
        },
        "Coche / Stroller / 婴儿车": {
            "delivered": "Stroller Delivered",
            "timeout": "Stroller Timeout",
            "missed": EG_MISSED_APPT_STATUS,
        },
        "Comida de mascota / Pet Food / 寵物食品": {
            "delivered": "Pet Food Delivered",
            "timeout": "Pet Food Timeout",
            "missed": EG_MISSED_APPT_STATUS,
        },
        "Historical: Mascaras / Masks / 口罩": {
            "delivered": "Masks Delivered",
            "timeout": "Masks Timeout",
            "missed": EG_MISSED_APPT_STATUS,
            "active": False,
        },
        "Historical: Productos Femenino - Tampones / Feminine Products - Tampons / 卫生棉条": {
            "delivered": "Tampons Delivered",
            "timeout": "Tampons Timeout",
            "missed": EG_MISSED_APPT_STATUS,
            "active": False,
        },
    },
}

FOOD_REQUESTS_SCHEMA = {
    "request_field": FOOD_REQUESTS_FIELD,
    "status_field": FOOD_STATUS_FIELD,
    "items": {
        "Alimentos / Groceries / 杂货": {
            "delivered": "Groceries Delivered",
            "timeout": "Groceries Request Timeout",
            "missed": FOOD_MISSED_APPT_STATUS,
        },
        "Comida caliente / Hot meals / 热食": {
            "delivered": "Hot Food Delivered",
            "timeout": "Hot Food Request Timeout",
        },
    },
}

SOCIAL_SERVICES_REQUESTS_SCHEMA = {
    "request_field": SOCIAL_SERVICES_REQUESTS_FIELD,
    "status_field": SOCIAL_SERVICES_STATUS_FIELD,
    "items": {
        "Asistencia legal de inmigración / Immigration legal assistance / 移民法律援助": {
            "delivered": "Immigration Assistance Delivered",
            "timeout": "Immigration Assistance Timeout",
        },
        "Asistencia legal de inquilinos / Tenant legal assistance / 租户法律援助": {
            "delivered": "Tenant Support Delivered - CUFFH",
            "timeout": "Tenant Legal Assistance Timeout",
        },
        "Asistencia con servicios escolares / Assistance with in-school services / 公立学校入学": {
            "delivered": "In School Services Assistance Delivered",
            "timeout": "In School Services Assistance Timeout",
        },
        "Tutoría estudiantil / Tutoring for students / 学生辅导": {
            "delivered": "Tutoring Assigned (K-12)",
            "timeout": "Tutoring Assistance Timeout",
        },
        "Clases de inglés / English Classes / 英语课": {
            "delivered": [
                "Referred to FeLT for English Classes",
                "English Classes Signup, Confirmed by OBT",
                "English Classes Signup, confirmed by DOE",
                "Registered for DOE ESL Classes",
                "ContraCovid - English Class Intake Scheduled",
            ],
            "timeout": "English Classes Timeout",
            "invalid": ["No Longer Interested - English Classes"],
        },
        "Asistencia asegurando vivienda/ Securing housing / 住房援助": {
            "delivered": [
                "Referred to Riseboro for Housing Assistance",
                "ContraCovid - Housing Intake Scheduled",
            ],
            "timeout": "Securing Housing Timeout",
        },
        "Asistencia con seguro médico / Medical insurance support / 医疗保健": {
            "delivered": [
                "Enrolled in Health Insurance - Metroplus",
                "Health Insurance Secured - HFNYC",
                "ContraCovid - Health Insurance Intake Scheduled",
            ],
            "timeout": "Health Insurance Assistance Timeout",
            "invalid": ["Already has Health Insurance"],
        },
        "Asistencia de Negocios / Small Business Support / 小型企业支持": {
            "delivered": "Small Business Support Delivered",
            "timeout": "Small Business Support Timeout",
        },
        "Internet de bajo costo en casa / Low-Cost Internet at home / 在家上网": {
            "delivered": "Low-Cost Internet Access Delivered",
            "timeout": "Low-Cost Internet Access TImeout",
        },
        "Asistencia con beneficios de comida / Assistance with food benefits / 协助 - WIC, SNAP, P-EBT": {
            "delivered": [
                "SNAP Signup Completed through WSCAH",
                "WIC Signup Completed through WSCAH",
                "ContraCovid - Food Benefits Intake Scheduled",
            ],
            "timeout": "Food Benefits Assistance Timeout",
            "invalid": [
                "No Longer Interested in Food Benefits",
                "Not Eligible for Food Benefits HFNYC",
                "Not Eligible for Food Benefits WSCAH",
                "Already has SNAP - WSCAH",
                "Already has P-EBT - HFNYC",
                "Already has SNAP - HFNYC",
                "Already has WIC - HFNYC",
                "Cannot Sign Up for Food Benefits - HFNYC",
            ],
        },
        "Asistencia con Transporte / Transportation Assistance": {
            "delivered": "MetroCard Delivered",
            "timeout": "MetroCard Request Timeout",
        },
        "Asistencia para niños discapacitados / Assistance for disabled children / 残疾儿童援助": {
            "delivered": "Child Disability Assistance Delivered",
            "timeout": "Child Disability Assistance Timeout",
        },
        "Asistencia para mascotas / Pet Assistance / 宠物协助": {
            "delivered": "Pet Assistance Delivered",
            "timeout": "Pet Assistance Timeout",
        },
    },
}

# Mappings for all requests
REQUESTS_SCHEMA = [
    FOOD_REQUESTS_SCHEMA,
    EG_REQUESTS_SCHEMA,
    SOCIAL_SERVICES_REQUESTS_SCHEMA,
]

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


# Geolocation constants

# location of mayday used to help lookup addresses
MAYDAY_LOCATION = {"lat": 40.7041015, "lng": -73.9163523}
MAYDAY_RADIUS = 16093.44  # 10 miles in meters
