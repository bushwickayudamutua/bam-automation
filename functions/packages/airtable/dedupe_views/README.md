# About
This repo hosts the script for deduplicating Airtable records. Hopefully the following diagram makes the codeflow and how to add new views clear. But if you have any questions or find any errors, please do file an issue here or reach out in the tech Signal group chat.

![](../../../../assets/img/codeflow.png)


-----
### To run remotely
- Press run [here](https://cloud.digitalocean.com/functions/fn-515ead29-18f0-45aa-afd8-f52071501da8/airtable/dedupe_views/source?i=e47e47) to manually invoke
- See logs from the latest runs [here](https://cloud.digitalocean.com/functions/fn-515ead29-18f0-45aa-afd8-f52071501da8/logs?i=e47e47)


### To run locally
1) If you don't already have python 3.9+ installed: Follow the instructions [here](https://docs.python.org/3/using/) for your OS.
2) Retrieve the [Airtable API_KEY and APP_KEY](https://airtable.com/create/apikey) for the BAM account, and add them to your environment.
3) Run the following in your terminal application
   ```bash
   python __main__.py
   ```

-----
### Known bugs
- [x] `Error: Field "fldJyDIUCME5Y4Jcp" cannot accept the provided value.`
  - The field in question is "Essential Goods Request Status"
  - Should be investigated on case-by-case basis, but generally, the issue is that "`Essential Goods Request Status` has none of {timeout_flag}" filter was deselected on view. Reselect filter to fix.
- [x] `Script exceeded execution time limit of 30 seconds`
  - Move off airtable automation

### TODO
- Persist env vars between digitalocean redeploys
