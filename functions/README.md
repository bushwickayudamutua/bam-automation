# BAM's automation functions.

This folder contains all of BAM's automated functions which are deployed on Digital Ocean. If you haven't worked with Digital Ocean's Functions before, this [quickstart](https://docs.digitalocean.com/products/functions/getting-started/quickstart/) may be helpful.

Each function makes use of common code in [`bam-core`](../core/). More detail on this can be found below in the section on developing new functions.

## How to I deploy functions to Digital Ocean?

While [Github Actions](../.github/workflows/deploy.yml) is configured to deploy any code changes on each push to the `main` branch, you may from time-to-time want to deploy from your local machine:

First install the [Digital Ocean CLI](https://docs.digitalocean.com/reference/doctl/how-to/install/)

Next configure your local environment by copying [`.env.sample`](../.env.sample) in the root directory of this repository to `.env` and fill in the missing values:

```bash
cd ../
cp .env.sample .env
```

You should now be able to redeploy after code changes by running the following from the `bam-automation` directory (the root of this repository):

```bash
make deploy-functions
```

## How do I run functions?

### Locally

Each [function](../core/bam_core/functions) is first written as a simple python class inside of `bam-core` which inherits from the base `bam_core.functions.base.Function` class. You can run each function locally by calling it's module from the command line, eg:

```bash
python -m bam_core.functions.update_website_request_data -h
```

All functions should include a "Dry Run" mode (the `-dr` flag) which prevents any modifications from running.

### On Digital Ocean

To run a function after it's been deployed, ensure you've configured `doctl` according to the above steps, and then execute the following:

```bash
doctl serverless functions invoke <function_name>
doctl serverless functions invoke airtable/dedupe_views # e.g. for the dedupe_views function
```

You can also run functions from within [the cloud interface](https://cloud.digitalocean.com/functions/fn-515ead29-18f0-45aa-afd8-f52071501da8). This way, you don't have to check the logs/results using a second command.

## How do I develop a new function?

To develop a new function, you can start by copying from an existing example, for instance [`website/update_request_data`](packages/website/update_request_data/):

```bash
git checkout -b feature/my-new-function
mkdir -p packages/airtable/my_new_function
cp -R packages/website/update_request_data  packages/airtable/my_new_function
chmod +X packages/airtable/my_new_function/build.sh # make the build script executable
chmod 777 packages/airtable/my_new_function/build.sh # open the permissions for the build script
```

When naming a new function, try to group functions that work with particular data sources in in the same directory, and add new directories when new data sources are added. When a function accesses multiple data sources, put it in the directory of the data source it updates (for instance, `update_request_data` pulls from Airtable, but writes data to be access on our website).

### Where do I write my function's code?

To ensure that functions are testable, reusable, and portable, please add the code for your function to [`bam_core.functions`](../core/bam_core/functions/) and inherit from the base `bam_core.functions.base.Function` class. You can import this in your `__main__.py` file of your function's directory, eg:

```python
from bam_core.functions.update_website_request_data import UpdateWebsiteRequestData

main = UpdateWebsiteRequestData().run_do

```

You'll then write the logic for your function in `bam_core`.

Below is an example to get you started. You would save this file as `bam_core/functions/my_new_function.py`

```python
from typing import Dict, Any
from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param

class MyNewFunction(Function):

    params = Params(
        Param(
            name="dry_run",
            type="bool",
            description="If true, update operations will not be performed.",
            default=True,
        )
    )

    def run(self, params, context) -> Dict[str, Any]:
        # # do your thing here
        # access airtable/mailjet/s3:
        # self.airtable
        # self.mailjet
        # self.s3
        # # access event / cli parameters
        dry_run = params["dry_run"]
        self.log.info("Hello!")
        return {}


if __name__ == "__main__:
    MyNewFunction().run_cli()
```

**NOTE**: If your function is adding methods for accessing new services, or new methods for accessing existing services, consider adding those to [`bam_core.lib`](../core/bam_core/lib/) or [`bam_core.utils`](../core/bam_core/utils/) as a part of your work as it'll benefit others moving forward!

### How do I prepare a new function for deployment?

If your function only makes use of tools in `bam-core`, then you should be all set to go.

If your function has any required packages that aren't included in `bam-core`, you'll want to add them to a `requirements.txt` file and then modify the `build.sh` script to include this line:

```bash
pip install -r requirements.txt --target virtualenv/lib/python3.9/site-packages
```

This will install your requirements into the virtual environment that is packaged up as a part of your function.

Next, update [project.yml](./project.yml) to include your new function, following the existing format. If your function requires any sensitive data, you should access it via environment variables which can be set locally in your `.env` file and [the secrets settings for this repository](https://github.com/bushwickayudamutua/bam-automation/settings/secrets/actions). You'll also need to add this secret to github in order for it to be accessible during the build process.

Once you're done, you should be able to create a pull request for your changes. Once merged, they'll be deployed to Digital Ocean via Github Actions. Alternatively, you can follow the above directions on deploying functions locally.

## How do I schedule a function? 

Rather than adding a [scheduled trigger](https://docs.digitalocean.com/products/functions/how-to/schedule-functions/) for each function, we have two functions - [cron/daily](packages/cron/daily) and [cron/hourly](packages/cron/hourly/) which run multiple functions on a daily and hourly basis, respectively. This helps us get around Digital Ocean's quota of three scheduled triggers per account.  Add your function and call the `main` method to add it the schedule.

For example:

```python
from bam_core.functions.base import Function
from bam_core.functions.my_new_function import MyNewFunction

def main(event, context):
    return Function.run_do_functions(
        event,
        context,
        MyNewFunction
    )
```
