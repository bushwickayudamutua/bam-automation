This is a work in progress! The goal is to automate the process of filtering AirTable records for mass texting by DialPad.
- `outreach.py` filters the "Essential Goods" table based on user-defined parameters in `outreach_params.yaml` and saves csv tables per item and language.
- `update_last_auto_texted.py` updates the last auto texted date to today's date, given a csv table created by `outreach.py`.
