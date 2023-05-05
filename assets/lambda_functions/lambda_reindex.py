import json, boto3, os

rekClient = boto3.client('rekognition')
sqsClient = boto3.client('sqs')

IOU_Threshold = 0.5


def bboxesProvided(ProvidedFaces):
    complete = True
    for face in ProvidedFaces:
        if len(face["BoundingBoxes"].keys()) != 4:
            complete = False
        if all(face["BoundingBoxes"].values()) == False:
            print("Missing bounding boxes")
            complete = False
            break
    return complete


def calculate_iou(bb1, bb2):
    bb1_x1, bb1_x2, bb1_y1, bb1_y2 = bb1["Left"], bb1["Left"] + bb1["Width"], bb1["Top"], bb1["Top"] + bb1["Height"]
    bb2_x1, bb2_x2, bb2_y1, bb2_y2 = bb2["Left"], bb2["Left"] + bb2["Width"], bb2["Top"], bb2["Top"] + bb2["Height"]
    x_left, y_top, x_right, y_bottom = max(bb1_x1, bb2_x1), max(bb1_y1, bb2_y1), min(bb1_x2, bb2_x2), min(bb1_y2,
                                                                                                          bb2_y2)
    if x_right < x_left or y_bottom < y_top: return 0
    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    bb1_area, bb2_area = (bb1_x2 - bb1_x1) * (bb1_y2 - bb1_y1), (bb2_x2 - bb2_x1) * (bb2_y2 - bb2_y1)
    iou = intersection_area / float(bb1_area + bb2_area - intersection_area)
    return iou


def rekogIndexFaces(bucket, key, collectionId, externalImageId):
    rek_response = rekClient.index_faces(
        CollectionId=collectionId,
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        ExternalImageId=externalImageId,
        QualityFilter=os.environ['qualityfilter']
    )
    return rek_response["FaceRecords"]


def sendResultstoDynamo(updatedRecords):
    sqs_response = sqsClient.send_message(
        QueueUrl=os.environ['dynamosqsurl'],
        MessageBody=json.dumps(updatedRecords),
        DelaySeconds=5,
    )

    print(sqs_response)
    print("Message Sent to DynamoDB queue")


def lambda_handler(event, context):
    for record in event['Records']:

        # Get SQS data
        payload = json.loads(record["body"])

        # Get the number of faces provided by the customer
        payloadFaces = payload["Faces"]

        ## Scenario 1. No faces are provided by the customer.
        if len(payloadFaces) == 0 or bboxesProvided(payloadFaces) == False:
            print("Faces Received: {}".format(len(payloadFaces)))
            print("Error, No faces provided by user or missing bounding boxes values")  # Raise error

        ## Scenario 2. One face is provided by the customer.
        elif len(payloadFaces) == 1:
            providedFace = payloadFaces[0]

            rekogIndexedFaces = rekogIndexFaces(  # Index faces with Rekognition.
                payload["Bucket"],
                payload["Key"],
                payload["CollectionId"],
                payload["ExternalImageId"])

            ## Scenario 2.1. Rekognition does not find any face to index
            ## Action 1: Raise Error
            if len(rekogIndexedFaces) == 0:
                print("Faces Received: {} -- Faces Indexed: {}".format(len(payloadFaces), len(rekogIndexedFaces)))
                print("Error, no faces found")  # Raise error

            ## Scenario 2.2. Rekognition indexes 1 face
            ## Action 1: Map face if iou is higher than 0.5
            elif len(rekogIndexedFaces) == 1:
                print("Faces Received: {} -- Faces Indexed: {}".format(len(payloadFaces), len(rekogIndexedFaces)))
                rekogIndexFace = rekogIndexedFaces[0]["Face"]
                iou = calculate_iou(providedFace["BoundingBoxes"], rekogIndexFace["BoundingBox"])
                if iou > IOU_Threshold:
                    updatedRecords = {
                        "Bucket": payload["Bucket"],
                        "Key": payload["Key"],
                        "ExternalImageId": payload["ExternalImageId"],
                        "Faces": [{
                            "UserID": providedFace["UserId"],
                            "OldFaceId": providedFace["FaceId"],
                            "OldImageId": providedFace["ImageId"],
                            "FaceId": rekogIndexFace["FaceId"],
                            "ImageId": rekogIndexFace["ImageId"],
                            "BoundingBoxes": rekogIndexFace["BoundingBox"],
                            "IsNewFace":False
                        }]
                    }

                else:
                    print("Not able to map face found")
                    updatedRecords = {
                        "Bucket": payload["Bucket"],
                        "Key": payload["Key"],
                        "ExternalImageId": payload["ExternalImageId"],
                        "Faces": [{
                            "UserID": "NewFace-{}".format(rekogIndexFace["FaceId"]),
                            "OldFaceId": "NewFace-{}".format(rekogIndexFace["FaceId"]),
                            "OldImageId": "NewFace-{}".format(rekogIndexFace["FaceId"]),
                            "FaceId": rekogIndexFace["FaceId"],
                            "ImageId": rekogIndexFace["ImageId"],
                            "BoundingBoxes": rekogIndexFace["BoundingBox"],
                            "IsNewFace":True
                        }]
                    }
                # Send records to Dynamo
                sendResultstoDynamo(updatedRecords)

            ## Scenario 2.3. Rekognition indexes more than 1 face
            ## Action 1: Map provided face to one of the indexed faces with the best iou
            ## Action 2: Notify new indexed faces
            elif len(rekogIndexedFaces) > 1:
                print("Faces Received: {} -- Faces Indexed: {}".format(len(payloadFaces), len(rekogIndexedFaces)))
                updatedRecords = {
                    "Bucket": payload["Bucket"],
                    "Key": payload["Key"],
                    "ExternalImageId": payload["ExternalImageId"],
                    "Faces": []
                }

                for indexedface in rekogIndexedFaces:
                    iou = calculate_iou(providedFace["BoundingBoxes"], indexedface["Face"]["BoundingBox"])
                    if iou > IOU_Threshold:
                        updatedRecords["Faces"].append({
                            "UserID": providedFace["UserId"],
                            "OldFaceId": providedFace["FaceId"],
                            "OldImageId": providedFace["ImageId"],
                            "FaceId": indexedface["Face"]["FaceId"],
                            "ImageId": indexedface["Face"]["ImageId"],
                            "BoundingBoxes": indexedface["Face"]["BoundingBox"],
                            "IsNewFace":False
                        })
                    else:
                        updatedRecords["Faces"].append({
                            "UserID": "NewFace-{}".format(indexedface["Face"]["FaceId"]),
                            "OldFaceId": "NewFace-{}".format(indexedface["Face"]["FaceId"]),
                            "OldImageId": "NewFace-{}".format(indexedface["Face"]["FaceId"]),
                            "FaceId": indexedface["Face"]["FaceId"],
                            "ImageId": indexedface["Face"]["ImageId"],
                            "BoundingBoxes": indexedface["Face"]["BoundingBox"],
                            "IsNewFace":True
                        })

                sendResultstoDynamo(updatedRecords)

        ## Scenario 3. More than one face is provided by the customer.
        elif len(payloadFaces) > 1:

            rekogIndexedFaces = rekogIndexFaces(  # Index faces with Rekognition.
                payload["Bucket"],
                payload["Key"],
                payload["CollectionId"],
                payload["ExternalImageId"]
            )

            ## Scenario 3.1. Rekognition does not find any face to index
            ## Action 1: Raise Error
            if len(rekogIndexedFaces) == 0:
                print("Faces Received: {} -- Faces Indexed: {}".format(len(payloadFaces), len(rekogIndexedFaces)))
                print("Error, no faces provided")  # Raise error

            ## Scenario 3.2. Rekognition only indexes one face
            ## Action 1: We try to map it to one of the input faces.
            ## Action 2: We save the other provided faces with "Not reindexed" and notify customer.
            ## Alternative: If there are more provided faces than rekognition can find, we raise an error.

            elif len(rekogIndexedFaces) == 1:
                print("Faces Received: {} -- Faces Indexed: {}".format(len(payloadFaces), len(rekogIndexedFaces)))
                rekogIndexedFace = rekogIndexedFaces[0]["Face"]

                updatedRecords = {
                    "Bucket": payload["Bucket"],
                    "Key": payload["Key"],
                    "ExternalImageId": payload["ExternalImageId"],
                    "Faces": []
                }

                for providedFace in payloadFaces:
                    iou = calculate_iou(providedFace["BoundingBoxes"], rekogIndexedFace["BoundingBox"])
                    if (iou > IOU_Threshold):
                        updatedRecords["Faces"].append({
                            "UserID": providedFace["UserId"],
                            "OldFaceId": providedFace["FaceId"],
                            "OldImageId": providedFace["ImageId"],
                            "FaceId": rekogIndexedFace["FaceId"],
                            "ImageId": rekogIndexedFace["ImageId"],
                            "BoundingBoxes": rekogIndexedFace["BoundingBox"],
                            "IsNewFace":False
                        })
                    else:
                        updatedRecords["Faces"].append({
                            "UserID": providedFace["UserId"],
                            "OldFaceId": providedFace["FaceId"],
                            "OldImageId": providedFace["ImageId"],
                            "FaceId": "Not reindexed",
                            "ImageId": "Not reindexed",
                            "BoundingBoxes": "Not reindexed"
                        })

                sendResultstoDynamo(updatedRecords)

            ## Scenario 3.3. Rekognition finds more than one face
            ## Action 1: Try to match all of the indexed faces by rekognition to the original input.
            ## Action 2: If new faces are discovered by rekog, we save them with "NewFaceIndexed"

            elif len(rekogIndexedFaces) > 1:
                print("Faces Received: {} -- Faces Indexed: {}".format(len(payloadFaces), len(rekogIndexedFaces)))
                updatedRecords = {
                    "Bucket": payload["Bucket"],
                    "Key": payload["Key"],
                    "ExternalImageId": payload["ExternalImageId"],
                    "Faces": []
                }

                for rekogIndexedFace in rekogIndexedFaces:
                    matchedFace = False
                    for providedFace in payloadFaces:
                        iou = calculate_iou(providedFace["BoundingBoxes"], rekogIndexedFace["Face"]["BoundingBox"])
                        if (iou > IOU_Threshold):
                            updatedRecords["Faces"].append({
                                "UserID": providedFace["UserId"],
                                "OldFaceId": providedFace["FaceId"],
                                "OldImageId": providedFace["ImageId"],
                                "FaceId": rekogIndexedFace["Face"]["FaceId"],
                                "ImageId": rekogIndexedFace["Face"]["ImageId"],
                                "BoundingBoxes": rekogIndexedFace["Face"]["BoundingBox"],
                                "IsNewFace":False
                            })
                            matchedFace = True
                            break
                    # If we cannot match the indexed face to any of the original input, notify the customer
                    if matchedFace == False:
                        updatedRecords["Faces"].append({
                            "UserID": "NewFace-{}".format(rekogIndexedFace["Face"]["FaceId"]),
                            "OldFaceId": "NewFace-{}".format(rekogIndexedFace["Face"]["FaceId"]),
                            "OldImageId": "NewFace-{}".format(rekogIndexedFace["Face"]["FaceId"]),
                            "FaceId": rekogIndexedFace["Face"]["FaceId"],
                            "ImageId": rekogIndexedFace["Face"]["ImageId"],
                            "BoundingBoxes": rekogIndexedFace["Face"]["BoundingBox"],
                            "IsNewFace":True
                        })

                sendResultstoDynamo(updatedRecords)

    return {
        'statusCode': 200,
        'body': json.dumps('Index Correct')
    }