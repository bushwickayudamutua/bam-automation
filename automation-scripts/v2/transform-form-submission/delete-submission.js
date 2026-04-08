const { formSubId } = input.config()

await base.getTable('Assistance Request Form Submissions').deleteRecordAsync(formSubId)

