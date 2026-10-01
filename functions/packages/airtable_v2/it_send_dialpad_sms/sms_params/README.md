## Input parameters for iterative mass texting with `ItSendDialpadSMS`

[it_sms_params.json](it_sms_params.json) is an example of DO input.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `view_name` | string | required | Airtable view to fetch Households from. |
| `distro_day` | string | required | Distro day, must be defined under `distro` in `message_template`. |
| `request_types` | list | required | EG items to text for, in order of priority. Must be defined in `request_label`. |
| `languages` | list | required | Languages to text in, in order of priority. Must be defined in `message_template` and `request_label`. |
| `volunteer` | list | required | Volunteer name, one value or one per language (in the order of `languages`). |
| `message_template` | json | | Overrides for [message_template.json](message_template.json). |
| `request_label` | json | | Overrides for [request_label.json](request_label.json). |
| `formula_filter` | string | | Airtable formula to filter the view. |
| `exclude_texted_today` | bool | `"True"` | Exclude Households texted today. |
| `max_messages` | int | `500` | Maximum number of messages to send. |
| `dry_run` | bool | `"True"` | Only log messages, don't send. |
| `verbose` | bool | `"True"` | Log the message per Household. |

**NOTE**
- Boolean parameters need to be provided in string format in DO input (`"True"` / `"False"`).
- Surrounding whitespace is stripped from all strings in `message_template` and `request_label`. Empty strings and lists are not allowed.

### Local run
Run from this function's directory with a config file in DO input format:
```
cd functions/packages/airtable_v2/it_send_dialpad_sms
python -m bam_core.functions.it_send_dialpad_sms --config-file sms_params/it_sms_params.json
```
Or with flags (can not be combined with `--config-file`, see `-h` for all flags):
```
python -m bam_core.functions.it_send_dialpad_sms -vn Main -dd Sunday -rt soap,clothing -la English -vo Zak
```

### `message_template`
[message_template.json](message_template.json) contains the default templates for SMS messages.

Currently supported languages:
`English`, `Spanish`, `Arabic`, `Chinese`

Currently supported distro days:
`Sunday`

Format per language:
- `languages`: list of Household `Languages` values texted with this template.
- `script`: message text with placeholders `[FIRST_NAME]`, `[VOLUNTEER]`, `[ITEM_LABEL]`, `[DAY]`, `[TIME]`, `[LOCATION]` (`[اسم]`, `[متطوع]`, `[المنتج]`, `[يوم]`, `[وقت]`, `[مكان]` in `Arabic`).
- `location`: distro address.
- `distro`: `day` and `time` per distro day.

**NOTE**
- All parameters provided by this file can be overridden using `message_template` input parameter. New languages and distro days can be added.
- Keys other than `languages`, `script`, `location`, `distro` (and `day`, `time` under each distro day) are not allowed.
- `location` must be provided by user. The following is an example of customizing distro address and time in Spanish:
```
"message_template": {
  "Spanish": {
    "location": "DISTRO ADDRESS HERE",
    "distro": {
      "Sunday": {
        "time": "entre las 11:30 am - 12:30 pm"
      }
    }
  }
}
```

### `request_label`
[request_label.json](request_label.json) contains the default EG item labels used in the SMS messages.

Currently supported languages:
`English`, `Spanish`, `Arabic`, `Chinese`

Currently supported EG items:
`baby_diapers`, `adult_diapers`, `clothing`, `soap`, `pads`, `school_supplies`, `pots_and_pans`, `plates_and_cups`, `soap_and_pads`

Format per EG item:
- `types`: list of Household `Open Request Types` values. Each must be a valid Requests `Type`.
- One label per language, e.g. `"English": "baby diapers"`.

**NOTE**
- All parameters provided by this file can be overridden using `request_label` input parameter. New EG items and languages can be added.
- If `capitalize` is true, the name of the item will be in all caps (in `English` & `Spanish`). This is false by default.
- Combinations of item types can be provided as a list, which will require the Household have an open request of every type. The earliest requested date (`Request Opened At`, via lookup field) of the first item will be used for sorting.
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
