import boto3, json, os
sqsClient = boto3.client('sqs')

def lambda_handler(event, context):
    status = False

    validation_response = sqsClient.get_queue_attributes(
        QueueUrl=os.environ['validationsqsurl'],
        AttributeNames=[
            'ApproximateNumberOfMessages',
            'ApproximateNumberOfMessagesNotVisible'
            ]
    )

    total = int(validation_response["Attributes"]["ApproximateNumberOfMessages"]) + int(validation_response["Attributes"]["ApproximateNumberOfMessagesNotVisible"])

    if total == 0: status = True

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!'),
        'queuesAreEmpty':status
    }