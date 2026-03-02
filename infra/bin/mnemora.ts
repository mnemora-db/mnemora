#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { MnemoraStack } from '../lib/mnemora-stack';

const app = new cdk.App();

const stage = (app.node.tryGetContext('stage') as string) ?? 'dev';

new MnemoraStack(app, `Mnemora-${stage}`, {
  stage,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
  description: `Mnemora infrastructure stack (${stage})`,
});
