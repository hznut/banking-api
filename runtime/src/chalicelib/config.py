import os
from enum import Enum, auto
import logging


def load_log_level():
    s = os.environ.get('LOG_LEVEL', 'INFO')
    m = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARN': logging.WARN,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'FATAL': logging.FATAL,
        'CRITICAL': logging.CRITICAL
    }
    return m.get(s, logging.INFO)


dynamodb_endpoint = os.environ.get('DYNAMO_ENDPOINT', None)
ddb_table_arn = os.environ.get('APP_TABLE_ARN', None)
ddb_table_name = os.environ.get('APP_TABLE_NAME', None)
ddb_table_region = os.environ.get('APP_TABLE_REGION', None)
log_level = load_log_level()


class AccountTypeEnum(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    checking = auto()
    savings = auto()
    money_market = auto()
    certificate_of_deposit = auto()
    brokerage = auto()
    traditional_ira = auto()
    roth_ira = auto()
    retirement_401k = auto()
    hsa = auto()
    cryptocurrency = auto()

    @staticmethod
    def from_str(s: str):
        try:
            return AccountTypeEnum.__members__[s.lower()]
        except Exception as e:
            raise LookupError(f"No AccountTypeEnum matching {s}") from e

