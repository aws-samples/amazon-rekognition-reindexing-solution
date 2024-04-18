import json
import os
import boto3

def lambda_handler(event, context):
    # Get the S3 bucket and key from the event
    s3_bucket = event['Records'][0]['s3']['bucket']['name']
    s3_key = event['Records'][0]['s3']['object']['key']

    # Define your Step Functions state machine ARN
    state_machine_arn = os.environ['statemachinearn']

    # Create Step Functions client
    stepfunctions = boto3.client('stepfunctions')

    # Start execution of the Step Functions state machine
    response = stepfunctions.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps({"bucket": s3_bucket, "key": s3_key, "res_prefix":"validation-results/execution"})
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Execution started successfully!')
    }
