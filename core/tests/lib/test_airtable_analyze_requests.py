from bam_core.lib.airtable import Airtable
from bam_core.constants import (
    EG_REQUESTS_FIELD,
    EG_STATUS_FIELD,
    FOOD_REQUESTS_FIELD,
    FOOD_STATUS_FIELD,
    SOCIAL_SERVICES_REQUESTS_FIELD,
    SOCIAL_SERVICES_STATUS_FIELD,
    FOOD_MISSED_APPT_STATUS,
    EG_MISSED_APPT_STATUS,
    KITCHEN_REQUESTS_FIELD,
    NEW_BED_REQUESTS_FIELD,
    OLD_BED_REQUESTS_FIELD,
    FURNITURE_REQUESTS_FIELD,
)


def test_analyze_requests_simple():
    record = {
        "fields": {
            FOOD_REQUESTS_FIELD: [
                "Alimentos / Groceries / 食品",
                "Comida caliente / Hot meals / 热食",
            ],
            FOOD_STATUS_FIELD: [
                "Groceries Delivered",
                "Hot Food Request Timeout",
            ],
            EG_REQUESTS_FIELD: [
                "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品",
                "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾",
                "Pañales / Baby Diapers / 嬰兒紙尿褲",
            ],
            EG_STATUS_FIELD: [
                "Soap & Shower Products Delivered",
                "Soap & Shower Products Timeout",  # this should be ignored
                "Pads Timeout",
            ],
            SOCIAL_SERVICES_REQUESTS_FIELD: [
                "Clases de inglés / English Classes / 英語課",
                "Asistencia con beneficios de comida / Assistance with food benefits / 食品福利協助（WIC, SNAP, P-EBT）",
                "Asistencia asegurando vivienda/ Securing housing / 住房協助",
            ],
            SOCIAL_SERVICES_STATUS_FIELD: [
                "English Classes Signup, Confirmed by OBT",
                "No Longer Interested in Food Benefits",
                "Securing Housing Timeout",
            ],
        }
    }

    analysis = Airtable.analyze_requests(record)
    assert analysis[EG_REQUESTS_FIELD]["timeout"] == [
        "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾"
    ]
    assert analysis[EG_REQUESTS_FIELD]["delivered"] == [
        "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品"
    ]
    assert analysis[FOOD_REQUESTS_FIELD]["timeout"] == [
        "Comida caliente / Hot meals / 热食"
    ]
    assert analysis[EG_REQUESTS_FIELD]["open"] == [
        "Pañales / Baby Diapers / 嬰兒紙尿褲"
    ]
    assert analysis[FOOD_REQUESTS_FIELD]["delivered"] == [
        "Alimentos / Groceries / 食品"
    ]
    assert analysis[SOCIAL_SERVICES_REQUESTS_FIELD]["timeout"] == [
        "Asistencia asegurando vivienda/ Securing housing / 住房協助"
    ]
    assert analysis[SOCIAL_SERVICES_REQUESTS_FIELD]["delivered"] == [
        "Clases de inglés / English Classes / 英語課"
    ]
    assert analysis[SOCIAL_SERVICES_REQUESTS_FIELD]["invalid"] == [
        "Asistencia con beneficios de comida / Assistance with food benefits / 食品福利協助（WIC, SNAP, P-EBT）"
    ]


def test_analyze_requests_missed_appt():
    record = {
        "fields": {
            FOOD_REQUESTS_FIELD: [
                "Alimentos / Groceries / 食品",
            ],
            FOOD_STATUS_FIELD: [FOOD_MISSED_APPT_STATUS],
            EG_REQUESTS_FIELD: [
                "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品",
                "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾",
            ],
            EG_STATUS_FIELD: [
                EG_MISSED_APPT_STATUS,
            ],
        }
    }
    analysis = Airtable.analyze_requests(record)
    assert analysis[EG_REQUESTS_FIELD]["missed"] == [
        "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品",
        "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾",
    ]
    assert analysis[FOOD_REQUESTS_FIELD]["missed"] == [
        "Alimentos / Groceries / 食品"
    ]
    assert analysis[EG_REQUESTS_FIELD]["open"] == [
        "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品",
        "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾",
    ]
    assert analysis[FOOD_REQUESTS_FIELD]["open"] == [
        "Alimentos / Groceries / 食品"
    ]


def test_analyze_requests_no_status():
    record = {
        "fields": {
            FOOD_REQUESTS_FIELD: [
                "Alimentos / Groceries / 食品",
            ],
            EG_REQUESTS_FIELD: [
                "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品",
                "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾",
            ],
        }
    }
    analysis = Airtable.analyze_requests(record)
    assert analysis[EG_REQUESTS_FIELD]["open"] == [
        "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品",
        "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾",
    ]
    assert analysis[FOOD_REQUESTS_FIELD]["open"] == [
        "Alimentos / Groceries / 食品"
    ]


def test_analyze_requests_one_level_of_nesting():
    record = {
        "fields": {
            EG_REQUESTS_FIELD: [
                "Muebles / Furniture / 家具",
                "Cosas de Cocina / Kitchen Supplies / 廚房用品",
            ],
            FURNITURE_REQUESTS_FIELD: [
                "Cajonera / Clothes Dresser / 衣櫃",
                "Mesa Para Comedor / Dining Room Table / 餐桌",
            ],
            KITCHEN_REQUESTS_FIELD: [
                "Ollas y Sartenes / Pots & Pans / 鍋碗瓢盆",
                "Platos / Plates / 盤子",
            ],
            EG_STATUS_FIELD: [
                "Plates Timeout",
                "Pots & Pans Delivered",
                "Dining Table Timeout",
                "Dresser Delivered",
            ],
        }
    }
    analysis = Airtable.analyze_requests(record)
    assert analysis[FURNITURE_REQUESTS_FIELD]["timeout"] == [
        "Mesa Para Comedor / Dining Room Table / 餐桌"
    ]
    assert analysis[FURNITURE_REQUESTS_FIELD]["delivered"] == [
        "Cajonera / Clothes Dresser / 衣櫃"
    ]
    assert analysis[KITCHEN_REQUESTS_FIELD]["timeout"] == [
        "Platos / Plates / 盤子"
    ]
    assert analysis[KITCHEN_REQUESTS_FIELD]["delivered"] == [
        "Ollas y Sartenes / Pots & Pans / 鍋碗瓢盆"
    ]


def test_analyze_requests_two_levels_of_nesting_specific_delivered_tag():
    record = {
        "fields": {
            EG_REQUESTS_FIELD: [
                "Muebles / Furniture / 家具",
            ],
            FURNITURE_REQUESTS_FIELD: [
                "Cama / Bed / 床",
            ],
            NEW_BED_REQUESTS_FIELD: [
                "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
            ],
            EG_STATUS_FIELD: ["Queen Bed Set Delivered"],
        }
    }
    analysis = Airtable.analyze_requests(record)
    assert analysis[NEW_BED_REQUESTS_FIELD]["delivered"] == [
        "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
    ]


def test_analyze_requests_two_levels_of_nesting_parent_delivered_tag():
    record = {
        "fields": {
            EG_REQUESTS_FIELD: [
                "Muebles / Furniture / 家具",
            ],
            FURNITURE_REQUESTS_FIELD: [
                "Cama / Bed / 床",
            ],
            OLD_BED_REQUESTS_FIELD: [
                "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
            ],
            EG_STATUS_FIELD: ["Mattress Delivered"],
        }
    }
    analysis = Airtable.analyze_requests(record)
    assert analysis[NEW_BED_REQUESTS_FIELD]["delivered"] == [
        "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
    ]


def test_analyze_requests_two_levels_of_nesting_specific_timeout_tag():
    record = {
        "fields": {
            EG_REQUESTS_FIELD: [
                "Muebles / Furniture / 家具",
            ],
            FURNITURE_REQUESTS_FIELD: [
                "Cama / Bed / 床",
            ],
            NEW_BED_REQUESTS_FIELD: [
                "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
            ],
            EG_STATUS_FIELD: ["Queen Bed Set Timeout"],
        }
    }
    analysis = Airtable.analyze_requests(record)
    assert analysis[NEW_BED_REQUESTS_FIELD]["timeout"] == [
        "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
    ]


def test_analyze_requests_two_levels_of_nesting_parent_timeout_tag():
    record = {
        EG_REQUESTS_FIELD: [
            "Muebles / Furniture / 家具",
        ],
        FURNITURE_REQUESTS_FIELD: [
            "Cama / Bed / 床",
        ],
        OLD_BED_REQUESTS_FIELD: [
            "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
        ],
        EG_STATUS_FIELD: ["Mattress Timeout"],
    }
    analysis = Airtable.analyze_requests(record)
    assert analysis[NEW_BED_REQUESTS_FIELD]["timeout"] == [
        "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
    ]


def test_analyze_requests_two_levels_of_nesting_grandparent_timeout_tag():
    record = {
        "fields": {
            EG_REQUESTS_FIELD: [
                "Muebles / Furniture / 家具",
            ],
            FURNITURE_REQUESTS_FIELD: [
                "Cama / Bed / 床",
            ],
            NEW_BED_REQUESTS_FIELD: [
                "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
            ],
            EG_STATUS_FIELD: ["Furniture Timeout"],
        }
    }
    analysis = Airtable.analyze_requests(record)
    assert analysis[NEW_BED_REQUESTS_FIELD]["timeout"] == [
        "Cama tamaño Queen / Queen Mattress + Frame / 全床垫+框架"
    ]
