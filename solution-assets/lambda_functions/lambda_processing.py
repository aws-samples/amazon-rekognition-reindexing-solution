import boto3
import json
import os
import botocore

sqs_client = boto3.client('sqs')
s3_client = boto3.client('s3')
firehose_client = boto3.client('firehose')

def validate_s3(bucket, key):
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        if response['ContentLength'] == 0:
            return False, "S3 validation failed: Object has zero bytes"
        return True, None
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False, "S3 validation failed: Object does not exist"
        return False, f"S3 validation failed: {str(e)}"

def validate_schema(item):
    expected_properties = {"Bucket", "Key", "ExternalImageId", "CollectionId"}
    missing_props = expected_properties - set(item.keys())
    if missing_props:
        return False, item, f"Missing required properties: {', '.join(missing_props)}"

    for prop, value in item.items():
        if prop in expected_properties and not isinstance(value, str):
            return False, item, f"Invalid type for property '{prop}': expected 'str', got '{type(value).__name__}'"

    return True, item, None

def process_items(items):
    success_items = []
    failed_items = []
    for item in items:
        schema_validation, validated_item, schema_reason = validate_schema(item)
        if schema_validation:
            s3_validation, s3_reason = validate_s3(validated_item["Bucket"], validated_item["Key"])
            if s3_validation:
                success_items.append(validated_item)
            else:
                failed_items.append({"record": validated_item, "reason": s3_reason})
        else:
            failed_items.append({"record": item, "reason": schema_reason})
    return success_items, failed_items

def lambda_handler(event, context):
    if "Items" in event:
        items = event["Items"]
    else:
        items = [event]

    success_items, failed_items = process_items(items)

    sqsURL = os.environ['reindexsqsurl']
    for item in success_items:
        sqs_client.send_message(QueueUrl=sqsURL, MessageBody=json.dumps(item), DelaySeconds=1)
        print(f"Sent valid record to SQS: {json.dumps(item)}")

    if failed_items:
        print("failed items: {}".format(failed_items))
        firehose_delivery_stream = os.environ['kinesis_stream']
        for failed_item in failed_items:
            record = {'Data': json.dumps(failed_item) + '\n'}
            firehose_client.put_record(DeliveryStreamName=firehose_delivery_stream, Record=record)
            print(f"Sent failed item to Kinesis Firehose: {json.dumps(failed_item)}")

    return {'statusCode': 200, 'body': json.dumps('Hello from Lambda!')}