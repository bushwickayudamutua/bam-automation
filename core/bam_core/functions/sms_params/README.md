## Input parameters for iterative mass texting with `ItSendDialpadSMSV2`

**WORK IN PROGRESS**

### `message_template`
[message_template.json](message_template.json) contains the default templates for SMS messages.

Currently supported langueags:
`English`, `Spanish`, `Arabic`, `Chinese`

Currently supported distro days:
`Sunday`

**NOTE**
- All parameters provided by this file can be overriden using `message_template` input parameter.
- `location` is empty for privacy reasons and must be provided by user. The following is an example of customizing distro address and time in Spanish:
```
"message_template": {
  "Spanish": {
    "location": "DISTRO ADDRESS HERE",
    "Sunday": {
      "time": "entre las 11:30 am - 12:30 pm"
    }
  }
}
```

### `request_label`
[request_label.json](request_label.json) contains the default EG item labels used in the SMS messages.

Currently supported langueags:
`English`, `Spanish`, `Arabic`, `Chinese`

Currently supported EG items:
`baby_diapers`, `adult_diapers`, `clothing`, `soap`, `pads`, `school_supplies`, `pots_and_pans`, `plates_and_cups`, `soap_and_pads`

**NOTE**
- All parameters provided by this file can be overriden using `request_label` input parameter.
- If `capitalize` is true, the name of the item will be capitalized (in `English` & `Spanish`). This is false by default. Note that boolean variables need to be provided in string format in DO input.
- Combinations of item types can be provided as a list, which will require the Household have an open request of every type. The earliest requested date (`Request Opened At`) of the first item will be used for sorting.
- The following is an example of customizing `request_label` parameters:
```
"request_label" : {
    "capitalize": "True",

    "diapers_and_clothing": {
        "types": ["Pañales / Baby Diapers / 嬰兒紙尿褲", "Ropa / Clothing / 服裝"],
        "English": "baby diapers & clothing",
        "Spanish": "pañales y ropa",
        "Arabic": "حفاضات الأطفال و ملابس",
        "Chinese": "纸尿裤和衣服"
    }
}
```
