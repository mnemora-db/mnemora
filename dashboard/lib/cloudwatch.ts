/**
 * CloudWatch + DynamoDB storage metrics utility.
 *
 * Fetches aggregate storage metrics from CloudWatch (S3 bucket size)
 * and DynamoDB (table size via DescribeTable). Used by the usage page
 * and the /api/usage/metrics route.
 */

import {
  CloudWatchClient,
  GetMetricStatisticsCommand,
} from "@aws-sdk/client-cloudwatch";
import {
  DynamoDBClient,
  DescribeTableCommand,
} from "@aws-sdk/client-dynamodb";

const cw = new CloudWatchClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});
const ddb = new DynamoDBClient({
  region: process.env.AWS_REGION ?? "us-east-1",
});

const STATE_TABLE = process.env.STATE_TABLE_NAME ?? "mnemora-state-dev";
const S3_BUCKET = "mnemora-episodes-dev-993952121255";

export interface StorageMetrics {
  storageUsedMB: number;
  dynamoTableSizeMB: number;
  s3BucketSizeMB: number;
}

/**
 * Fetch aggregate storage metrics from CloudWatch and DynamoDB.
 *
 * - S3: CloudWatch BucketSizeBytes (daily metric, may be 24-48h delayed).
 * - DynamoDB: DescribeTable TableSizeBytes (updated ~every 6 hours).
 *
 * Returns zeros gracefully if metrics are unavailable.
 */
export async function getStorageMetrics(): Promise<StorageMetrics> {
  const now = new Date();

  const [s3Result, dynamoResult] = await Promise.all([
    // S3 bucket size — daily metric, look back 3 days to find latest
    cw
      .send(
        new GetMetricStatisticsCommand({
          Namespace: "AWS/S3",
          MetricName: "BucketSizeBytes",
          Dimensions: [
            { Name: "BucketName", Value: S3_BUCKET },
            { Name: "StorageType", Value: "StandardStorage" },
          ],
          StartTime: new Date(now.getTime() - 3 * 86_400_000),
          EndTime: now,
          Period: 86_400,
          Statistics: ["Average"],
        })
      )
      .catch(() => null),

    // DynamoDB table size
    ddb
      .send(new DescribeTableCommand({ TableName: STATE_TABLE }))
      .catch(() => null),
  ]);

  // S3: pick the most recent datapoint
  let s3Bytes = 0;
  if (s3Result?.Datapoints?.length) {
    const sorted = s3Result.Datapoints.sort(
      (a, b) =>
        (b.Timestamp?.getTime() ?? 0) - (a.Timestamp?.getTime() ?? 0)
    );
    s3Bytes = sorted[0]?.Average ?? 0;
  }

  // DynamoDB
  const dynamoBytes = Number(
    dynamoResult?.Table?.TableSizeBytes ?? 0
  );

  const s3MB = s3Bytes / (1024 * 1024);
  const dynamoMB = dynamoBytes / (1024 * 1024);

  return {
    storageUsedMB: Math.round((s3MB + dynamoMB) * 100) / 100,
    dynamoTableSizeMB: Math.round(dynamoMB * 100) / 100,
    s3BucketSizeMB: Math.round(s3MB * 100) / 100,
  };
}
