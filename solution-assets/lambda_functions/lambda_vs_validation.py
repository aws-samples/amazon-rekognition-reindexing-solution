import boto3
import json
import os
import botocore
#from jsonschema import validate, ValidationError

sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')
firehose_client = boto3.client('firehose')

def validate_s3(bucket, key):
    try:
        # Use head_object to check if the object exists
        response = s3_client.head_object(Bucket=bucket, Key=key)
        return True, None  # Successful validation, no specific reason
    except botocore.exceptions.ClientError as e:
        # If an exception is raised, the object does not exist
        if e.response['Error']['Code'] == '404':
            return False, "S3 validation failed: Object does not exist"
        else:
            return False, f"S3 validation failed: {str(e)}"

def validate_schema(record):
    expected_properties = ["Bucket", "Key", "ExternalImageId", "CollectionId"]

    for prop in expected_properties:
        if prop not in record:
            return False, record, f"Missing required property: {prop}"

        prop_type = type(record[prop]).__name__
        expected_type = "str"  # Modify as needed for other expected types

        if prop_type != expected_type:
            return False, record, f"Invalid type for property '{prop}': expected '{expected_type}', got '{prop_type}'"

    return True, record, None

def lambda_handler(event, context):
    success_items = []
    failed_items = []
    print("Records: {}".format(event['Records']))
    for record in event['Records']:
        # Get SQS data
        payload = json.loads(record["body"])

        # Validate against schema first
        schema_validation, _, schema_reason = validate_schema(payload)

        # Check if schema validation passes
        if schema_validation:
            # Proceed with S3 validation
            s3_validation, s3_reason = validate_s3(payload["Bucket"], payload["Key"])

            # Check if S3 validation passes
            if s3_validation:
                success_items.append(payload)
            else:
                failed_items.append({
                    "record": payload,
                    "reason": f"{s3_reason}." if s3_reason else ""
                })
        else:
            failed_items.append({
                "record": payload,
                "reason": f"Schema validation failed: {schema_reason}" if schema_reason else ""
            })

    # Send failed items to the alternative SQS queue with reasons
    if failed_items:
        print("failed items: {}".format(failed_items))
        firehose_delivery_stream = os.environ['kinesis_stream']
        for failed_item in failed_items:
            record = {'Data': json.dumps(failed_item) + '\n'}
            response = firehose_client.put_record(
                DeliveryStreamName=firehose_delivery_stream,
                Record=record
            )
        print(f"Sent failed item to Kinesis Firehose: {json.dumps(failed_item)}")

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
