class AppError(Exception):
    def __init__(self, app_error_code: int, error_message: str, http_error_code: int):
        super().__init__(error_message)
        self.app_error_code = app_error_code
        self.error_message = error_message
        self.http_error_code = http_error_code


class BadRequestError(AppError):
    def __init__(self, app_error_code: int, error_message: str):
        super().__init__(app_error_code, error_message, 400)


class AccountAlreadyExistsError(AppError):
    def __init__(self, account_number: str, account_type: str):
        super().__init__(4004, f"Account with account_number={account_number} and account_type={account_type} "
                               f"already exists.", 400)


class AccountDoesNotExistError(AppError):
    def __init__(self, account_number: str):
        super().__init__(4005, f"Account with account_number={account_number} doesn't exist OR isn't active.", 400)


class AccountTypeDoesNotExistError(AppError):
    def __init__(self, account_number: str, account_type: str):
        super().__init__(4005, f"Account with account_number={account_number} and account_type={account_type} "
                               f"doesn't exist OR isn't active.", 400)


class AccountCreationFailedError(AppError):
    def __init__(self, account_number: str, account_type: str):
        super().__init__(5001, f"Couldn't create account of type {account_type} for {account_number} due to  "
                               f"internal error. Retry after some time.", 500)


class AccountFetchFailedError(AppError):
    def __init__(self, account_number=None):
        if account_number is not None:
            mssg = f"Couldn't fetch accounts for {account_number} due to internal error. Retry after some time."
        else:
            mssg = f"Couldn't fetch all accounts requested by admin {account_number} due to internal error. " \
                   f"Retry after some time."
        super().__init__(5002, mssg, 500)


class DeleteFailedNonZeroBalanceError(AppError):
    def __init__(self, account_number: str, account_type: str):
        super().__init__(5003, f"Couldn't delete account {account_number} {account_type} due to non-zero balance.", 500)


class DeleteFailedError(AppError):
    def __init__(self, account_number: str, account_type: str):
        super().__init__(5004, f"Couldn't delete account {account_number} {account_type} due to internal error. "
                               f"Retry after some time.", 500)


class TransferWithinSameAccountError(AppError):
    def __init__(self, amount: int, src_account_number: str, src_account_type: str, dest_account_number: str,
                 dest_account_type: str):
        super().__init__(4014, f"Source and destination accounts are same {src_account_number}:{src_account_type}.",
                         400)


class TransferFailedInsufficientFundsError(AppError):
    def __init__(self, amount: int, src_account_number: str, src_account_type: str, dest_account_number: str,
                 dest_account_type: str):
        super().__init__(4015, f"""Couldn't transfer amount={amount} from account \
{src_account_number}:{src_account_type} to {dest_account_number}:{dest_account_type} due to \
insufficient funds.""", 400)


class TransferFailedAccountDoesNotExistError(AppError):
    def __init__(self, amount: int, src_account_number: str, src_account_type: str, dest_account_number: str,
                 dest_account_type: str):
        super().__init__(4016, f"""Couldn't transfer amount={amount} from account \
{src_account_number}:{src_account_type} to {dest_account_number}:{dest_account_type} due to \
either/both account(s) not found.""", 400)


class TransferFailedError(AppError):
    def __init__(self, amount: int, src_account_number: str, src_account_type: str, dest_account_number: str,
                 dest_account_type: str):
        super().__init__(5007, f"""Couldn't transfer amount={amount} from account \
{src_account_number}:{src_account_type} to {dest_account_number}:{dest_account_type} due to internal error. \
Retry after some time.""", 500)
