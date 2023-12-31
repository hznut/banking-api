import os

from aws_cdk import (
    aws_dynamodb as dynamodb,
    core as cdk
)
from chalice.cdk import Chalice


RUNTIME_SOURCE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), os.pardir, 'runtime', 'src')


def ddb_table_region_from_arn(arn: str) -> (str, str):
    assert arn.startswith('arn:aws:dynamodb:')
    assert ':table/' in arn
    tokens = arn.split(':')
    return tokens[3]


def ddb_table_name_from_arn(arn: str) -> (str, str):
    assert arn.startswith('arn:aws:dynamodb:')
    assert ':table/' in arn
    tokens = arn.split(':')
    return tokens[5].split('/')[1]


class ChaliceApp(cdk.Stack):

    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)
        self.dynamodb_table = self._create_ddb_table()
        self.chalice = Chalice(
            self, 'ChaliceApp', source_dir=RUNTIME_SOURCE_DIR,
            stage_config={
                'automatic_layer': True,
                "api_gateway_stage": "prod",
                "autogen_policy": False,
                "iam_policy_file": "policy-prod.json",
                "api_gateway_policy_file": "api-gateway-resource-policy-prod.json",
                'environment_variables': {
                    'APP_TABLE_ARN': self.dynamodb_table.table_arn,
                    'APP_TABLE_NAME': self.dynamodb_table.table_name,
                    "APP_TABLE_REGION": 'us-west-2',
                    "DYNAMO_ENDPOINT": "https://dynamodb.us-west-2.amazonaws.com",
                    "LOG_LEVEL": "DEBUG"
                }
            }
        )

    def _create_ddb_table(self):
        dynamodb_table = dynamodb.Table(
            self, 'AppTable',
            partition_key=dynamodb.Attribute(
                name='pk', type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(
                name='sk', type=dynamodb.AttributeType.STRING
            ),
            removal_policy=cdk.RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST)
        cdk.CfnOutput(self, 'AppTableName', value=dynamodb_table.table_name)
        dynamodb_table.add_global_secondary_index(index_name='view_all_active_accounts_index',
                                                  partition_key=dynamodb.Attribute(
                                                      name='is_account_active', type=dynamodb.AttributeType.STRING),
                                                  projection_type=dynamodb.ProjectionType.ALL)
        return dynamodb_table
