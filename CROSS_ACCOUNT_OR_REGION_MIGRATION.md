# Cross-Account / Cross-Region Rekognition Collection Migration

This guide extends the [Amazon Rekognition Face Collection ReIndexing Solution](README.md) to support migrating face collections across AWS accounts or regions.

## Prerequisites

- AWS CLI configured with profiles for both source and destination accounts
- Python 3.x with boto3 installed
- Access to the source Rekognition collection and its associated S3 images
- Permissions to deploy CloudFormation stacks in the destination account

## Migration Workflow

### Step 1: Extract Face Records from Source Collection

Extract face records from the source collection using `ListFaces()` with image S3 mapping and save as a JSON file — the repo includes a helper Jupyter notebook (`helper-modules/0-Data-Preparation.ipynb`) that provides a starting template, though you'll need to implement the `getAdditionalInfo` function to map each FaceId back to its source S3 Bucket and Key.

```bash
# Example: List faces in the source collection
aws rekognition list-faces \
  --collection-id <source-collection-id> \
  --region <source-region> \
  --profile <source-profile>
```

**Output:** A JSON file matching the [expected data format](README.md#expected-data-format).

### Step 2: Make Source Images Accessible from Destination Account

Make source images accessible from the destination account:

- **Option A — Copy images:** Copy/replicate source images to an S3 bucket in the destination account/region using `aws s3 sync`.

  ```bash
  # Sync from source to destination bucket
  aws s3 sync s3://<source-bucket>/<prefix> s3://<destination-bucket>/<prefix> \
    --source-region <source-region> \
    --region <destination-region>
  ```

- **Option B — Cross-account access:** Configure a cross-account S3 bucket policy on the source bucket granting `s3:GetObject` to the destination account's Rekognition service role.

  ```json
  {
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::<DESTINATION_ACCOUNT_ID>:root"
    },
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::<SOURCE_BUCKET>/*"
  }
  ```

### Step 3: Deploy Reindexing Stack in Destination

Deploy the reindexing CloudFormation stack (`solution-assets/cloudformation_template/template.yaml`) in the destination account/region, specifying your IndexFaces TPS limit, Lambda concurrency quota, and quality filter parameters.

```bash
aws cloudformation deploy \
  --template-file solution-assets/cloudformation_template/template.yaml \
  --stack-name rekognition-reindex \
  --capabilities CAPABILITY_IAM \
  --region <destination-region> \
  --profile <destination-profile>
```

Alternatively, use the one-click launch links in the [main README](README.md#solution-deployment).

### Step 4: Create Target Collection in Destination

Create the target Rekognition collection in the destination account/region using `aws rekognition create-collection`.

```bash
aws rekognition create-collection \
  --collection-id <new-collection-id> \
  --region <destination-region> \
  --profile <destination-profile>
```

### Step 5: Update Records JSON for Destination Environment

Update the records JSON to reflect the destination environment — set `CollectionId` to the new target collection name, and if you copied images (Option A), update `Bucket` to the destination bucket name; if using cross-account access (Option B), keep the original `Bucket`/`Key` values.

```bash
# Example using jq to update CollectionId and Bucket
jq '[ .[] | .CollectionId = "<new-collection-id>" | .Bucket = "<destination-bucket>" ]' \
  source-records.json > destination-records.json
```

### Step 6: Upload Records to Trigger Reindexing

Upload the records JSON to the `records/` folder inside the S3 bucket created by the CloudFormation stack, which automatically triggers the Step Functions state machine to begin the reindexing process.

```bash
aws s3 cp destination-records.json \
  s3://<cfn-created-bucket>/records/destination-records.json \
  --region <destination-region> \
  --profile <destination-profile>
```

### Step 7: Monitor and Validate

Monitor the Step Functions execution in the AWS console and review the DynamoDB results table for old-to-new FaceId mappings, checking the logs table for any records that failed IoU threshold matching or where faces were not detected.

```bash
# Check Step Functions execution status
aws stepfunctions list-executions \
  --state-machine-arn <state-machine-arn> \
  --region <destination-region> \
  --profile <destination-profile>

# Scan DynamoDB results table
aws dynamodb scan \
  --table-name <results-table-name> \
  --region <destination-region> \
  --profile <destination-profile>
```

## Validation

After migration completes, verify the new collection:

```bash
# Compare face counts
aws rekognition describe-collection \
  --collection-id <new-collection-id> \
  --region <destination-region> \
  --profile <destination-profile>
```

The repo also includes a [validation solution](helper-modules/validation-solution.md) for verifying records.

### Step 8: Migrate User Vectors (Optional)

The reindexing solution migrates face vectors but does not recreate [User Vectors](https://aws.amazon.com/about-aws/whats-new/2023/06/amazon-rekognition-face-search-accuracy-user-vectors/). If your source collection uses `CreateUser` and `AssociateFaces`, use the [User Vector Migration notebook](helper-modules/1-User-Vector-Migration.ipynb) to recreate users and face associations in the target collection using the DynamoDB results table.

## Cleanup

Delete the CloudFormation stack in the destination account when done testing:

```bash
aws cloudformation delete-stack \
  --stack-name rekognition-reindex \
  --region <destination-region> \
  --profile <destination-profile>
```
