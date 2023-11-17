BAM's Automation API
=====

This application is designed to house APIs which can be called from within Airtable via HTTP requests.

Currently, it has the following endpoints:

* `/clean-record`:
  * Cleans, formats, and performs DNS checks on email address domains via `email-formatter`.
  * Cleans and formats phone numbers via `phonenumbers`
  * Parameters:
    * `apikey`: An apikey to provide security
    * `email`: The email address to validate
    * `phone`: The phone number to validate
    * `dns_check`: Whether or not to perform a dns check (defaults to `false`)


## How do I install this locally?

Follow the setup guide in the [README](../README.md) of this repository, then run the tests to confirm everything is working:


```bash
pytest -vv . # run the tests
```

## How do I run this locally?

### via docker

From the root of the repository run

```
docker compose build && docker-compose up
```

You should now have a version of the API running at http://localhost:3030

### via python

After following the installation instructions above, run the following:

```
uvicorn bam_app.main:app --reload --port 3030 --host 0.0.0.0
```
