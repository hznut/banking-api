from chalicelib.config import log_level, ddb_table_name, ddb_table_region, dynamodb_endpoint
from pynamodb.models import Model
from pynamodb.exceptions import QueryError, TransactWriteError, UpdateError, PutError
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, UTCDateTimeAttribute, BooleanAttribute, JSONAttribute
)
from pynamodb.indexes import GlobalSecondaryIndex, AllProjection
from pynamodb.connection import Connection
from pynamodb.transactions import TransactWrite, TransactGet
from datetime import datetime
from chalicelib.config import AccountTypeEnum
from chalicelib.utils.exceptions import (AppError, AccountAlreadyExistsError, AccountCreationFailedError,
                                         AccountTypeDoesNotExistError, AccountFetchFailedError, BadRequestError,
                                         DeleteFailedError, DeleteFailedNonZeroBalanceError,
                                         TransferFailedInsufficientFundsError, TransferFailedAccountDoesNotExistError,
                                         TransferFailedError, AccountDoesNotExistError)
import logging
from typing import Dict, Any
from enum import Enum, auto

logging.basicConfig()
log = logging.getLogger("pynamodb")
log.setLevel(log_level)
log.propagate = True
connection = Connection(region=ddb_table_region, host=dynamodb_endpoint)


class EntityType(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    acc_metadata = auto()
    acc_balance = auto()
    transfer = auto()


def create_sk(account_type: AccountTypeEnum, version: int) -> str:
    return f"{EntityType.acc_balance.name}_{account_type.value}_v{version}"


def get_v0_sk(account_type: AccountTypeEnum) -> str:
    return create_sk(account_type, 0)


class BankAccount(Model):
    """
    pk: Will be same as account_number
    sk: Can be:
                * acc_balance_<account_type>_v<version>
                    * acc_balance_<account_type>_v0 points to the current active account of that type.
                    * All other versions are inactive with zero balance.
                * transfer
                * acc_metadata
    """
    class Meta:
        table_name = ddb_table_name
        region = ddb_table_region
        host = dynamodb_endpoint
        billing_mode = 'PAY_PER_REQUEST'

    pk = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)
    entity_type = UnicodeAttribute()
    account_number = UnicodeAttribute(null=True)
    account_type = UnicodeAttribute(null=True)
    balance = NumberAttribute(null=True)
    is_account_active = UnicodeAttribute(null=True)
    is_admin = UnicodeAttribute(null=True)
    last_version = JSONAttribute(null=True)
    version = NumberAttribute(null=True)
    dest_account_number = UnicodeAttribute(null=True)
    dest_account_type = UnicodeAttribute(null=True)
    transfer_amount = NumberAttribute(null=True)
    created_at = UTCDateTimeAttribute(default=datetime.now())
    updated_at = UTCDateTimeAttribute(default=datetime.now())

    class ViewAllActiveAccountsIndex(GlobalSecondaryIndex):
        is_account_active = UnicodeAttribute(hash_key=True)

        class Meta:
            index_name = 'view_all_active_accounts_index'
            projection = AllProjection

    view_all_active_accounts_index = ViewAllActiveAccountsIndex()

    @staticmethod
    def create_new_account(account_number: str, account_type: AccountTypeEnum, initial_balance: int, request_id=None):
        """
        Checks if acc_metadata exists for this account else creates it.
        Gets last version for given account_type.
        Then creates a new active account for the given account_type with next version (version = last_version + 1).
        """
        try:
            account_metadata = BankAccount.get(account_number, EntityType.acc_metadata.name, consistent_read=True)
            last_version = int(account_metadata.last_version[account_type.value])
            log.debug(f"create_new_account: last_version={last_version}")
        except BankAccount.DoesNotExist as e:
            last_version = 0
            try:
                new_acc_metadata = BankAccount(account_number, EntityType.acc_metadata.name,
                                               entity_type=EntityType.acc_metadata.name,  is_admin='N',
                                               last_version=dict((e.value, 0) for e in AccountTypeEnum))
                new_acc_metadata.save(condition=(BankAccount.pk.does_not_exist() | BankAccount.sk.does_not_exist()))
            except PutError as e:
                log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
                if e.cause_response_code == "ConditionalCheckFailedException":
                    account_metadata.refresh(consistent_read=True)
                    last_version = int(account_metadata.last_version[account_type.value])
                else:
                    raise AccountCreationFailedError(account_number, account_type.value) from e

        try:
            new_acc = BankAccount(account_number, get_v0_sk(account_type),
                                  entity_type=EntityType.acc_balance.value, version=(last_version + 1),
                                  account_number=account_number,
                                  account_type=account_type.value, balance=initial_balance, is_account_active='Y')
            new_acc.save(condition=(BankAccount.pk.does_not_exist() | BankAccount.sk.does_not_exist() |
                                    (BankAccount.is_account_active == 'N')))
        except PutError as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            if e.cause_response_code == "ConditionalCheckFailedException":
                raise AccountAlreadyExistsError(account_number, account_type.value) from e
            else:
                raise AccountCreationFailedError(account_number, account_type.value) from e
        except AppError as e:
            raise e
        except Exception as e:
            raise AccountCreationFailedError(account_number, account_type.value) from e

    @staticmethod
    def is_admin_account(account_number: str) -> bool:
        result = BankAccount.get(account_number, EntityType.acc_metadata.name)
        return result.is_admin == 'Y'

    @staticmethod
    def list_accounts(account_number: str, limit: int, last_evaluated_key=None) -> ([Dict], Any):
        """
        If admin account then iterate through all active accounts else iterate only through active accounts of caller.
        """
        result = []
        try:
            is_admin = BankAccount.is_admin_account(account_number)
            log.debug(f"is_admin_account={is_admin}")
            if is_admin:
                res = BankAccount.view_all_active_accounts_index.query('Y',
                                                                       attributes_to_get=['account_number',
                                                                                          'account_type'],
                                                                       limit=limit,
                                                                       last_evaluated_key=last_evaluated_key)
            else:
                res = BankAccount.query(account_number,
                                        range_key_condition=(BankAccount.sk.startswith(
                                            f"{EntityType.acc_balance.name}_")),
                                        filter_condition=(BankAccount.is_account_active == 'Y'),
                                        attributes_to_get=['account_number', 'account_type'],
                                        limit=limit,
                                        last_evaluated_key=last_evaluated_key)

            for item in res:
                result.append({'account_number': item.account_number, 'account_type': item.account_type})

            log.debug(f"new last_evaluated_key={res.last_evaluated_key}")
            return result, res.last_evaluated_key
        except BankAccount.DoesNotExist as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            raise AccountDoesNotExistError(account_number) from e
        except QueryError as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            raise BadRequestError(4009, f"Possibly invalid last_evaluated_key={last_evaluated_key}") from e
        except Exception as e:
            if is_admin:
                raise AccountFetchFailedError() from e
            else:
                raise AccountFetchFailedError(account_number) from e

    @staticmethod
    def get_balance(account_number: str, account_type: AccountTypeEnum) -> int:
        try:
            result = BankAccount.get(account_number, get_v0_sk(account_type))
            if result is not None:
                return result.balance

            raise AccountTypeDoesNotExistError(account_number, account_type.value)
        except BankAccount.DoesNotExist as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            raise AccountTypeDoesNotExistError(account_number, account_type.value) from e
        except AppError as e:
            raise e
        except Exception as e:
            raise AccountFetchFailedError() from e

    @staticmethod
    def delete_account(account_number, account_type, request_id=None) -> None:
        """
        For the given account_number if the current acc_balance_<account_type>_v0 has zero balance then mark it as
        inactive and make it the next version i.e. acc_balance_<account_type>_vN effectively removing the
        acc_balance_<account_type>_v0.
        """
        try:
            with TransactWrite(connection=connection, client_request_token=request_id) as transaction:
                v0 = BankAccount.get(account_number, get_v0_sk(account_type))
                # Finalizing the version
                vn = BankAccount(account_number, create_sk(account_type, v0.version),
                                 entity_type=EntityType.acc_balance.name, version=v0.version,
                                 account_number=account_number, account_type=account_type.value,
                                 balance=v0.balance, is_account_active='N', created_at=v0.created_at,
                                 updated_at=datetime.now())
                transaction.save(vn, condition=(BankAccount.sk.does_not_exist()))
                transaction.delete(v0, condition=(BankAccount.balance == 0))
                try:
                    # Update metadata
                    account_metadata = BankAccount.get(account_number, EntityType.acc_metadata.name)
                    last_version_map = account_metadata.last_version
                    last_version_map[account_type.value] = last_version_map[account_type.value] + 1
                    transaction.update(account_metadata, actions=[BankAccount.last_version.set(last_version_map)])
                except (UpdateError, TransactWriteError) as e:
                    # Failure to update metadata shouldn't result in non-zero balance error c'se that'll be misleading.
                    log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
                    raise DeleteFailedError(account_number, account_type.value) from e
        except BankAccount.DoesNotExist as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            raise AccountTypeDoesNotExistError(account_number, account_type.value) from e
        except AppError as e:
            raise e
        except (PutError, TransactWriteError, UpdateError) as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            raise DeleteFailedNonZeroBalanceError(account_number, account_type.value) from e
        except Exception as e:
            raise DeleteFailedError(account_number, account_type.value) from e

    @staticmethod
    def transfer(amount: int, src_account_number: str, src_account_type: AccountTypeEnum, dest_account_number: str,
                 dest_account_type: AccountTypeEnum, request_id=None) -> (int, int):
        try:
            src_account = BankAccount.get(src_account_number, get_v0_sk(src_account_type))
            dest_account = BankAccount.get(dest_account_number, get_v0_sk(dest_account_type))

            with TransactWrite(connection=connection, client_request_token=request_id) as transaction:
                transaction.update(src_account,
                                   actions=[BankAccount.balance.add(amount * -1)],
                                   condition=((BankAccount.balance >= amount) &
                                              (BankAccount.is_account_active == 'Y')))
                transaction.update(dest_account,
                                   actions=[BankAccount.balance.add(amount)],
                                   condition=(BankAccount.is_account_active == 'Y'))

                transfer = BankAccount(src_account_number, EntityType.transfer.value,
                                       entity_type=EntityType.transfer.value,
                                       account_type=src_account_type.value,
                                       dest_account_number=dest_account_number,
                                       dest_account_type=dest_account_type.value,
                                       transfer_amount=(-1 * amount))
                transaction.save(transfer)

            src_account.refresh()
            dest_account.refresh()
            return src_account.balance, dest_account.balance
        except BankAccount.DoesNotExist as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            raise TransferFailedAccountDoesNotExistError(amount, src_account_number, src_account_type.value,
                                                         dest_account_number, dest_account_type.value) from e
        except (TransactWriteError, UpdateError) as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            raise TransferFailedInsufficientFundsError(amount, src_account_number, src_account_type.value,
                                                       dest_account_number, dest_account_type.value) from e
        except Exception as e:
            raise TransferFailedError(amount, src_account_number, src_account_type.value,
                                      dest_account_number, dest_account_type.value) from e

    @staticmethod
    def set_admin_access(account_number: str, is_admin: str) -> None:
        try:
            acc_metadata = BankAccount.get(account_number, EntityType.acc_metadata.value)
            acc_metadata.update(actions=[BankAccount.is_admin.set(is_admin)])
        except BankAccount.DoesNotExist as e:
            log.debug(f"{e.cause_response_code}: {e.cause_response_message}")
            raise AccountDoesNotExistError(account_number) from e
        except Exception as e:
            raise AccountFetchFailedError(account_number) from e
