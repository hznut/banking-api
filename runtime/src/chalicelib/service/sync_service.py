from chalicelib.db.orm import BankAccount
from chalicelib.config import AccountTypeEnum
from typing import Dict, Any


class SyncService:
    @staticmethod
    def create_account(account_number: str, account_type: AccountTypeEnum, initial_balance: int, request_id=None):
        BankAccount.create_new_account(account_number=account_number, account_type=account_type,
                                       initial_balance=initial_balance, request_id=request_id)

    @staticmethod
    def list_accounts(account_number: str, limit=10, last_evaluated_key=None) -> ([Dict], Any):
        return BankAccount.list_accounts(account_number, limit, last_evaluated_key)

    @staticmethod
    def get_balance(account_number: str, account_type: AccountTypeEnum) -> int:
        return BankAccount.get_balance(account_number, account_type)

    @staticmethod
    def delete_account(account_number: str, account_type: AccountTypeEnum, request_id=None) -> None:
        return BankAccount.delete_account(account_number, account_type, request_id=request_id)

    @staticmethod
    def transfer(amount: int, src_account_number: str, src_account_type: AccountTypeEnum, dest_account_number: str,
                 dest_account_type: AccountTypeEnum, request_id=None) -> (int, int):
        return BankAccount.transfer(amount, src_account_number, src_account_type, dest_account_number,
                                    dest_account_type, request_id)

    @staticmethod
    def give_admin_access(account_number: str) -> None:
        return BankAccount.set_admin_access(account_number, 'Y')

    @staticmethod
    def revoke_admin_access(account_number: str) -> None:
        return BankAccount.set_admin_access(account_number, 'N')
