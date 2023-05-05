import boto3, json, os
sqsClient = boto3.client('sqs')

def lambda_handler(event, context):
    status = False
    
    reindex_response = sqsClient.get_queue_attributes(
        QueueUrl=os.environ['reindexsqsurl'],
        AttributeNames=[
            'ApproximateNumberOfMessages',
            'ApproximateNumberOfMessagesNotVisible'
            ]   
    )
    
    dynamo_response = sqsClient.get_queue_attributes(
        QueueUrl=os.environ['dynamosqsurl'],
        AttributeNames=[
            'ApproximateNumberOfMessages',
            'ApproximateNumberOfMessagesNotVisible'
            ]   
    )
    
    total = int(reindex_response["Attributes"]["ApproximateNumberOfMessages"]) + int(reindex_response["Attributes"]["ApproximateNumberOfMessagesNotVisible"]) + int(dynamo_response["Attributes"]["ApproximateNumberOfMessages"]) + int(dynamo_response["Attributes"]["ApproximateNumberOfMessagesNotVisible"])
    
    if total == 0: status = True
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!'),
        'queuesAreEmpty':status
    }