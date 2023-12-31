import os
from pytest import fixture
from chalice.test import Client, LocalGateway
import docker
import socket
from docker.models.resource import Model
import random
import boto3

docker_client = docker.from_env()
ddb_container = None


class LocalGatewayForTest(LocalGateway):
    """
    Workaround since Chalice TestHttpClient doesn't support AWS_IAM Authorizer in local mode.
    """
    def __init__(self, app_object, config, account_id=None):
        super().__init__(app_object, config)
        self.account_id = account_id

    def _generate_lambda_event(self, method, path, headers, body):
        event = super(LocalGatewayForTest, self)._generate_lambda_event(method, path, headers, body)
        event['requestContext']['identity'] = {'accountId': self.account_id}
        return event


@fixture(scope="session", autouse=True)
def set_environ():
    os.environ['LOG_LEVEL'] = 'DEBUG'
    os.environ['APP_TABLE_NAME'] = 'banking-api-AppTable'
    os.environ['APP_TABLE_REGION'] = 'us-west-2'
    # Without the following AWS_SHARED_CREDENTIALS_FILE environment variable the boto3 SDK call looks for default
    # profile in $HOME/.aws/credentials. If the default profile or the credentials file isn't present on the host
    # eg. on Jenkins node, then the test setup fails.
    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = f"{os.path.dirname(os.path.realpath(__file__))}/aws_credentials_for_test"


@fixture(scope="function")
def test_client(setup, caller_account_id, request):
    print(f"module: {request.node.nodeid}")
    from app import app
    with Client(app, stage_name='prod') as client:
        client.http._local_gateway = LocalGatewayForTest(client.http._app, client.http._config, caller_account_id)
        yield client
    # delete_ddb_table()


def next_free_port(start_port=1024, max_port=65535):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port = start_port
    while port <= max_port:
        try:
            sock.bind(('', port))
            sock.close()
            return port
        except OSError:
            port += 1
    raise IOError('no free ports')


@fixture(scope="session", autouse=True)
def start_ddb_local(set_environ) -> (Model, str):
    # environ = set_environ
    global ddb_container
    port = next_free_port(start_port=8002)
    try:
        containers = docker_client.containers.list(filters={'ancestor': 'amazon/dynamodb-local'})
    except Exception as e:
        print(e)
        raise e
    for running_container in containers:
        if running_container.name.startswith('banking-api-tests'):
            running_container.stop()
            running_container.remove()
            print(f"Stopped dynamodb-local container {running_container.short_id}")
    try:
        docker_client.images.pull('amazon/dynamodb-local', 'latest')
        ddb_container = docker_client.containers.run(image='amazon/dynamodb-local',
                                                     command="-jar DynamoDBLocal.jar -sharedDb", detach=True,
                                                     ports={'8000/tcp': port},
                                                     name=f"banking-api-tests-{random.randint(100, 999)}")
    except Exception as e:
        print(e)
        raise e
    print(f"Started dynamodb-local container name={ddb_container.name} short_id={ddb_container.short_id} on port {port}")
    DYNAMO_ENDPOINT = f"http://localhost:{port}"
    os.environ['DYNAMO_ENDPOINT'] = DYNAMO_ENDPOINT
    print(f"DYNAMO_ENDPOINT={os.environ['DYNAMO_ENDPOINT']}")
    return ddb_container, DYNAMO_ENDPOINT


@fixture(scope="module", autouse=True)
def create_ddb_table(set_environ):
    # environ = set_environ
    table_name = os.environ['APP_TABLE_NAME']
    dynamo_endpoint = os.environ['DYNAMO_ENDPOINT']
    ddb = boto3.client('dynamodb', endpoint_url=dynamo_endpoint)
    response = ddb.list_tables()
    if table_name in response['TableNames']:
        ddb.delete_table(TableName=table_name)
        print(f"Pre-existing table {table_name} deleted.")
    ddb.create_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'pk',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'sk',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'is_account_active',
                'AttributeType': 'S'
            }
        ],
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': 'pk',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'sk',
                'KeyType': 'RANGE'
            }
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'view_all_active_accounts_index',
                'KeySchema': [
                    {
                        'AttributeName': 'is_account_active',
                        'KeyType': 'HASH'
                    }
                ],
                'Projection': {
                    'ProjectionType': 'ALL'
                }
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    print(f"Table {table_name} created.")


def delete_ddb_table():
    table_name = os.environ['APP_TABLE_NAME']
    dynamo_endpoint = os.environ['DYNAMO_ENDPOINT']
    ddb = boto3.client('dynamodb', endpoint_url=dynamo_endpoint)
    response = ddb.list_tables()
    if table_name in response['TableNames']:
        ddb.delete_table(TableName=table_name)
        print(f"Table {table_name} deleted.")


def destroy_db():
    """
    In case of failure rerun after commenting out call to this method so that
    you can connect to dynamodb-local using dynamodb-admin. Don't forget to set the DYNAMO_ENDPOINT to relevant value
    as printed in the setup_module(..) before launching dynamodb-admin.
    Eg. For accessing dynamodb-admin on http://localhost:9001 to connect to dynamodb-local on port 8005:
    > DYNAMO_ENDPOINT=http://localhost:8005 dynamodb-admin -p 9001
    """
    if ddb_container is not None:
        ddb_container.stop()
        ddb_container.remove()
        print(f"Stopped dynamodb-local container name={ddb_container.name} short_id={ddb_container.short_id}")


@fixture(scope="module", autouse=True)
def setup(set_environ, create_ddb_table):
    pass


@fixture(scope="session", autouse=True)
def session_cleanup(request):
    request.addfinalizer(destroy_db)
