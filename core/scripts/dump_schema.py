import csv

from bam_core.constants import REQUESTS_SCHEMA
from bam_core.utils.etc import to_list

# write out a csv with the following columns:
# request_type, tag, delivered_tags (separated by line breaks), timeout tags (separated by line breaks)

def write_schema(
    writer,
    schema = {},
    parent_request_field = None,
    parent_status_field = None,
):
    request_field = schema['request_field']
    status_field = schema['status_field']
    for request_tag, item in schema['items'].items():
        if 'items' in item:
            write_schema(
                writer = writer,
                schema = item['items'],
                parent_request_field = request_field,
                parent_status_field = status_field,
            )
        writer.writerow({
            'request_field': request_field,
            'status_field': status_field,
            'parent_request_field': parent_request_field,
            'parent_status_field': parent_status_field,
            'request_tag': request_tag,
            'delivered_tags': '\n\n'.join(to_list(item.get('delivered', []))),
            'timeout_tags': '\n\n'.join(to_list(item.get('timeout', []))),
            "invalid_tags": '\n\n'.join(to_list(item.get('invalid', []))),
            "missed_tags": '\n\n'.join(to_list(item.get('missed', []))),
        })

if __name__ == '__main__':
    columns = ['request_field', 'status_field', 'parent_request_field', 'parent_status_field', 'request_tag', 'delivered_tags', 'timeout_tags', 'invalid_tags', 'missed_tags']
    writer = csv.DictWriter(open('schema.csv', 'w'), fieldnames=columns)
    writer.writeheader()
    print("wrtiting schema to schema.csv")
    for schema in REQUESTS_SCHEMA:
        write_schema(writer, schema=schema)
