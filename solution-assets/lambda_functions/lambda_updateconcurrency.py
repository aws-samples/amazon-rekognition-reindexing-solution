import os
import boto3
import json

# Initialize AWS clients
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    # Get the function name and the limit from environment variables
    function_name = os.environ['FUNCTION_NAME']
    max_concurrency_limit = int(os.environ['MAX_CONCURRENCY_LIMIT'])

    # Get the event source mappings for the function
    event_source_mappings = lambda_client.list_event_source_mappings(FunctionName=function_name)['EventSourceMappings']

    # Initialize the response
    response = {
        'updated_mappings': [],
        'skipped_mappings': []
    }

    # Iterate over each event source mapping
    for mapping in event_source_mappings:
        # Check if ScalingConfig.MaximumConcurrency is below the limit
        if mapping.get('ScalingConfig', {}).get('MaximumConcurrency') is None or mapping['ScalingConfig']['MaximumConcurrency'] < max_concurrency_limit:
            # Calculate the new MaximumConcurrency value
            new_max_concurrency = min(max_concurrency_limit, mapping['ScalingConfig'].get('MaximumConcurrency', 0) + 50)

            # Update the event source mapping
            lambda_client.update_event_source_mapping(
                UUID=mapping['UUID'],
                FunctionName=function_name,
                ScalingConfig={
                    'MaximumConcurrency': new_max_concurrency
                }
            )

            # Add the updated mapping to the response
            response['updated_mappings'].append({
                'UUID': mapping['UUID'],
                'new_max_concurrency': new_max_concurrency
            })
        else:
            # Add the skipped mapping to the response
            response['skipped_mappings'].append({
                'UUID': mapping['UUID'],
                'current_max_concurrency': mapping['ScalingConfig']['MaximumConcurrency']
            })

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }