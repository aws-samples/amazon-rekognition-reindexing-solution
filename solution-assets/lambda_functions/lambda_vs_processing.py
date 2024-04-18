import boto3, json, os
sqsClient = boto3.client('sqs')

def lambda_handler(event, context):
    print(event)
    if "Items" in event:
        for item in event["Items"]:
            print(item)
            sqsURL = os.environ['validationsqsurl']
            response = sqsClient.send_message(
                QueueUrl=sqsURL,
                MessageBody=json.dumps(item),
                DelaySeconds=1
            )
    else:
        sqsURL = os.environ['validationsqsurl']
        response = sqsClient.send_message(
            QueueUrl=sqsURL,
            MessageBody=json.dumps(event),
            DelaySeconds=1
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
