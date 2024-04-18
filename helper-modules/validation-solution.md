# Reindex Data Validator

To ensure the reindexing process works correctly and at its maximum capacity, it is essential that we reduce the possible AWS Lambda errors.

Before sending the records for processing, we should validate that the submitted data adheres to the required schema, and verify that the images exist in the specified bucket and key.

Due to the potential volume of records ranging from hundreds to millions, we have developed a scalable solution to validate your records file. This solution follows the same architecture as the reindexing solution.



## Solution Architecture

![Architecture](images/rvs-architecture.png)

## Solution Deployment

The solution is already packaged into an AWS CloudFormation template. AWS CloudFormation is a service that helps you model and set up your AWS resources so that you can spend less time managing those resources and more time focusing on your applications that run in AWS.

Launch one of the following AWS CloudFormation Templates in your account (The link will automatically open the AWS CloudFormation console).
- [Launch solution in N.Virginia - us-east-1](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://rkra-us-east-1.s3.us-east-1.amazonaws.com/validation-assets/template.yaml&stackName=remember-only-lowercase&unique)
- [Launch solution in Oregon - us-west-2](https://us-west-2.console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/create/review?templateURL=https://rkra-us-west-2.s3.us-west-2.amazonaws.com/validation-assets/template.yaml&stackName=remember-only-lowercase&unique)
- [Launch solution in Ireland - eu-west-1](https://eu-west-1.console.aws.amazon.com/cloudformation/home?region=eu-west-1#/stacks/create/review?templateURL=https://rkra-eu-west-1.s3.eu-west-1.amazonaws.com/validation-assets/template.yaml&stackName=remember-only-lowercase&unique)

You will need to specify the following parameters in the template:

1. **Template name:** A name for the template. Resources will include this name in their resource name, 🔴 **make sure it is unique and lowercase** 🔴.
2. **LambdaMaxConcurrencyAvailable:** Specify your Lambda Concurrency Quota for your account. This will speed up the process. **Max Value is 10000**.

Wait until the service finishes deploying the template provided. Head over to the **Outputs** tab in AWS CloudFormation to find the link to a new Amazon S3 bucket created.

## Launch a new validation process

### Expected data format

The solution will take in as input your face collection data as a JSON file. The file will contain a list of records containing the information about the original pictures and indexed faces.

Data records should adhere to the following structure for the reindexing solution to function correctly:

```
[ #List of Images
    { #Image1
        "Bucket": String,
        "Key": String,
        "ExternalImageId": String, #Optional value 
        "CollectionId": String, #Name of the new collection to store faces into
        "Faces": [ #List of original indexed faces in Image1
          {                         
            "UserId": String, #Optional value
            "FaceId": String,
            "ImageId": String,
            "BoundingBoxes": {
              "Width": Float,
              "Height": Float,
              "Left": Float,
              "Top": Float
            }
          }
        ]
    }
]      
```

You can retrieve most of the information using the Rekognition ListFaces() function. You also have available a Jupyter Notebook in the **helper modules** folder to help you prepare this data.

## Validation process kickoff

**🔴 IMPORTANT PREREQUISITES BEFORE LAUNCHING AN INDEXING PROCESS🔴**

* **You need to create a folder named "validation-input" inside the Amazon S3 bucket.**

Once you have deployed the solution and prepared your face records following the structure in the step above, you are ready to begin a reindexing process. You only need to upload your JSON file to the records folder inside the generated Amazon S3 bucket. Once the file lands inside the bucket a new Step Functions state machine will be triggered.

### Validation Results

The AWS Lambda function will validate the records follow the required schema and the file exists in the Amazon S3 location provided.
Records that do not pass the validation process will be sent to Kinesis Firehose, which will group them in JSON format and save them in the created Amazon S3 bucket.
