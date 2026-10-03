## Input parameters for iterative mass texting with `ItSendDialpadSMS`

[it_sms_params_example.json](it_sms_params_example.json) is an example of DO input, but can also be used for CLI as `--config-file`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `view_name` | string | required | Airtable view to fetch Households from. |
| `distro_day` | string | required | Distro day, must be defined under `distro` in `message_template`. |
| `request_types` | list | required | EG items to text for, in order of priority. Must be defined in `request_label`. |
| `languages` | list | required | Languages to text in, in order of priority. Must be defined in `message_template` and `request_label`. |
| `volunteer` | list | required | Volunteer name, either one value used for every language, or one per language in the same order as `languages`. |
| `message_template` | json | | Overrides the defaults in [message_template.json](message_template.json). |
| `request_label` | json | | Overrides the defaults in [request_label.json](request_label.json). |
| `exclude_texted_today` | bool | `"True"` | Exclude Households texted today. |
| `max_messages` | int | `500` | Maximum number of messages to send. |
| `dry_run` | bool | `"True"` | Run in testing mode without sending Dialpad messages. |
| `verbose` | bool | `"True"` | Log the message per Household. |

**NOTE**
- Households will be sorted by the earliest requested date (`Request Opened At`, via lookup) of the EG items, in the order of priority, and up to `max_messages` will be selected.
- Boolean parameters need to be provided in string format in DO input (`"True"` / `"False"`).
- Surrounding whitespace is stripped from all strings in `message_template` and `request_label`. Empty strings and lists are not allowed.

### Local run
Run from this function's directory with a config file in DO input format:
```
export PYTHONPATH="${PYTHONPATH}:$(pwd)/core/"
cd functions/packages/airtable_v2/it_send_dialpad_sms/

python3 -m bam_core.functions.it_send_dialpad_sms \
    --config-file sms_params/it_sms_params_example.json
```
Or with flags (can not be combined with `--config-file`, see `-h` for all flags):
```
python -m bam_core.functions.it_send_dialpad_sms \
    -vn Main -dd Sunday -rt soap,clothing -la Spanish -vo Zak
```

### `message_template`
[message_template.json](message_template.json) contains the default templates for SMS messages.

Currently supported languages:
`English`, `Spanish`, `Arabic`, `Chinese`

Currently supported distro days:
`Sunday`

Format per language:
- `languages`: list of Household `Languages` texted with this template. This is a single value except for `Chinese`, which incldues Mandarin, Cantose, and Toishanese.
- `script`: message text with placeholders `[FIRST_NAME]`, `[VOLUNTEER]`, `[REQUEST_LABEL]`, `[DAY]`, `[TIME]`, `[LOCATION]` (or `[اسم]`, `[متطوع]`, `[المنتج]`, `[يوم]`, `[وقت]`, `[مكان]` in `Arabic`).
- `location`: distro address. This is empty by default for security, so it must always be provided for every language and day.
- `distro`: `day` and `time` per distro day.
- Keys other than `languages`, `script`, `location`, `distro` (and `day`, `time` under each distro day) are not allowed.

**NOTE**
- All parameters provided by this file can be overridden using `message_template` input parameter to DO (or `--config-file`). New languages and distro days can be added.
- The following is an example of customizing distro address and time in Spanish:
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

- If `capitalize` is true, the name of the item will be in all caps (in `English` & `Spanish`). This is false by default.
- Format per EG item:
  - `types`: list of Requests `Type` in the Household `Open Request Types`. If more than one provided (e.g. `soap_and_pads`), it selects households that have an open request for all types. The earliest requested date (`Request Opened At`, via lookup) of the first item will be used for sorting.
  - One label per language, e.g. `"English": "baby diapers"`.

**NOTE**
- All parameters provided by this file can be overridden using `request_label` input parameter to DO (or `--config-file`). New EG items and languages can be added.
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
