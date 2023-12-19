# About

This function accomplishes the following task:

- For all records that have an `ESSENTIAL_GOODS_REQUEST`, add a "timeout" status to any unfulfilled records for phone numbers which have at least one fulfilled request.

### To Run
##### Via DigitalOcean Console
0) If you don't already have access to BAM DigitalOcean account, request access in the BAM Tech signal chat
1) In the DigitalOcean dashboard: Click on Manage > Functions on the lefthand navigation bar, then select the airtable/consolidate_eq_requests function
![](./assets/images/function_nav.png)

2) Click on `parameters`
![](./assets/images/function_params.png)

3) Update the following input

```json
{
  "ESSENTIAL_GOODS_REQUEST": "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品",
  "DRY_RUN": "this is optional. set to `True` when you just want to see the expected output without running updates"
}
```

1) Click the `run` button
![](./assets/images/function_run.png)

1) In the logs you should see a full list of the changes made and a summary of all changes.
![](./assets/images/function_logs.png)
