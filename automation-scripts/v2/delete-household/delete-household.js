const { householdId } = input.config()

await base.getTable('Households').deleteRecordAsync(householdId)
