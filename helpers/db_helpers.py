# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

#    http://aws.amazon.com/asl/

# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.
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
