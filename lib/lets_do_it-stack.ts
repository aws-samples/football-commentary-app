import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as kinesis from 'aws-cdk-lib/aws-kinesis';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambdEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as cforigins from 'aws-cdk-lib/aws-cloudfront-origins';


export class FootballCommentaryStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create Kinesis stream
    const kinesisStream = new kinesis.Stream(this, 'MyKinesisStream', {
      streamName: 'my-kinesis-stream',
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Create DynamoDB table
    const dynamoTable = new dynamodb.Table(this, 'MyDynamoTable', {
      tableName: 'SoccerCommentary',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      deletionProtection: false,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });


    // Create Lambda functions
    const ingestLambda = new lambda.Function(this, 'IngestLambda', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/ingest-lambda'),
      timeout: cdk.Duration.minutes(2),
      environment: {
        STREAM_NAME: kinesisStream.streamName,
        TABLE_NAME: dynamoTable.tableName,
      },
    });
    // set the trigger of this lambda function to be kinesis
    ingestLambda.addEventSource(new lambdEventSources.KinesisEventSource(kinesisStream,{
      startingPosition: lambda.StartingPosition.LATEST,
    }));

    const getLambda = new lambda.Function(this, 'GetLambda', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'index.handler',
      timeout: cdk.Duration.minutes(2),
      code: lambda.Code.fromAsset('lambda/get-lambda'),
      environment: {
        TABLE_NAME: dynamoTable.tableName,
      },
    });

    // Set up permissions
    kinesisStream.grantRead(ingestLambda);
    dynamoTable.grantReadData(getLambda);
    dynamoTable.grantReadWriteData(ingestLambda);
    ingestLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['bedrock:InvokeModel'],
      resources: ['*'],
    }));

    // Create API Gateway
    const api = new apigateway.RestApi(this, 'SoccerApi');

    const displayResource = api.root.addResource('display');
    displayResource.addMethod('GET', new apigateway.LambdaIntegration(getLambda));

    // Hosting bucket
    const webHostingBucket = new s3.Bucket(this, 'HostingBucket', {
      accessControl: s3.BucketAccessControl.PRIVATE,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    const cf = new cloudfront.Distribution(this, 'WebDistribution', {
      defaultRootObject: 'index.html',
      defaultBehavior: {
        origin: cforigins.S3BucketOrigin.withOriginAccessIdentity(webHostingBucket)
      }
    });

  // CDK Outputs
  new cdk.CfnOutput(this, "ApiGatewayUrl", {value: api.url});
  new cdk.CfnOutput(this, "CloudFrontEndpoint", {value: cf.distributionDomainName});
  new cdk.CfnOutput(this, "CloudFrontDistributionId", {value: cf.distributionId});
  new cdk.CfnOutput(this, "S3BucketName", {value: webHostingBucket.bucketName});
  new cdk.CfnOutput(this, "KinesisStreamName", {value: kinesisStream.streamName});
  }
  
}
