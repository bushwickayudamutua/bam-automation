# bam-automation

Hi! Welcome to `bam-automation`. This repository contains code for syncing data between Bushwick Ayuda Mutua's services and performing routine and/or automated tasks. It contains three components, each of which contains a README with more information. If you're interested in helping us out with our efforts, fill our [our volunteer form](https://bushwickayudamutua.com/volunteer/) and select the `Tech and data support / Soporte técnico y de datos` working group. A volunteer coordinator will get in touch with shortly thereafter!

## Local Development Setup

You'll first need `python3.9` installed. If you're on a Mac, you can do this with [Homebrew](https://brew.sh/).

```
brew install python@3.9
```

Next you'll need to setup a virtual environment and install the dependencies for each subproject:

```
python3.9 -m venv .venv # create a virtualenv
source .venv/bin/activate # activate it
pip install -r requirements-dev.txt # install the development requirements
pip install -e ./core # install the bam-core library
pip install -r ./app/requirements.txt # install the automation API requirements
pip install -r ./notebooks/requirements.txt # install the notebook requirements
```

Finally, configure your local environment by copying [`.env.sample`](.env.sample) to `.env` and fill in the missing values. You'll need to ask someone in our Signal chat for access to these secrets:

```bash
cp .env.sample .env
```

### Subfolders
## [`app`](app/)
 This folder contains a [`fastapi`](https://fastapi.tiangolo.com/) application designed to provide additional functionality to Airtable automations via HTTP requests.

## [`core`](core/)

This folder contains a python module with reusable utilities for connecting and interacting with our tech services (Airtable, Dialpad, Twilio, Mailjet, Digital Ocean, etc). This module is automatically included in every function's virtual environment.

## [`functions`](functions/)

This folder contains code for [Digital Ocean Functions](https://www.digitalocean.com/products/functions) which can be run via:

- The [cloud interface](https://cloud.digitalocean.com/functions/fn-515ead29-18f0-45aa-afd8-f52071501da8?i=e47e47)
- The [API/CLI](https://docs.digitalocean.com/products/functions/reference/)
- Or [scheduled triggers](https://docs.digitalocean.com/products/functions/how-to/schedule-functions/), which are configured in the [project.yml](functions/project.yml) file.

These deploy automatically via [github actions](.github/workflows/actions.yml).

## [`notebooks`](notebooks/)

This folder contains jupyter notebooks for repeatable analysis of our airtable data.
