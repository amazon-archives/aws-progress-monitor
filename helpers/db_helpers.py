import boto3


def does_table_exist(table_name):
    table_exists = False
    try:
        client = boto3.client('dynamodb')
        client.describe_table(TableName=table_name)
        table_exists = True

    except Exception as exception:
        if "Requested resource not found: Table" in str(exception):
            table_exists = False

    return table_exists


def validate_table(table_name, create_table):
    if (not does_table_exist(table_name)):
        create_table()
