from typing import Union
import chalicelib.config
from chalice import (Chalice, Response, IAMAuthorizer)
from chalicelib.service.sync_service import SyncService
from chalicelib.utils.exceptions import (AppError, TransferWithinSameAccountError)
from chalicelib.utils.request_helper import (extract_callers_account_number, extract_dest_account_number,
                                             extract_initial_balance, check_account_type,
                                             extract_result_limit, extract_last_evaluated_key, extract_amount)
import json
from contextlib import contextmanager

app = Chalice(app_name='banking-api')
sync_service = SyncService()
app.log.setLevel(chalicelib.config.log_level)
authorizer = IAMAuthorizer()


def handle_error(ex: Union[AppError]):
    # app.log.error(ex.error_message)
    app.log.exception(ex)
    response = {
        'status': 'failed',
        'error': {
            'code': ex.app_error_code,
            'details': ex.error_message
        }
    }
    return Response(body=json.dumps(response), status_code=ex.http_error_code,
                    headers={'Content-Type': 'application/json'})


@contextmanager
def app_error_handling():
    try:
        yield
    except AppError as e:
        app.log.exception(e)
        response = {
            'status': 'failed',
            'error': {
                'code': e.app_error_code,
                'details': e.error_message
            }
        }
        return Response(body=json.dumps(response), status_code=e.http_error_code,
                        headers={'Content-Type': 'application/json'})


@app.route('/swagger_json', methods=['GET'])
def swagger_json() -> Response:
    with open("./chalicelib/swagger.json") as f:
        swgr_json = json.load(f)
    return Response(body=json.dumps(swgr_json), status_code=200, headers={"Content-Type": "application/json"})


@app.route('/account_types', methods=['GET'])
def account_types() -> Response:
    response = {
        'status': 'success',
        'account_types': [e.name for e in chalicelib.config.AccountTypeEnum]
    }
    return Response(body=json.dumps(response), status_code=200, headers={'Content-Type': 'application/json'})


@app.route('/admin_access', methods=['PUT'], authorizer=authorizer)
def give_admin_access() -> Response:
    """
    Grant Admin access. (Only for ease of demo.)
    """
    try:
        account_number = extract_callers_account_number(app)
        SyncService.give_admin_access(account_number)
        response = {
            'status': 'success'
        }
        return Response(body=json.dumps(response), status_code=200, headers={'Content-Type': 'application/json'})
    except AppError as ex:
        return handle_error(ex)


@app.route('/admin_access', methods=['DELETE'], authorizer=authorizer)
def revoke_admin_access() -> Response:
    """
    Revoke Admin access. (Only for ease of demo.)
    """
    try:
        account_number = extract_callers_account_number(app)
        SyncService.revoke_admin_access(account_number)
        response = {
            'status': 'success'
        }
        return Response(body=json.dumps(response), status_code=200, headers={'Content-Type': 'application/json'})
    except AppError as ex:
        return handle_error(ex)


@app.route('/accounts', methods=['PUT'], authorizer=authorizer)
def create_account() -> Response:
    """
    Create Account of specific type.
    """
    with app_error_handling():
        try:
            account_number = extract_callers_account_number(app)
            initial_balance = extract_initial_balance(app)
            account_type = check_account_type(app.current_request.json_body.get('account_type'))
            app.log.info(f"Received request to create account for {account_number} of type '{account_type.value}' with "
                         f"initial balance={initial_balance}")
            SyncService.create_account(account_number=account_number, account_type=account_type,
                                       initial_balance=initial_balance,
                                       request_id=app.current_request.context.get('event_id'))
            response = {
                'status': 'success'
            }
            app.log.info(f"""Created account for {account_number} of type '{account_type.value}' with \
initial balance={initial_balance}""")
            return Response(body=json.dumps(response), status_code=200, headers={'Content-Type': 'application/json'})
        except AppError as ex:
            return handle_error(ex)


@app.route('/accounts', methods=['GET'], authorizer=authorizer)
def list_accounts() -> Response:
    """
    List own accounts (if caller's a non-admin) OR list all accounts (if caller's an amin.)
    """
    with app_error_handling():
        try:
            account_number = extract_callers_account_number(app)
            limit = extract_result_limit(app)
            last_evaluated_key = extract_last_evaluated_key(app)
            lst, new_last_evaluated_key = SyncService.list_accounts(account_number, limit, last_evaluated_key)
            response = {
                'status': 'success',
                'accounts': lst
            }
            response = Response(body=json.dumps(response), status_code=200, headers={'Content-Type': 'application/json'})
            if new_last_evaluated_key is not None:
                response.headers['x-page-last-evaluated-key'] = json.dumps(new_last_evaluated_key, separators=(',', ':'))
            return response
        except AppError as ex:
            return handle_error(ex)


@app.route('/accounts/{account_type}/balance', methods=['GET'], authorizer=authorizer)
def get_account_balance(account_type: str) -> Response:
    """
    Get account balance.
    """
    with app_error_handling():
        try:
            account_number = extract_callers_account_number(app)
            account_type_enum = check_account_type(account_type)
            balance = SyncService.get_balance(account_number, account_type_enum)
            response = {
                'status': 'success',
                'balance': balance
            }
            return Response(body=json.dumps(response), status_code=200, headers={'Content-Type': 'application/json'})
        except AppError as ex:
            return handle_error(ex)


@app.route('/accounts/{account_type}', methods=['DELETE'], authorizer=authorizer)
def delete_account(account_type: str):
    """
    Delete account.
    """
    with app_error_handling():
        try:
            account_number = extract_callers_account_number(app)
            account_type_enum = check_account_type(account_type)
            app.log.info(f"Received request to delete '{account_type_enum.value}' account for {account_number}.")
            SyncService.delete_account(account_number=account_number, account_type=account_type_enum,
                                       request_id=app.current_request.context.get('event_id'))
            response = {
                'status': 'success'
            }
            app.log.info(f"Deleted '{account_type_enum.value}' account for {account_number}.")
            return Response(body=json.dumps(response), status_code=200, headers={'Content-Type': 'application/json'})
        except AppError as ex:
            return handle_error(ex)


@app.route('/accounts/{account_type}/transfers', methods=['POST'], authorizer=authorizer)
def transfer(account_type: str):
    """
    Transfer between accounts.
    """
    with app_error_handling():
        try:
            src_account_number = extract_callers_account_number(app)
            src_account_type_enum = check_account_type(account_type)
            dest_account_number = extract_dest_account_number(app)
            dest_account_type_enum = check_account_type(app.current_request.json_body.get('dest_account_type'))
            amount = extract_amount(app)
            if src_account_number == dest_account_number and src_account_type_enum == dest_account_type_enum:
                raise TransferWithinSameAccountError(amount, src_account_number, src_account_type_enum.value,
                                                     dest_account_number, dest_account_type_enum.value)
            app.log.info(f"""Received request for transferring amount={amount} \
FROM {src_account_number}:{src_account_type_enum.value} TO {dest_account_number}:{dest_account_type_enum.value}""")
            src_balance, dest_balance = SyncService.transfer(amount=amount, src_account_number=src_account_number,
                                                             src_account_type=src_account_type_enum,
                                                             dest_account_number=dest_account_number,
                                                             dest_account_type=dest_account_type_enum,
                                                             request_id=app.current_request.context.get('event_id'))
            response = {
                'status': 'success',
                'src': {
                    'account_number': src_account_number,
                    'account_type': src_account_type_enum.value,
                    'balance': src_balance
                }
            }
            if src_account_number == dest_account_number:
                response['dest'] = {
                    'account_number': dest_account_number,
                    'account_type': dest_account_type_enum.value,
                    'balance': dest_balance
                }
            app.log.info(f"""Transferred amount={amount} FROM {src_account_number}:{src_account_type_enum.value} TO \
{dest_account_number}:{dest_account_type_enum.value}""")
            return Response(body=json.dumps(response), status_code=200, headers={'Content-Type': 'application/json'})
        except AppError as ex:
            return handle_error(ex)

