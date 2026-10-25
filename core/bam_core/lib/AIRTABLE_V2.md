# BAM Assistance Requests (airtable_v2) ORM reference

This is the reference for the pyairtable ORM models in [`airtable_v2.py`](airtable_v2.py), each corresponding to a table in Airtable base "BAM Assistance Requests". Please see the [Airtable Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs) for more details about each table and its fields.

**Work in progress**
- Documentation of automations [here](../../../automation-scripts/v2/README.md).
- Documentation of function `send_dialpad_sms_v2.py` [here](../../../functions/packages/airtable_v2/send_dialpad_sms/README.md).
- Full review of field descriptions below.
- Updating documentation of `Notes` and `Other requests and comments` fields for **Assistance Request Form Submissions**, **Households**, and automations.

## Tables

- [**Assistance Request Form Submissions**](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:assistance%20request%20form%20submissions): This is a table where request form submissions land, temporarily, before they're parsed into household and request records described below.
- [**Households**](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:households): Each row in this table is a household's profile.
- [**Requests**](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:requests): Each row in this table is an essential goods request linked to a household.
- [**Furniture Requests**](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:furniture%20requests): Each row in this table is a furniture request linked to a household.
- [**Social Service Requests**](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:social%20service%20requests): Each row in this table is a social service request linked to a household.
- [**Mesh Requests**](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:mesh%20requests): Each row in this table is a MESH request linked to a household.
- [**Fulfilled Request Count**](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:fulfilled%20request%20count): Each row in this table is a date with the number of delivered requests of each type.

## Automations

The following Airtable automations maintain the database and process households and their requests. Please find more details about automations [here](../../../automation-scripts/v2/README.md).

**Intake**
- `[On Create] Write form submission to household, request tables` runs when a new request form submission record is created, cleans up the contact information via API ([FastAPI app](../../../app/bam_app/main.py)), creates a household and its request records, and deletes the form submission record.
- `[On Create] Merge households`: Each household is represented by a unique phone number. When a new household is created, and if there is an existing household with that phone number, their profiles and requests are consolidated. There is only one open request of each type, per household, and new requests are merged into older open requests.

**Cleanup**
- `[At 23:45 EST] Count and delete older closed records`: All delivered/timed-out requests are deleted after a number of days, and delivered requests of each type are counted.
- `[When Requests empty] Delete household`: A household is deleted if it's not linked to any request records.

**Update**
- `[On Update] Merge households on phone # update`: Each household is represented by a unique phone number. When a household's phone number is updated and cleaned up via API, and if there is an existing household with that phone number, their profiles and requests are consolidated. There is only one open request of each type, per household, and duplicate requests are merged into the older one.
- `[On Update] Merge mesh request on address update`: MESH requests are identified by a household and a unique building identification number (BIN). When a household's address is updated and cleaned up via API, and they already have an open request for that BIN, open MESH requests are merged into the older one.
- `[On Update] Clean email address`: When a household's email is updated, it is cleaned up via API.

**Interface**
- `[On Button Press] Time out household's open EG requests`: This is an interface button to time out all open EG requests from a household.

## Functions

- **SMS**: Dialpad SMS functions ([`send_dialpad_sms_v2.py`](../functions/send_dialpad_sms_v2.py) and [`it_send_dialpad_sms.py`](../functions/it_send_dialpad_sms.py), which rely on [`dialpad.py`](dialpad.py)) are used via Digital Ocean (or CLI) to mass text an Airtable view of the Households table. More details on how to use `it_send_dialpad_sms.py` [here](../../../functions/packages/airtable_v2/it_send_dialpad_sms/README.md) and `send_dialpad_sms_v2.py` [here](../../../functions/packages/airtable_v2/send_dialpad_sms/README.md).

## Assistance Request Form Submissions

ORM class: `FormSubmission` · Table ID: `tbl4ZZUeYCQyUq8Xo`

| Airtable field | ORM variable | Description / definition | Touched by |
|---|---|---|---|
| ID (autoNumber) | `bam_id` (AutoNumberField) |  | — |
| Name (singleLineText) | `name` (TextField) |  | — |
| Phone Number (phoneNumber) | `phone_number` (PhoneNumberField) |  | Intake (R†) |
| Email (email) | `email` (EmailField) |  | Intake (R†) |
| Languages (multipleSelects) | `languages` (MultipleSelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:assistance%20request%20form%20submissions). | — |
| Other Languages (multilineText) | `other_languages` (MultilineTextField) |  | — |
| Notes (richText) | `notes` (RichTextField) |  | — |
| Street Address (singleLineText) | `street_address` (TextField) |  | Intake (R†) |
| City, State (singleLineText) | `city_and_state` (TextField) |  | Intake (R†) |
| Zip Code (number) | `zip_code` (NumberField) |  | Intake (R†) |
| Request Types (multipleSelects) | `request_types` (MultipleSelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:assistance%20request%20form%20submissions). | Intake (R†) |
| Furniture Acknowledgement (checkbox) | `furniture_acknowledgement` (CheckboxField) |  | — |
| Furniture Items (multipleSelects) | `furniture_items` (MultipleSelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:assistance%20request%20form%20submissions). | Intake (R†) |
| Bed Details (multipleSelects) | `bed_details` (MultipleSelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:assistance%20request%20form%20submissions). | Intake (R†) |
| Social Service Requests (multipleSelects) | `ss_request_types` (MultipleSelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:assistance%20request%20form%20submissions). | Intake (R†) |
| Internet Access (multipleSelects) | `internet_access` (MultipleSelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:assistance%20request%20form%20submissions). | Intake (R†) |
| Roof Accessible? (checkbox) | `roof_is_accessible` (CheckboxField) |  | — |
| Created At (createdTime) | — |  | — |
| Should Merge (formula) | — | Formula → checkbox: `DATETIME_DIFF(NOW(), {Created At}, 'seconds') >= 30` | — |

## Households

ORM class: `Household` · Table ID: `tbl4nhEmNKhwTvIgT`

| Airtable field | ORM variable | Description / definition | Touched by |
|---|---|---|---|
| ID (autoNumber) | `bam_id` (AutoNumberField) |  | — |
| Name (singleLineText) | `name` (TextField) |  | Merge households (W), SMS (R) |
| Phone Number (phoneNumber) | `phone_number` (PhoneNumberField) | Cleaned by `/clean-record` (US format). | Intake (W†), Merge households (R†, W†), SMS (R) |
| Invalid Phone Number? (checkbox) | `phone_is_invalid` (CheckboxField) | Set from `/clean-record`: checked when the phone number is missing or not a valid number. | Intake (W†), Merge households (W) |
| Int'l Phone Number? (checkbox) | `phone_is_intl` (CheckboxField) | Set from `/clean-record`: checked when the phone number is valid and has a non-US country code. | Intake (W†), Merge households (W) |
| Email (email) | `email` (EmailField) | Cleaned by `/clean-record` (`email_validator` with DNS check). | Intake (W†), Clean email (R†, W†), Merge households (W) |
| Email Error (singleLineText) | `email_error` (TextField) | Set from `/clean-record`: the validation error, or `No email address provided` when blank. | Intake (W†), Clean email (W†), Merge households (W) |
| Languages (multipleSelects) | `languages` (MultipleSelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:households). | Merge households (W), SMS (R) |
| Other Languages (multilineText) | `other_languages` (MultilineTextField) | Other languages not listed on the form | Merge households (W) |
| Notes (richText) | `notes` (RichTextField) |  | Merge households (W) |
| Legacy First Date Submitted (date) | `legacy_first_date_submitted` (DateField) |  | — |
| Legacy Last Date Submitted (date) | `legacy_last_date_submitted` (DateField) |  | — |
| Last Texted (date) | `last_texted` (DateField) | Set to today's date after a successful (non-dry-run) SMS send. | SMS (R, W) |
| Last Called (date) | `last_called` (DateField) |  | — |
| Needs Delivery (checkbox) | `needs_delivery` (CheckboxField) | This household requires services delivered to their home. | Merge households (W) |
| Needs Email Outreach (checkbox) | `needs_email_outreach` (CheckboxField) | This person prefers outreach via email. | Merge households (W) |
| Open Request Types (multipleLookupValues) | `open_request_types` (LookupField) | Lookup via `{Requests}` of `Requests.Type`<br>Filter (inferred): `Status = Open` | SMS (R) |
| Baby Diapers Requested At (multipleLookupValues) | `baby_diapers_requested_at` (LookupField) | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Pañales / Baby Diapers / 嬰兒紙尿褲` | SMS (R) |
| Adult Diapers Requested At (multipleLookupValues) | `adult_diapers_requested_at` (LookupField) | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Pañales de adultos / Adult Diapers / 成人紙尿褲` | SMS (R) |
| Clothing Requested At (multipleLookupValues) | `clothing_requested_at` (LookupField) | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Ropa / Clothing / 服裝` | SMS (R) |
| Soap Requested At (multipleLookupValues) | `soap_requested_at` (LookupField) | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品` | SMS (R) |
| Pads Requested At (multipleLookupValues) | `pads_requested_at` (LookupField) | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾` | SMS (R) |
| School Supplies Requested At (multipleLookupValues) | `school_supplies_requested_at` (LookupField) | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Cosas de Escuela / School Supplies / 學校用品` | SMS (R) |
| Pots & Pans Requested At (multipleLookupValues) | `pots_and_pans_requested_at` (LookupField) | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Ollas y Sartenes / Pots & Pans / 鍋碗瓢盆` | SMS (R) |
| Plates & Cups Requested At (multipleLookupValues) | `plates_and_cups_requested_at` (LookupField) | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Platos o Tazas / Plates or Cups / 盘子或杯子` | SMS (R) |
| Other Requests and Comments (multilineText) | — | Input from form submission | — |
| Requests (multipleRecordLinks) | — | Link to `Requests` | Merge households (R, W) |
| Delivered Request Types (multipleLookupValues) | — | Lookup via `{Requests}` of `Requests.Type`<br>Filter (inferred): `Status = Delivered` | — |
| Furniture Requests (multipleRecordLinks) | — | Link to `Furniture Requests` | Merge households (R, W) |
| Open Furniture Request Types (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Type`<br>Filter (inferred): `Status = Open` | — |
| Delivered Furniture Request Types (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Type`<br>Filter (inferred): `Status = Delivered` | — |
| Social Service Requests (multipleRecordLinks) | — | Link to `Social Service Requests` | Merge households (R, W) |
| Open Social Service Request Types (multipleLookupValues) | — | Lookup via `{Social Service Requests}` of `Social Service Requests.Type`<br>Filter (inferred): `Status = Open` | — |
| Delivered Social Service Request Types (multipleLookupValues) | — | Lookup via `{Social Service Requests}` of `Social Service Requests.Type`<br>Filter (inferred): `Status = Delivered` | — |
| Mesh Requests (multipleRecordLinks) | — | Link to `Mesh Requests` | Merge households (R, W) |
| Created At (formula) | — | Date of request submission (Creation date for new submissions, and "Legacy First Date Submitted" for migrated households)<br>Formula → date: `IF({Legacy First Date Submitted}, {Legacy First Date Submitted}, CREATED_TIME())` | Merge households (R) |
| Updated At (lastModifiedTime) | — | Last modified time of any field | — |
| Appointment Date (date) | — |  | — |
| Appointment Time (singleSelect) | — | Appointment time slot, in 30-minute steps (e.g. `10:00 AM`, `10:30 AM`). | — |
| Appointment Status (singleSelect) | — | One of `Pending`, `Booked`, `Checked-in`, `Missed`. | — |
| Utensils Requested At (multipleLookupValues) | — | Lookup via `{Requests}` of `Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Utensilios / Utensils / 餐具` | — |
| MESH Requested At (multipleLookupValues) | — | Lookup via `{Mesh Requests}` of `Mesh Requests.Request Opened At`<br>Filter: `Status = Open`; sorted by `Request Opened At` (earliest first) and limited to the first record, i.e. the earliest open request date (a household can have multiple open Mesh requests, unique by `Building Identification Number`) | — |
| Tutoring Requested At (multipleLookupValues) | — | Lookup via `{Social Service Requests}` of `Social Service Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Tutoría estudiantil / Tutoring for students / 學生輔導` | — |
| English Classes Requested At (multipleLookupValues) | — | Lookup via `{Social Service Requests}` of `Social Service Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Clases de inglés / English Classes / 英語課` | — |
| Asistencia para niños con discapacidad (multipleLookupValues) | — | Lookup via `{Social Service Requests}` of `Social Service Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Asistencia para niños con discapacidad / Assistance for disabled children / 殘疾兒童協助` | — |
| Medical Insurance Assistance Requested At (multipleLookupValues) | — | Lookup via `{Social Service Requests}` of `Social Service Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Asistencia con seguro médico / Medical insurance support / 醫療保險協助` | — |
| Sofa Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Sofa / Sofa / 沙發` | — |
| Dresser Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Cajonera / Clothes Dresser / 衣櫃` | — |
| Desk Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Escritorio / Desk / 書桌` | — |
| Coffee Table Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Mesa de centro / Coffee Table / 咖啡桌` | — |
| Chairs Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Sillas / Chairs / 椅子` | — |
| Storage Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Almacenamiento / Storage / 儲物櫃` | — |
| Dining Table Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Mesa Para Comedor / Dining Room Table / 餐桌` | — |
| Refrigerator Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Nevera / Refrigerator / 冰箱` | — |
| AC Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Aire conditionador / Air Conditioner / 空調` | — |
| Bed Frame Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type` is any of the 8 types with "Frame" in the name; sorted by `Request Opened At` (earliest first) and limited to the first record, i.e. the earliest open request date | — |
| Mattress Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type` is any of the 8 types with "Mattress" in the name; sorted by `Request Opened At` (earliest first) and limited to the first record, i.e. the earliest open request date | — |
| Crib Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Cuna / Crib / 嬰兒床` | — |
| Bunk Bed Requested At (multipleLookupValues) | — | Lookup via `{Furniture Requests}` of `Furniture Requests.Request Opened At`<br>Filter: `Status = Open`, `Type = Litera / Loft or Bunk Bed / 閣樓床或上下床` | — |

## Requests

ORM class: `Request` · Table ID: `tbl36vstoygz75JnJ`

| Airtable field | ORM variable | Description / definition | Touched by |
|---|---|---|---|
| Household (multipleRecordLinks) | `household` (SingleLinkField) | Link to `Households` | Merge households (W, via the Households link fields) |
| Status (singleSelect) | `status` (SelectField) | One of `Open`, `Timeout`, `Delivered`. | Count closed (R), Website (R) |
| Last Requested (dateTime) | `last_requested` (DatetimeField) | Last request form submission for the item (regardless of how long request has been open) | Intake (W), Merge households (W) |
| Legacy Date Submitted (date) | `legacy_date_submitted` (DateField) | Date of request submission in the old base | — |
| Request Opened At (formula) | `request_opened_at` (DateField, read-only) | Date of request submission (Creation date for new submissions, and "Legacy Date Submitted" for migrated requests)<br>Formula → date: `IF({Legacy Date Submitted}, {Legacy Date Submitted}, CREATED_TIME())` | Merge households (R) |
| Type (singleSelect) | `type` (SelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:requests:fields). | Intake (W), Merge households (R), Count closed (R), Website (R) |
| Label (formula) | — | Formula → singleLineText: `{Type}` | — |
| Updated At (lastModifiedTime) | — | Last modified time of any field | — |
| Status Last Updated At (lastModifiedTime) | — | Last modified time of `{Status}` | Count closed (R) |
| Processing Date (formula) | — | Formula → date: `IF( {Status} != 'Open', DATEADD( {Status Last Updated At}, SWITCH( {Status}, 'Delivered', SWITCH( {Type}, 'Ollas y Sartenes / Pots & Pans / 鍋碗瓢盆', 30, 14 ), 14 ), 'days' ) )`<br>Only set once the request leaves `Open` (`Delivered` or `Timeout`): `Status Last Updated At` plus a number of days. Empty for open requests. | — |

## Furniture Requests

ORM class: `FurnitureRequest` · Table ID: `tblHL2GkNY9f98DjS`

| Airtable field | ORM variable | Description / definition | Touched by |
|---|---|---|---|
| Household (multipleRecordLinks) | `household` (SingleLinkField) | Link to `Households` | Merge households (W, via the Households link fields) |
| Status (singleSelect) | `status` (SelectField) | One of `Open`, `Timeout`, `Delivered`. | Count closed (R), Website (R) |
| Last Requested (dateTime) | `last_requested` (DatetimeField) | Last request form submission for the item (regardless of how long request has been open) | Intake (W), Merge households (W) |
| Legacy Date Submitted (date) | `legacy_date_submitted` (DateField) | Date of request submission in the old base | — |
| Request Opened At (formula) | `request_opened_at` (DateField, read-only) | Date of request submission (Creation date for new submissions, and "Legacy Date Submitted" for migrated requests)<br>Formula → date: `IF({Legacy Date Submitted}, {Legacy Date Submitted}, CREATED_TIME())` | Merge households (R) |
| Type (singleSelect) | `type` (SelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:furniture%20requests). | Intake (W), Merge households (R), Count closed (R), Website (R) |
| Geocode (singleLineText) | `geocode` (TextField) | Google Plus Code of the cleaned address, from `/clean-record`. Empty if the API call fails or no plus code is found. | Intake (W), Merge households (W) |
| Label (formula) | — | Formula → singleLineText: `{Type}` | — |
| Updated At (lastModifiedTime) | — | Last modified time of any field | — |
| Status Last Updated At (lastModifiedTime) | — | Last modified time of `{Status}` | Count closed (R) |
| Processing Date (formula) | — | Formula → date: `IF( {Status} != 'Open', DATEADD({Status Last Updated At}, 60, 'days') )`<br>Only set once the request leaves `Open` (`Delivered` or `Timeout`): `Status Last Updated At` plus a number of days. Empty for open requests. | — |

## Social Service Requests

ORM class: `SocialServiceRequest` · Table ID: `tblr81hk68OA7G7XB`

| Airtable field | ORM variable | Description / definition | Touched by |
|---|---|---|---|
| Household (multipleRecordLinks) | `household` (SingleLinkField) | Link to `Households` | Merge households (W, via the Households link fields) |
| Status (singleSelect) | `status` (SelectField) | One of `Open`, `Timeout`, `Delivered`. | Count closed (R) |
| Last Requested (dateTime) | `last_requested` (DatetimeField) | Last request form submission for the item (regardless of how long request has been open) | Intake (W), Merge households (W) |
| Legacy Date Submitted (date) | `legacy_date_submitted` (DateField) |  | — |
| Request Opened At (formula) | `request_opened_at` (DateField, read-only) | Earliest open request (Creation time for new submissions, and "Legacy Date Submitted" for migrated requests)<br>Formula → date: `IF({Legacy Date Submitted}, {Legacy Date Submitted}, CREATED_TIME())` | Merge households (R) |
| Type (singleSelect) | `type` (SelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:social%20service%20requests). | Intake (W), Merge households (R), Count closed (R) |
| Label (formula) | — | Formula → singleLineText: `{Type}` | — |
| Partner Org (multipleSelects) | — | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:social%20service%20requests). | Merge households (W) |
| Status Last Updated At (lastModifiedTime) | — | Last modified time of `{Status}` | Count closed (R) |
| Updated At (lastModifiedTime) | — | Last modified time of any field | — |
| Processing Date (formula) | — | Formula → date: `IF( {Status} != 'Open', DATEADD({Status Last Updated At}, 60, 'days') )`<br>Only set once the request leaves `Open` (`Delivered` or `Timeout`): `Status Last Updated At` plus a number of days. Empty for open requests. | — |

## Mesh Requests

ORM class: `MeshRequest` · Table ID: `tbljXi3yblCy0sOTR`

| Airtable field | ORM variable | Description / definition | Touched by |
|---|---|---|---|
| Household (multipleRecordLinks) | `household` (SingleLinkField) | Link to `Households` | Merge households (W, via the Households link fields) |
| Status (singleSelect) | `status` (SelectField) | One of `Open`, `Timeout`, `Delivered`. | Count closed (R) |
| Last Requested (dateTime) | `last_requested` (DatetimeField) | Last request form submission for the item (regardless of how long request has been open) | Intake (W), Merge households (W), Merge mesh (W) |
| Legacy Date Submitted (date) | `legacy_date_submitted` (DateField) |  | — |
| Request Opened At (formula) | `request_opened_at` (DateField, read-only) | Earliest open request (Creation time for new submissions, and "Legacy Date Submitted" for migrated requests)<br>Formula → date: `IF({Legacy Date Submitted}, {Legacy Date Submitted}, CREATED_TIME())` | Merge households (R), Merge mesh (R) |
| MESH History (multilineText) | `mesh_history` (MultilineTextField) |  | Merge households (W), Merge mesh (W) |
| Internet Access (multipleSelects) | `internet_access` (MultipleSelectField) | Options: see the [Web API docs](https://airtable.com/appjIo54Z8MWrqhlI/api/docs#curl/table:mesh%20requests). | Intake (W), Merge households (W), Merge mesh (W) |
| Address (singleLineText) | `address` (TextField) | Cleaned address from `/clean-record` ([`geo.py`](../utils/geo.py)): Google Places + Address Validation, USPS-standardized. If the API call fails, falls back to the raw form address (street, city, zip joined). | Intake (W), Merge households (W), Merge mesh (W, W†) |
| Address Accuracy (singleSelect) | `address_accuracy` (SelectField) | Set from `/clean-record` ([`geo.py`](../utils/geo.py)) to `Apartment`, `Building`, or `No result`, only when the clean step succeeded. `Address Outside NY` and `Invalid Address Provided` are not set by code in this repo (the merge scripts rank them lowest). | Intake (W), Merge households (R, W), Merge mesh (R, W, W†) |
| Building Identification Number (number) | `building_identification_number` (NumberField) | Looked up from NYC Planning Labs by `/clean-record` ([`geo.py`](../utils/geo.py)); only set when `Address Accuracy` is not `No result` and the BIN is not a placeholder (`1000000`, `3000000`). A household can have one open Mesh request per BIN. | Intake (W), Merge households (R), Merge mesh (W†) |
| Street Address (singleLineText) | `street_address` (TextField) | Raw value from the form submission. | Intake (W), Merge households (W), Merge mesh (R†, W) |
| City, State (singleLineText) | `city_and_state` (TextField) | Raw value from the form submission. | Intake (W), Merge households (W), Merge mesh (R†, W) |
| Zip Code (number) | `zip_code` (NumberField) | Raw value from the form submission. | Intake (W), Merge households (W), Merge mesh (R†, W) |
| Status Last Updated At (lastModifiedTime) | — | Last modified time of `{Status}` | Count closed (R) |
| Updated At (lastModifiedTime) | — | Last modified time of any field | — |
| Processing Date (formula) | — | Formula → date: `IF( {Status} != 'Open', DATEADD({Status Last Updated At}, 60, 'days') )`<br>Only set once the request leaves `Open` (`Delivered` or `Timeout`): `Status Last Updated At` plus a number of days. Empty for open requests. | — |
| ID (autoNumber) | — |  | — |

## Fulfilled Request Count

Raw table (no ORM class), exposed as `count_table` · Table ID: `tbl1nGWv6LKA7nX21`

Daily counts of delivered requests, one record per `Date`.

| Airtable field | ORM variable | Description / definition | Touched by |
|---|---|---|---|
| Date (date) | — | The date the counted requests were closed (each request's `Status Last Updated At`). Created by `count-closed-requests.js` if no record exists for that date. | Count closed (R, W), Website (R) |

All other fields are `number` count columns, one per request type (see below). They are written by Count closed and read by Website.

- **Written by** the Airtable automation script [`count-closed-requests.js`](../../../automation-scripts/v2/count-closed-requests/count-closed-requests.js). For each request passed in by the automation (from `Requests`, `Furniture Requests`, `Social Service Requests`, and `Mesh Requests`), it finds (or creates) the count record whose `Date` equals the request's `Status Last Updated At`, adds 1 to the matching count column if the request's `Status` is `Delivered`, and then deletes the request.
- **Count columns** are named after the middle (English) part of the request's `Type`, e.g. `Ropa / Clothing / 服裝` → `Clothing`. Mesh requests always count toward `Low-Cost Home Internet`. Requests whose `Type` has no matching column are not processed: they are neither counted nor deleted, and are reported in the script's `invalidCountCols` output.
- **Read by** [`update_website_request_data.py`](../functions/update_website_request_data.py), which fetches the records from the last 31 days and sums the columns in each metric's `count_columns` to build the website's fulfilled-request metrics.
