import json, boto3, os

dynClient = boto3.client('dynamodb')

def lambda_handler(event, context):
    for record in event['Records']:
        print("Reading record")
        print("--------------")

        # Get SQS data
        payload = json.loads(record["body"])
        print(payload)
        
        for face in payload["Faces"]:
            dynamoitem = {
                'Bucket': {'S': str(payload["Bucket"])},
                'Key': {'S': str(payload["Key"])},
                'ExternalImageId': {'S': str(payload["ExternalImageId"])},
                'UserID': {'S': str(face["UserID"])},
                'FaceId': {'S': str(face["FaceId"])},
                'OldFaceId': {'S': str(face["OldFaceId"])},
                'OldImageId': {'S': str(face["OldImageId"])},
                'ImageId': {'S': str(face["ImageId"])},
                'BoundingBoxes':{'S': json.dumps(face["BoundingBoxes"])}
            }
            
            if "IsNewFace" in face:
                dynamoitem.update({'IsNewFace':{'S': str(face["IsNewFace"])}})

            response = dynClient.put_item(
                TableName=os.environ["dynamoTable"],
                Item=dynamoitem)
            print(response)

    return {
        'statusCode': 200,
        'body': json.dumps('Results sent to Dynamo')
    }