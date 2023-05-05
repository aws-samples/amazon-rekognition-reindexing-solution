# Amazon Rekognition Face Collection ReIndexing Solution

This solution allows customers to migrate their Amazon Rekognition face collections to the newest FaceModelVersion available. 

The solution is already packaged into an Amazon CloudFormation template. AWS CloudFormation is a service that helps you model and set up your AWS resources so that you can spend less time managing those resources and more time focusing on your applications that run in AWS. 

### Solution Architecture

![Architecture](images/architecture.png)

## Solution Deployment

### Configure your Amazon SageMaker Studio Environment
To configure and deploy the solution we have created a Jupyter Notebook containing all the needed steps. Amazon Sagemaker
Studio allows you to access fully managed Jupyter notebooks. If you don't have an existing Studio environment, you can follow
the instructions in [this guide](https://catalog.us-east-1.prod.workshops.aws/workshops/63069e26-921c-4ce1-9cc7-dd882ff62575/en-US/prerequisites/option2). 

### Download this repository
When you have your environment ready, open a new Terminal and type the following command:

```git clone https://github.com/aws-samples/amazon-rekognition-reindexing-solution.git```

In the File Browser you should see an **assets** folder and a notebook named **0-Data-Preparation.ipynb**.

Open the notebook to prepare your face collection dataset, once finished, open **1-ReIndex-Solution.ipynb** to deploy and launch the reindex solution.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.