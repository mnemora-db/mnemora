import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatchActions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import {
  HttpApi,
  CorsHttpMethod,
  HttpMethod,
  HttpNoneAuthorizer,
} from 'aws-cdk-lib/aws-apigatewayv2';
import { HttpLambdaIntegration } from 'aws-cdk-lib/aws-apigatewayv2-integrations';
import {
  HttpLambdaAuthorizer,
  HttpLambdaResponseType,
} from 'aws-cdk-lib/aws-apigatewayv2-authorizers';

export interface MnemoraStackProps extends cdk.StackProps {
  readonly stage: string;
}

export class MnemoraStack extends cdk.Stack {
  public readonly stateTable: dynamodb.Table;
  public readonly auroraCluster: rds.DatabaseCluster;
  public readonly episodeBucket: s3.Bucket;
  public readonly vpc: ec2.Vpc;
  public readonly auroraSg: ec2.SecurityGroup;
  public readonly lambdaSg: ec2.SecurityGroup;
  public readonly usersTable: dynamodb.Table;
  public readonly httpApi: HttpApi;

  constructor(scope: Construct, id: string, props: MnemoraStackProps) {
    super(scope, id, props);

    const { stage } = props;
    const isProd = stage === 'prod';

    // -------------------------------------------------------
    // VPC — public, private, and isolated subnets
    // Public: NAT gateway lives here
    // Private: Lambda functions (egress via NAT for Bedrock, etc.)
    // Isolated: Aurora (no internet access)
    // -------------------------------------------------------
    this.vpc = new ec2.Vpc(this, 'Vpc', {
      vpcName: `mnemora-vpc-${stage}`,
      maxAzs: 2,
      natGateways: isProd ? 2 : 1,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
        },
        {
          cidrMask: 24,
          name: 'Isolated',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
        },
      ],
    });

    // Gateway endpoints — free, keeps DynamoDB/S3 traffic off NAT
    this.vpc.addGatewayEndpoint('DynamoDbEndpoint', {
      service: ec2.GatewayVpcEndpointAwsService.DYNAMODB,
    });
    this.vpc.addGatewayEndpoint('S3Endpoint', {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });

    // -------------------------------------------------------
    // DynamoDB — single-table design for working memory
    // PK/SK are generic strings; key format enforced at app layer
    // See CLAUDE.md for key patterns (tenant_id#agent_id, etc.)
    // -------------------------------------------------------
    this.stateTable = new dynamodb.Table(this, 'StateTable', {
      tableName: `mnemora-state-${stage}`,
      partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sk', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: 'ttl',
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      deletionProtection: isProd,
    });

    // GSI for episodic session queries: PK = tenant_id#session_id, SK = timestamp
    this.stateTable.addGlobalSecondaryIndex({
      indexName: 'session-index',
      partitionKey: { name: 'gsi1pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'gsi1sk', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // -------------------------------------------------------
    // DynamoDB — users table for API key management
    // PK: github_id (from OAuth). Stores hashed API keys.
    // Dashboard writes keys here; Lambda authorizer reads them.
    // -------------------------------------------------------
    this.usersTable = new dynamodb.Table(this, 'UsersTable', {
      tableName: `mnemora-users-${stage}`,
      partitionKey: { name: 'github_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      deletionProtection: isProd,
    });

    // GSI for authorizer: look up user by API key hash in O(1)
    this.usersTable.addGlobalSecondaryIndex({
      indexName: 'api-key-index',
      partitionKey: { name: 'api_key_hash', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // -------------------------------------------------------
    // Aurora Serverless v2 — PostgreSQL 15 with pgvector
    // pgvector extension enabled by application code:
    //   CREATE EXTENSION IF NOT EXISTS vector;
    // -------------------------------------------------------
    this.auroraSg = new ec2.SecurityGroup(this, 'AuroraSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: `mnemora-aurora-sg-${stage}`,
      description: 'Security group for Mnemora Aurora Serverless v2 cluster',
      allowAllOutbound: false,
    });

    this.auroraCluster = new rds.DatabaseCluster(this, 'AuroraCluster', {
      clusterIdentifier: `mnemora-db-${stage}`,
      engine: rds.DatabaseClusterEngine.auroraPostgres({
        version: rds.AuroraPostgresEngineVersion.VER_15_8,
      }),
      serverlessV2MinCapacity: 0.5,
      serverlessV2MaxCapacity: 4,
      vpc: this.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      securityGroups: [this.auroraSg],
      defaultDatabaseName: 'mnemora',
      credentials: rds.Credentials.fromGeneratedSecret('mnemora_admin', {
        secretName: `mnemora/aurora/${stage}/credentials`,
      }),
      writer: rds.ClusterInstance.serverlessV2('Writer', {
        scaleWithWriter: true,
      }),
      readers: [],
      storageEncrypted: true,
      deletionProtection: isProd,
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      backup: {
        retention: cdk.Duration.days(isProd ? 30 : 7),
      },
    });

    // -------------------------------------------------------
    // S3 — episodic memory cold storage with lifecycle tiering
    // -------------------------------------------------------
    this.episodeBucket = new s3.Bucket(this, 'EpisodeBucket', {
      bucketName: `mnemora-episodes-${stage}-${cdk.Aws.ACCOUNT_ID}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: !isProd,
      lifecycleRules: [
        {
          id: 'TierToGlacier',
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(30),
            },
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
          expiration: cdk.Duration.days(365),
        },
      ],
    });

    // -------------------------------------------------------
    // Lambda security group + Aurora ingress
    // -------------------------------------------------------
    this.lambdaSg = new ec2.SecurityGroup(this, 'LambdaSecurityGroup', {
      vpc: this.vpc,
      securityGroupName: `mnemora-lambda-sg-${stage}`,
      description: 'Security group for Mnemora Lambda functions',
      allowAllOutbound: true,
    });

    this.auroraSg.addIngressRule(
      this.lambdaSg,
      ec2.Port.tcp(5432),
      'Allow Lambda functions to connect to Aurora PostgreSQL',
    );

    // -------------------------------------------------------
    // Lambda functions — Python 3.12, ARM64 (Graviton)
    // -------------------------------------------------------
    const commonEnv: Record<string, string> = {
      STAGE: stage,
      STATE_TABLE_NAME: this.stateTable.tableName,
      AURORA_HOST: this.auroraCluster.clusterEndpoint.hostname,
      AURORA_PORT: this.auroraCluster.clusterEndpoint.port.toString(),
      AURORA_SECRET_ARN: this.auroraCluster.secret?.secretArn ?? '',
      AURORA_DB_NAME: 'mnemora',
      EPISODE_BUCKET_NAME: this.episodeBucket.bucketName,
      USERS_TABLE_NAME: this.usersTable.tableName,
    };

    // Bundle Python deps (pydantic) into the Lambda deployment package.
    // Uses local pip with --platform flags (no Docker required).
    // boto3 excluded — provided by Lambda runtime.
    const lambdaCode = lambda.Code.fromAsset('../api', {
      bundling: {
        image: lambda.Runtime.PYTHON_3_12.bundlingImage,
        local: {
          tryBundle(outputDir: string): boolean {
            const { execSync } = require('child_process');  // eslint-disable-line @typescript-eslint/no-require-imports
            try {
              // Pin psycopg + psycopg-binary to same version to avoid mismatch.
              // psycopg-binary ARM64 wheels may lag behind psycopg pure-Python releases.
              execSync([
                'pip3 install "psycopg[binary]==3.2.6" "psycopg_pool>=3.2" pydantic',
                `--target "${outputDir}"`,
                '--platform manylinux2014_aarch64',
                '--implementation cp',
                '--python-version 3.12',
                '--only-binary=:all:',
                '--upgrade --quiet',
              ].join(' '));
              execSync(`cp -r ../api/handlers ../api/lib ../api/requirements.txt "${outputDir}/"`);
              return true;
            } catch (e) {
              console.error('Local bundling failed:', e);
              return false;
            }
          },
        },
      },
    });

    const vpcLambdaProps = {
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      memorySize: 256,
      timeout: cdk.Duration.seconds(30),
      code: lambdaCode,
      vpc: this.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      securityGroups: [this.lambdaSg],
      environment: commonEnv,
    };

    const publicLambdaProps = {
      runtime: lambda.Runtime.PYTHON_3_12,
      architecture: lambda.Architecture.ARM_64,
      memorySize: 256,
      timeout: cdk.Duration.seconds(30),
      code: lambdaCode,
      environment: commonEnv,
    };

    const healthFn = new lambda.Function(this, 'HealthFunction', {
      ...publicLambdaProps,
      functionName: `mnemora-health-${stage}`,
      handler: 'handlers.health.handler',
      description: 'Health check endpoint',
    });

    const authFn = new lambda.Function(this, 'AuthFunction', {
      ...publicLambdaProps,
      functionName: `mnemora-auth-${stage}`,
      handler: 'handlers.auth.handler',
      description: 'API key authorizer',
    });

    const stateFn = new lambda.Function(this, 'StateFunction', {
      ...vpcLambdaProps,
      functionName: `mnemora-state-${stage}`,
      handler: 'handlers.state.handler',
      description: 'Working memory CRUD (DynamoDB)',
    });

    const semanticFn = new lambda.Function(this, 'SemanticFunction', {
      ...vpcLambdaProps,
      functionName: `mnemora-semantic-${stage}`,
      handler: 'handlers.semantic.handler',
      description: 'Semantic memory + vector search (Aurora pgvector)',
    });

    const episodicFn = new lambda.Function(this, 'EpisodicFunction', {
      ...vpcLambdaProps,
      functionName: `mnemora-episodic-${stage}`,
      handler: 'handlers.episodic.handler',
      description: 'Episodic memory + time-range queries',
    });

    const unifiedFn = new lambda.Function(this, 'UnifiedFunction', {
      ...vpcLambdaProps,
      functionName: `mnemora-unified-${stage}`,
      handler: 'handlers.unified.handler',
      description: 'Unified /v1/memory endpoint',
    });

    // -------------------------------------------------------
    // Migration Lambda — runs inside VPC to reach Aurora
    // Invoke manually: aws lambda invoke --function-name mnemora-migrate-dev /dev/stdout
    // -------------------------------------------------------
    const migrateFn = new lambda.Function(this, 'MigrateFunction', {
      ...vpcLambdaProps,
      functionName: `mnemora-migrate-${stage}`,
      handler: 'handlers.migrate.handler',
      description: 'One-shot Aurora migration runner',
      timeout: cdk.Duration.seconds(60),
      memorySize: 256,
    });
    this.auroraCluster.secret?.grantRead(migrateFn);

    // -------------------------------------------------------
    // IAM grants — least privilege per function
    // -------------------------------------------------------
    this.stateTable.grantReadData(authFn);
    this.usersTable.grantReadData(authFn);

    this.stateTable.grantReadWriteData(stateFn);

    this.auroraCluster.secret?.grantRead(semanticFn);
    semanticFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        resources: [
          `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/amazon.titan-embed-text-v2:0`,
        ],
      }),
    );

    this.stateTable.grantReadWriteData(episodicFn);
    this.episodeBucket.grantReadWrite(episodicFn);
    episodicFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        resources: [
          `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/amazon.titan-embed-text-v2:0`,
          `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0`,
        ],
      }),
    );
    this.auroraCluster.secret?.grantRead(episodicFn);

    this.stateTable.grantReadWriteData(unifiedFn);
    this.auroraCluster.secret?.grantRead(unifiedFn);
    this.episodeBucket.grantReadWrite(unifiedFn);
    unifiedFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['bedrock:InvokeModel', 'bedrock:InvokeModelWithResponseStream'],
        resources: [
          `arn:aws:bedrock:${cdk.Aws.REGION}::foundation-model/amazon.titan-embed-text-v2:0`,
        ],
      }),
    );

    // -------------------------------------------------------
    // Lambda authorizer — SIMPLE response type, 5-min cache
    // -------------------------------------------------------
    const lambdaAuthorizer = new HttpLambdaAuthorizer('MnemoraAuthorizer', authFn, {
      authorizerName: `mnemora-authorizer-${stage}`,
      identitySource: ['$request.header.Authorization'],
      resultsCacheTtl: cdk.Duration.minutes(5),
      responseTypes: [HttpLambdaResponseType.SIMPLE],
    });

    // -------------------------------------------------------
    // HTTP API Gateway — CORS, default authorizer, routes
    // -------------------------------------------------------
    this.httpApi = new HttpApi(this, 'HttpApi', {
      apiName: `mnemora-api-${stage}`,
      description: `Mnemora API (${stage})`,
      corsPreflight: {
        allowHeaders: ['Content-Type', 'Authorization', 'X-Request-Id'],
        allowMethods: [
          CorsHttpMethod.GET,
          CorsHttpMethod.POST,
          CorsHttpMethod.PUT,
          CorsHttpMethod.DELETE,
          CorsHttpMethod.OPTIONS,
        ],
        allowOrigins: ['*'],
        maxAge: cdk.Duration.hours(1),
      },
      defaultAuthorizer: lambdaAuthorizer,
    });

    // Integrations
    const healthIntegration = new HttpLambdaIntegration('HealthIntegration', healthFn);
    const stateIntegration = new HttpLambdaIntegration('StateIntegration', stateFn);
    const semanticIntegration = new HttpLambdaIntegration('SemanticIntegration', semanticFn);
    const episodicIntegration = new HttpLambdaIntegration('EpisodicIntegration', episodicFn);
    const unifiedIntegration = new HttpLambdaIntegration('UnifiedIntegration', unifiedFn);

    // Health — no auth
    this.httpApi.addRoutes({
      path: '/v1/health',
      methods: [HttpMethod.GET],
      integration: healthIntegration,
      authorizer: new HttpNoneAuthorizer(),
    });

    // State routes — base path for POST (create) + catch-all proxy for rest
    this.httpApi.addRoutes({
      path: '/v1/state',
      methods: [HttpMethod.POST],
      integration: stateIntegration,
    });
    this.httpApi.addRoutes({
      path: '/v1/state/{proxy+}',
      methods: [HttpMethod.GET, HttpMethod.POST, HttpMethod.PUT, HttpMethod.DELETE],
      integration: stateIntegration,
    });

    // Semantic routes — base path for POST (create) + catch-all proxy
    this.httpApi.addRoutes({
      path: '/v1/memory/semantic',
      methods: [HttpMethod.POST],
      integration: semanticIntegration,
    });
    this.httpApi.addRoutes({
      path: '/v1/memory/semantic/{proxy+}',
      methods: [HttpMethod.GET, HttpMethod.POST, HttpMethod.DELETE],
      integration: semanticIntegration,
    });

    // Episodic routes — base path for POST (create) + catch-all proxy
    this.httpApi.addRoutes({
      path: '/v1/memory/episodic',
      methods: [HttpMethod.POST],
      integration: episodicIntegration,
    });
    this.httpApi.addRoutes({
      path: '/v1/memory/episodic/{proxy+}',
      methods: [HttpMethod.GET, HttpMethod.POST],
      integration: episodicIntegration,
    });

    // Unified memory routes
    this.httpApi.addRoutes({
      path: '/v1/memory',
      methods: [HttpMethod.POST],
      integration: unifiedIntegration,
    });
    this.httpApi.addRoutes({
      path: '/v1/memory/{agent_id}',
      methods: [HttpMethod.GET, HttpMethod.DELETE],
      integration: unifiedIntegration,
    });
    this.httpApi.addRoutes({
      path: '/v1/memory/search',
      methods: [HttpMethod.POST],
      integration: unifiedIntegration,
    });

    // Usage
    this.httpApi.addRoutes({
      path: '/v1/usage',
      methods: [HttpMethod.GET],
      integration: unifiedIntegration,
    });

    // -------------------------------------------------------
    // Observability — SNS, CloudWatch Dashboard, Alarms
    // All Lambda functions are referenced by local variable here.
    // -------------------------------------------------------

    // All six Lambda functions in a typed array for widget iteration
    const allFunctions: Array<{ fn: lambda.Function; label: string }> = [
      { fn: healthFn, label: 'health' },
      { fn: authFn, label: 'auth' },
      { fn: stateFn, label: 'state' },
      { fn: semanticFn, label: 'semantic' },
      { fn: episodicFn, label: 'episodic' },
      { fn: unifiedFn, label: 'unified' },
    ];

    // -------------------------------------------------------
    // SNS alert topic — receives all alarm notifications
    // -------------------------------------------------------
    const alertTopic = new sns.Topic(this, 'AlertTopic', {
      topicName: `mnemora-alerts-${stage}`,
      displayName: `Mnemora Alerts (${stage})`,
    });

    /** Placeholder email subscription — replace with real address before going live */
    alertTopic.addSubscription(
      new snsSubscriptions.EmailSubscription('alerts@example.com'),
    );

    // -------------------------------------------------------
    // CloudWatch Alarms
    // -------------------------------------------------------

    // Helper: build a Lambda error-rate alarm for a single function.
    // Uses a MathExpression: errors / invocations > 0.05 over 5 minutes.
    const buildLambdaErrorRateAlarm = (
      fn: lambda.Function,
      label: string,
    ): cloudwatch.Alarm => {
      const invocations = fn.metricInvocations({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
        label: `${label} Invocations`,
      });

      const errors = fn.metricErrors({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
        label: `${label} Errors`,
      });

      // MathExpression: errorRate = IF(invocations > 0, errors / invocations, 0)
      // IF guard prevents division-by-zero when function is idle.
      const errorRateExpr = new cloudwatch.MathExpression({
        expression: 'IF(invocations > 0, errors / invocations, 0)',
        usingMetrics: { errors, invocations },
        period: cdk.Duration.minutes(5),
        label: `${label} Error Rate`,
      });

      const alarm = new cloudwatch.Alarm(this, `LambdaErrorRateAlarm-${label}`, {
        alarmName: `mnemora-lambda-error-rate-${label}-${stage}`,
        alarmDescription: `Lambda error rate > 5% for 5 minutes on ${label} function (${stage})`,
        metric: errorRateExpr,
        threshold: 0.05,
        evaluationPeriods: 1,
        comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });

      alarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
      alarm.addOkAction(new cloudwatchActions.SnsAction(alertTopic));
      return alarm;
    };

    // Create per-function Lambda error rate alarms
    for (const { fn, label } of allFunctions) {
      buildLambdaErrorRateAlarm(fn, label);
    }

    // API Gateway 5xx > 10 in 5 minutes
    const api5xxMetric = new cloudwatch.Metric({
      namespace: 'AWS/ApiGateway',
      metricName: '5xx',
      dimensionsMap: { ApiId: this.httpApi.httpApiId },
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
      label: 'API Gateway 5xx Count',
    });

    const api5xxAlarm = new cloudwatch.Alarm(this, 'Api5xxAlarm', {
      alarmName: `mnemora-api-5xx-${stage}`,
      alarmDescription: `API Gateway 5xx errors > 10 in 5 minutes (${stage})`,
      metric: api5xxMetric,
      threshold: 10,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    api5xxAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
    api5xxAlarm.addOkAction(new cloudwatchActions.SnsAction(alertTopic));

    // Aurora ACU > 2 sustained for 15 minutes (cost protection)
    const auroraAcuMetric = new cloudwatch.Metric({
      namespace: 'AWS/RDS',
      metricName: 'ServerlessDatabaseCapacity',
      dimensionsMap: { DBClusterIdentifier: this.auroraCluster.clusterIdentifier },
      period: cdk.Duration.minutes(5),
      statistic: 'Average',
      label: 'Aurora ACU',
    });

    const auroraAcuAlarm = new cloudwatch.Alarm(this, 'AuroraAcuAlarm', {
      alarmName: `mnemora-aurora-acu-${stage}`,
      alarmDescription: `Aurora ACU > 2 for 15 minutes — cost protection alert (${stage})`,
      metric: auroraAcuMetric,
      threshold: 2,
      evaluationPeriods: 3, // 3 × 5-min periods = 15 minutes
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    auroraAcuAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
    auroraAcuAlarm.addOkAction(new cloudwatchActions.SnsAction(alertTopic));

    // DynamoDB throttled requests > 0
    const dynamoThrottleReadMetric = new cloudwatch.Metric({
      namespace: 'AWS/DynamoDB',
      metricName: 'ReadThrottleEvents',
      dimensionsMap: { TableName: this.stateTable.tableName },
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
      label: 'DynamoDB Read Throttles',
    });

    const dynamoThrottleWriteMetric = new cloudwatch.Metric({
      namespace: 'AWS/DynamoDB',
      metricName: 'WriteThrottleEvents',
      dimensionsMap: { TableName: this.stateTable.tableName },
      period: cdk.Duration.minutes(5),
      statistic: 'Sum',
      label: 'DynamoDB Write Throttles',
    });

    // Alarm on combined read+write throttles
    const dynamoThrottleMath = new cloudwatch.MathExpression({
      expression: 'readThrottles + writeThrottles',
      usingMetrics: {
        readThrottles: dynamoThrottleReadMetric,
        writeThrottles: dynamoThrottleWriteMetric,
      },
      period: cdk.Duration.minutes(5),
      label: 'DynamoDB Total Throttles',
    });

    const dynamoThrottleAlarm = new cloudwatch.Alarm(this, 'DynamoThrottleAlarm', {
      alarmName: `mnemora-dynamo-throttle-${stage}`,
      alarmDescription: `DynamoDB throttled requests > 0 (${stage})`,
      metric: dynamoThrottleMath,
      threshold: 0,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    dynamoThrottleAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
    dynamoThrottleAlarm.addOkAction(new cloudwatchActions.SnsAction(alertTopic));

    // -------------------------------------------------------
    // CloudWatch Dashboard — "MnemoraHealth"
    // Row layout:
    //   Row 1: Lambda invocation counts (all 6 functions)
    //   Row 2: Lambda error counts (all 6 functions)
    //   Row 3: Lambda p50/p95/p99 duration (all 6 functions, 3 widgets × percentile)
    //   Row 4: API Gateway 4xx/5xx rates, request count, latency percentiles
    //   Row 5: DynamoDB consumed R/W capacity
    //   Row 6: Aurora ACU + DatabaseConnections
    // -------------------------------------------------------
    const dashboard = new cloudwatch.Dashboard(this, 'MnemoraHealthDashboard', {
      dashboardName: `MnemoraHealth-${stage}`,
    });

    // --- Lambda invocation counts ---
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Invocations',
        width: 24,
        height: 6,
        left: allFunctions.map(({ fn, label }) =>
          fn.metricInvocations({
            period: cdk.Duration.minutes(5),
            statistic: 'Sum',
            label,
          }),
        ),
      }),
    );

    // --- Lambda error counts ---
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Errors',
        width: 24,
        height: 6,
        left: allFunctions.map(({ fn, label }) =>
          fn.metricErrors({
            period: cdk.Duration.minutes(5),
            statistic: 'Sum',
            label,
          }),
        ),
      }),
    );

    // --- Lambda duration p50 / p95 / p99 (one widget per percentile) ---
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Duration p50 (ms)',
        width: 8,
        height: 6,
        left: allFunctions.map(({ fn, label }) =>
          fn.metricDuration({
            period: cdk.Duration.minutes(5),
            statistic: 'p50',
            label: `${label} p50`,
          }),
        ),
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Duration p95 (ms)',
        width: 8,
        height: 6,
        left: allFunctions.map(({ fn, label }) =>
          fn.metricDuration({
            period: cdk.Duration.minutes(5),
            statistic: 'p95',
            label: `${label} p95`,
          }),
        ),
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Duration p99 (ms)',
        width: 8,
        height: 6,
        left: allFunctions.map(({ fn, label }) =>
          fn.metricDuration({
            period: cdk.Duration.minutes(5),
            statistic: 'p99',
            label: `${label} p99`,
          }),
        ),
      }),
    );

    // --- API Gateway: 4xx rate, 5xx rate, request count (one row) ---
    const apiDimensions = { ApiId: this.httpApi.httpApiId };

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Gateway 4xx Error Rate',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/ApiGateway',
            metricName: '4xx',
            dimensionsMap: apiDimensions,
            period: cdk.Duration.minutes(5),
            statistic: 'Sum',
            label: 'API 4xx',
          }),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'API Gateway 5xx Error Rate',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/ApiGateway',
            metricName: '5xx',
            dimensionsMap: apiDimensions,
            period: cdk.Duration.minutes(5),
            statistic: 'Sum',
            label: 'API 5xx',
          }),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'API Gateway Request Count',
        width: 8,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/ApiGateway',
            metricName: 'Count',
            dimensionsMap: apiDimensions,
            period: cdk.Duration.minutes(5),
            statistic: 'Sum',
            label: 'Requests',
          }),
        ],
      }),
    );

    // --- API Gateway latency percentiles ---
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Gateway Latency p50/p95/p99 (ms)',
        width: 24,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/ApiGateway',
            metricName: 'Latency',
            dimensionsMap: apiDimensions,
            period: cdk.Duration.minutes(5),
            statistic: 'p50',
            label: 'Latency p50',
          }),
          new cloudwatch.Metric({
            namespace: 'AWS/ApiGateway',
            metricName: 'Latency',
            dimensionsMap: apiDimensions,
            period: cdk.Duration.minutes(5),
            statistic: 'p95',
            label: 'Latency p95',
          }),
          new cloudwatch.Metric({
            namespace: 'AWS/ApiGateway',
            metricName: 'Latency',
            dimensionsMap: apiDimensions,
            period: cdk.Duration.minutes(5),
            statistic: 'p99',
            label: 'Latency p99',
          }),
        ],
      }),
    );

    // --- DynamoDB consumed read/write capacity ---
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'DynamoDB Consumed Capacity',
        width: 24,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/DynamoDB',
            metricName: 'ConsumedReadCapacityUnits',
            dimensionsMap: { TableName: this.stateTable.tableName },
            period: cdk.Duration.minutes(5),
            statistic: 'Sum',
            label: 'Read CU',
          }),
          new cloudwatch.Metric({
            namespace: 'AWS/DynamoDB',
            metricName: 'ConsumedWriteCapacityUnits',
            dimensionsMap: { TableName: this.stateTable.tableName },
            period: cdk.Duration.minutes(5),
            statistic: 'Sum',
            label: 'Write CU',
          }),
        ],
      }),
    );

    // --- Aurora ACU + DatabaseConnections ---
    const auroraClusterDimensions = {
      DBClusterIdentifier: this.auroraCluster.clusterIdentifier,
    };

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Aurora Serverless ACU Usage',
        width: 12,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/RDS',
            metricName: 'ServerlessDatabaseCapacity',
            dimensionsMap: auroraClusterDimensions,
            period: cdk.Duration.minutes(5),
            statistic: 'Average',
            label: 'ACU',
          }),
        ],
      }),
      new cloudwatch.GraphWidget({
        title: 'Aurora Database Connections',
        width: 12,
        height: 6,
        left: [
          new cloudwatch.Metric({
            namespace: 'AWS/RDS',
            metricName: 'DatabaseConnections',
            dimensionsMap: auroraClusterDimensions,
            period: cdk.Duration.minutes(5),
            statistic: 'Average',
            label: 'Connections',
          }),
        ],
      }),
    );

    // -------------------------------------------------------
    // Stack outputs
    // -------------------------------------------------------
    new cdk.CfnOutput(this, 'StateTableName', {
      value: this.stateTable.tableName,
      description: 'DynamoDB state table name',
      exportName: `mnemora-state-table-${stage}`,
    });

    new cdk.CfnOutput(this, 'StateTableArn', {
      value: this.stateTable.tableArn,
      description: 'DynamoDB state table ARN',
      exportName: `mnemora-state-table-arn-${stage}`,
    });

    new cdk.CfnOutput(this, 'AuroraClusterEndpoint', {
      value: this.auroraCluster.clusterEndpoint.hostname,
      description: 'Aurora cluster writer endpoint',
      exportName: `mnemora-aurora-endpoint-${stage}`,
    });

    new cdk.CfnOutput(this, 'AuroraClusterPort', {
      value: this.auroraCluster.clusterEndpoint.port.toString(),
      description: 'Aurora cluster port',
      exportName: `mnemora-aurora-port-${stage}`,
    });

    new cdk.CfnOutput(this, 'AuroraSecretArn', {
      value: this.auroraCluster.secret?.secretArn ?? '',
      description: 'Aurora credentials secret ARN',
      exportName: `mnemora-aurora-secret-arn-${stage}`,
    });

    new cdk.CfnOutput(this, 'EpisodeBucketName', {
      value: this.episodeBucket.bucketName,
      description: 'S3 episode storage bucket name',
      exportName: `mnemora-episode-bucket-${stage}`,
    });

    new cdk.CfnOutput(this, 'EpisodeBucketArn', {
      value: this.episodeBucket.bucketArn,
      description: 'S3 episode storage bucket ARN',
      exportName: `mnemora-episode-bucket-arn-${stage}`,
    });

    new cdk.CfnOutput(this, 'VpcId', {
      value: this.vpc.vpcId,
      description: 'VPC ID for Lambda functions',
      exportName: `mnemora-vpc-id-${stage}`,
    });

    new cdk.CfnOutput(this, 'AuroraSecurityGroupId', {
      value: this.auroraSg.securityGroupId,
      description: 'Aurora security group ID',
      exportName: `mnemora-aurora-sg-id-${stage}`,
    });

    new cdk.CfnOutput(this, 'ApiEndpoint', {
      value: this.httpApi.apiEndpoint,
      description: 'HTTP API endpoint URL',
      exportName: `mnemora-api-endpoint-${stage}`,
    });

    new cdk.CfnOutput(this, 'ApiId', {
      value: this.httpApi.httpApiId,
      description: 'HTTP API ID',
      exportName: `mnemora-api-id-${stage}`,
    });

    new cdk.CfnOutput(this, 'AlertTopicArn', {
      value: alertTopic.topicArn,
      description: 'SNS topic ARN for Mnemora alerts',
      exportName: `mnemora-alerts-topic-arn-${stage}`,
    });

    new cdk.CfnOutput(this, 'UsersTableName', {
      value: this.usersTable.tableName,
      description: 'DynamoDB users table name',
      exportName: `mnemora-users-table-${stage}`,
    });
  }
}
