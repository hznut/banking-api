from chalice import Chalice
from chalicelib.config import log_level, AccountTypeEnum
from chalicelib.utils.exceptions import BadRequestError
from typing import Dict, Any
from schema import Schema
import json


def extract_callers_account_number(app: Chalice) -> str:
    app.log.debug(f"app.current_request.context['identity']={app.current_request.context['identity']}")
    if ('identity' in app.current_request.context and 'accountId' in app.current_request.context['identity'] and
            app.current_request.context['identity']['accountId'] is not None):
        app.log.debug(f"Caller's account_number={app.current_request.context['identity']['accountId']}")
        return app.current_request.context['identity']['accountId']
    else:
        raise BadRequestError(4001, f"Request is missing AWS account id.")


def extract_dest_account_number(app: Chalice) -> str:
    acc_number = app.current_request.json_body.get('dest_account')
    if acc_number is None:
        raise BadRequestError(4011, f"dest_account is missing!")
    return acc_number


def extract_amount(app: Chalice) -> int:
    try:
        amount = int(app.current_request.json_body['amount'])
        if amount <= 0:
            raise BadRequestError(4013, f"amount is missing OR is not a positive integer.")
        return amount
    except BadRequestError as e:
        raise e
    except Exception as e:
        raise BadRequestError(4012, f"amount is missing OR is not a positive integer.") from e


def extract_initial_balance(app: Chalice) -> int:
    try:
        initial_balance = int(app.current_request.json_body['initial_balance'])
        if initial_balance < 0:
            raise BadRequestError(4002, f"initial_balance is missing OR is not a positive integer.")
        return initial_balance
    except BadRequestError as e:
        raise e
    except Exception as e:
        raise BadRequestError(4002, f"initial_balance is missing OR is not a positive integer.") from e


def check_account_type(acc_type: str) -> AccountTypeEnum:
    try:
        return AccountTypeEnum.from_str(acc_type)
    except LookupError as e:
        raise BadRequestError(4003, f"account_type '{acc_type}' is invalid!") from e


def extract_result_limit(app: Chalice) -> int:
    if app.current_request.query_params is None:
        return 10
    x = app.current_request.query_params.get('limit')
    if x is None:
        return 10
    else:
        try:
            x = int(x)
        except Exception as e:
            raise BadRequestError(4006, f"limit={x} is not a positive integer.") from e

        # if x < 10:
        #     raise BadRequestError(4006, f"limit={x} is less than 10. Min value is 10.")

        return x


def extract_last_account_info(app: Chalice) -> (str, AccountTypeEnum):
    last_account_number = app.current_request.query_params.get('last_account_number')
    last_account_type_str = app.current_request.query_params.get('last_account_type')
    if last_account_number is None or len(last_account_number) == 0:
        return None, None

    if last_account_type_str is None or len(last_account_type_str) == 0:
        raise BadRequestError(4007, f"last_account_type corresponding to last_account_number={last_account_number} "
                                    f"is missing.")
    else:
        try:
            last_account_type = AccountTypeEnum.from_str(last_account_type_str)
            return last_account_number, last_account_type
        except LookupError as e:
            raise BadRequestError(4008, f"last_account_type={last_account_type_str} is invalid!") from e


def extract_last_evaluated_key(app: Chalice) -> Any:
    try:
        x_page_last_evaluated_key = app.current_request.headers.get('x-page-last-evaluated-key')
        if x_page_last_evaluated_key is None:
            return None
        else:
            last_evaluated_key = json.loads(x_page_last_evaluated_key)
            return last_evaluated_key
    except json.JSONDecodeError as e:
        raise BadRequestError(4010, f"Invalid format for x-page-last-evaluated-key={x_page_last_evaluated_key}")

