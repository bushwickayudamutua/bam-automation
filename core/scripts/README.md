# BAM_Texting_Scripts

Python scripts for sending texts via [Twilio](https://pypi.org/project/twilio/).

### send_mass_text.py

This script pulls configurable lists of contacts and message content from Airtable and sends each contact a text in their configured language via Twilio.
#### Setup:
```
$ pip install -r requirements.txt
```

#### Credentials
Slack the #dev-team channel to request access to the Twilio and Airtable accounts. You'll need access to set up a `.env` file at the root directory with the expected credentials. Use the [sample.env](sample.env) file as a template.
```bash
$ cp sample.env .env
```


#### Usage

Follow [send_mass_text.sh](send_mass_text.sh) for an example!

In most cases, you should only need to configure the `airtable_contact_view_name` and the `airtable_text_message_name` in order to send a mass text, however all options are configurable via the command line. You must add the `--send` flag in order to use the Twilio API to send the messages, otherwise the script will run in test mode and simply print the messages to the console. If there is an unexpected Twilio error midway through a mass text, you can use the `airtable_contact_start_at` flag to resume the mass text at the record it initially failed at. This number is based off the indices (1-based) in the associated Airtable view.

```bash
Usage: send_mass_text.py [OPTIONS]

Options:
  --airtable_contact_url TEXT     The API Endpoint for the Table to pull the
                                  contact records from.  [default: https://api
                                  .airtable.com/v0/appEiw5APdZSlOwdm/Mass%20Te
                                  xt%20List]
  --airtable_contact_view_name TEXT
                                  The view which filters out just the Contacts
                                  to send this mass text to.  [required]
  --airtable_text_message_url TEXT
                                  The API Endpoint for the Table to pull the
                                  message content (by langauge) from.
                                  [default: https://api.airtable.com/v0/appEiw
                                  5APdZSlOwdm/Language%20for%20Mass%20Texts]
  --airtable_text_message_view_name TEXT
                                  The view which filters out just the message
                                  content (by langauge) for this mass text.
                                  [default: Language for Mass Texts]
  --airtable_text_message_name TEXT
                                  The value of the "Name" field for the
                                  message content.  [required]
  --airtable_contact_language_field TEXT
                                  The name of the column in the Contact view
                                  which contains the list of the Contact's
                                  languages spoken.  [default: Language]
  --airtable_contact_phone_number_field TEXT
                                  The name of the column in the Contact view
                                  which contains the the Contact's Phone
                                  number.  [default: Phone number]
  --airtable_text_message_language_field TEXT
                                  The name of the column in the message
                                  content view which contains the language of
                                  the message.  [default: Language]
  --airtable_text_message_content_field TEXT
                                  The name of the column in the message
                                  content view which contains the content for
                                  the message.  [default: Notes]
  --airtable_contact_start_at INTEGER
                                  The index number of Contact Records list to
                                  start at. Useful when resuming a mass text
                                  which breaks midway.
  --twilio_from_phone_number TEXT
                                  The twilio number to send the message from.
                                  Use the default for mass texts. Use
                                  +16468870083 to trigger the BAM Response
                                  Tracker  [default: +17185500340]
  --template_variables TEXT       JSON-formatted variables to pass into
                                  template strings in messages. Any string
                                  formatted {EXAMPLE} can be populated by
                                  passing '{"EXAMPLE": "test"}' at runtime.
  --send / --dont_send            Whether or not to send the text messages via
                                  Twilio's API
  --help                          Show this message and exit.                       Show this message and exit.
```

#### Troubleshooting/Data Pre-check

The error handling isn't too robust (yet) in these scripts so we'll want to pre-clean the data before running them

In the Airtable view that you are pulling records from we need to check a few things:

  1. Make sure that each record has a language. If a record doesn't have a language, we'll send a text using all languages in the `Language for Mass Texts` table. Longer messages incur greater costs from Twilio, so it's always better to send texts in a single, specific language.
  2. Take a quick glance down the phone number column for any weirdness. They should all be in the format `(###) ###-####`
     A quick scroll through them will make any oddities stand out, sometimes there are too many numbers `(###) ###-#####`, 
     or I've seen multiple numbers entered as `(###) ###-#### or (###) ###-####`, both of these will throw an error, though the script will continue.

General troubleshooting:
  1. If the script crashes mid-execution, check which index number it crashed on and pass it to the `--airtable_contact_start_at` flag.
  2. Filters applied to the table will affect what the script gets from the API, this has helped me do things like only send out texts in one language, only send out pickup texts, and a few other situations

Thats pretty much it! Slack BAM's #dev-team with any questions!.

### Contributing

#### Formatting
We use [Black](https://black.readthedocs.io/en/stable/) to auto format the python code. The idea is to spend less time on things like formatting and style and more time solving important problems. [Flake8](https://github.com/pycqa/flake8) is our linter, but most IDEs should support Black formatting on save, which should handle most of the linting errors.

A pre-commit hooks have been configured to run black and flake8 on every commit. Install them using the following:
```
$ pip install -r requirements.txt -r requirements_dev.txt
$ pre-commit install
```
Once black is installed, you can also run it manually:
```
$ black path_to_file.py
```
