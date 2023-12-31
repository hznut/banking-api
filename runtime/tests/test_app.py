import json
import pytest


@pytest.mark.parametrize("caller_account_id", [None])
def test_create_account_invalid_account_id(test_client):
    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'savings', 'initial_balance': 100}))
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'
    # assert response.json_body['error']['code'] == 4001


@pytest.mark.parametrize("caller_account_id", ["123456789012"])
def test_all_ops_on_unregistered_account(test_client):
    # List accounts
    response = test_client.http.get("/accounts", headers={'Content-Type': 'application/json'})
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'
    # Get balance
    response = test_client.http.get("/accounts/checking/balance", headers={'Content-Type': 'application/json'})
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'
    # Del
    response = test_client.http.delete("/accounts/savings", headers={'Content-Type': 'application/json'})
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'
    # Transfer
    response = test_client.http.post("/accounts/savings/transfers",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'dest_account_type': 'hsa', 'dest_account': '987654321098',
                                                     'amount': 100}))
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'


@pytest.mark.parametrize("caller_account_id", ["123456789012"])
def test_create_account_invalid_input(test_client):
    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'savings', 'initial_balance': "l00"}))
    assert response.status_code == 400
    # assert response.json_body['error']['code'] == 4002
    assert response.json_body['status'] == 'failed'

    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'fixed', 'initial_balance': 100}))
    assert response.status_code == 400
    # assert response.json_body['error']['code'] == 4003
    assert response.json_body['status'] == 'failed'


@pytest.mark.parametrize("caller_account_id", ["123456789012"])
def test_create_first_account(test_client):
    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'checking', 'initial_balance': 100}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success'}

    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'savings', 'initial_balance': 500}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success'}

    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'hsa', 'initial_balance': 250}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success'}


@pytest.mark.parametrize("caller_account_id", ["987654321098"])
def test_create_another_account(test_client):
    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'checking', 'initial_balance': 100}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success'}

    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'savings', 'initial_balance': 500}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success'}

    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'hsa', 'initial_balance': 0}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success'}


@pytest.mark.parametrize("caller_account_id", ["123456789012"])
def test_get_first_account_balance(test_client):
    response = test_client.http.get("/accounts/fixed/balance",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'
    # assert response.json_body['error']['code'] == 4003

    response = test_client.http.get("/accounts/checking/balance",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert response.json_body == {'status': 'success', 'balance': 100}
    response = test_client.http.get("/accounts/savings/balance",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert response.json_body == {'status': 'success', 'balance': 500}
    response = test_client.http.get("/accounts/hsa/balance",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert response.json_body == {'status': 'success', 'balance': 250}

    response = test_client.http.get("/accounts/brokerage/balance",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'
    # assert response.json_body['error']['code'] == 4005


@pytest.mark.parametrize("caller_account_id", ["123456789012"])
def test_create_same_account_again(test_client):
    # Duplicate request
    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'checking', 'initial_balance': 100}))
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'
    # assert response.json_body['error']['code'] == 4004

    # Repeat with different initial balance.
    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'checking', 'initial_balance': 200}))
    assert response.status_code == 400
    assert response.json_body['status'] == 'failed'
    # assert response.json_body['error']['code'] == 4004


@pytest.mark.parametrize("caller_account_id", ["123456789012"])
def test_list_accounts(test_client):
    response = test_client.http.get("/accounts", headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert len(response.json_body['accounts']) == 3
    assert {'account_number': '123456789012', 'account_type': 'checking'} in response.json_body['accounts']
    assert {'account_number': '123456789012', 'account_type': 'savings'} in response.json_body['accounts']
    assert {'account_number': '123456789012', 'account_type': 'hsa'} in response.json_body['accounts']
    # Pagination
    lst = []
    response = test_client.http.get("/accounts?limit=2", headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert response.json_body['status'] == 'success'
    assert response.json_body.get('accounts') is not None
    assert len(response.json_body['accounts']) == 2
    lst += response.json_body['accounts']
    lst_eval_key = response.headers.get('x-page-last-evaluated-key')
    assert lst_eval_key is not None
    response = test_client.http.get("/accounts?limit=2",
                                    headers={'Content-Type': 'application/json', 'x-page-last-evaluated-key': lst_eval_key})
    assert response.status_code == 200
    assert response.json_body['status'] == 'success'
    assert response.json_body.get('accounts') is not None
    assert len(response.json_body['accounts']) == 1
    lst += response.json_body['accounts']
    lst_eval_key = response.headers.get('x-page-last-evaluated-key')
    assert lst_eval_key is None
    assert len(lst) == 3
    assert {'account_number': '123456789012', 'account_type': 'checking'} in lst
    assert {'account_number': '123456789012', 'account_type': 'savings'} in lst
    assert {'account_number': '123456789012', 'account_type': 'hsa'} in lst


@pytest.mark.parametrize("caller_account_id", ["987654321098"])
def test_delete_account(test_client):
    # Create account
    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'brokerage', 'initial_balance': 0}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success'}
    # List accounts
    response = test_client.http.get("/accounts",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert len(response.json_body['accounts']) == 4
    assert {'account_number': '987654321098', 'account_type': 'checking'} in response.json_body['accounts']
    assert {'account_number': '987654321098', 'account_type': 'savings'} in response.json_body['accounts']
    assert {'account_number': '987654321098', 'account_type': 'hsa'} in response.json_body['accounts']
    assert {'account_number': '987654321098', 'account_type': 'brokerage'} in response.json_body['accounts']
    # Del account success
    response = test_client.http.delete("/accounts/brokerage",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    # List accounts
    response = test_client.http.get("/accounts",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert len(response.json_body['accounts']) == 3
    assert {'account_number': '987654321098', 'account_type': 'checking'} in response.json_body['accounts']
    assert {'account_number': '987654321098', 'account_type': 'savings'} in response.json_body['accounts']
    assert {'account_number': '987654321098', 'account_type': 'hsa'} in response.json_body['accounts']
    # Del account failure
    response = test_client.http.delete("/accounts/savings",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 500
    # assert response.json_body['error']['code'] == 5003


@pytest.mark.parametrize("caller_account_id", ["987654321098"])
def test_recreate_account(test_client):
    response = test_client.http.put("/accounts",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'account_type': 'brokerage', 'initial_balance': 150}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success'}

    response = test_client.http.get("/accounts/brokerage/balance",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert response.json_body == {'status': 'success', 'balance': 150}


@pytest.mark.parametrize("caller_account_id", ["123456789012"])
def test_transfer_own_account(test_client):
    # Same account types
    response = test_client.http.post("/accounts/savings/transfers",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'dest_account_type': 'savings', 'dest_account': '123456789012',
                                                     'amount': 100}))
    assert response.status_code == 400
    # Different account types
    response = test_client.http.post("/accounts/savings/transfers",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'dest_account_type': 'hsa', 'dest_account': '123456789012',
                                                     'amount': 100}))
    assert response.status_code == 200
    assert response.json_body['src'] == {'account_number': '123456789012', 'account_type': 'savings', 'balance': 400}
    # assert response.json_body['dest'] == {'account_number': '123456789012', 'account_type': 'hsa', 'balance': 350}
    response = test_client.http.get("/accounts/savings/balance", headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert response.json_body == {'status': 'success', 'balance': 400}
    response = test_client.http.get("/accounts/hsa/balance", headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert response.json_body == {'status': 'success', 'balance': 350}


@pytest.mark.parametrize("caller_account_id", ["987654321098"])
def test_delete_recipients_account(test_client):
    # Del account success
    response = test_client.http.delete("/accounts/hsa",
                                    headers={'Content-Type': 'application/json'})
    assert response.status_code == 200


@pytest.mark.parametrize("caller_account_id", ["123456789012"])
def test_transfer_cross_account(test_client):
    # Invalid transfer requests
    response = test_client.http.post("/accounts/checking/transfers",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'dest_account_type': 'checking', 'dest_account': '987654321098',
                                                     'amount': 0}))
    assert response.status_code == 400
    # assert response.json_body['error']['code'] == 4013
    response = test_client.http.post("/accounts/fixed/transfers",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'dest_account_type': 'checking', 'dest_account': '987654321098',
                                                     'amount': 0}))
    assert response.status_code == 400
    # assert response.json_body['error']['code'] == 4003
    # Transfer failed due to insufficient funds
    response = test_client.http.post("/accounts/checking/transfers",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'dest_account_type': 'checking', 'dest_account': '987654321098',
                                                     'amount': 110}))
    assert response.status_code == 400
    # assert response.json_body['error']['code'] == 5005
    # Transfer success
    response = test_client.http.post("/accounts/checking/transfers",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'dest_account_type': 'checking', 'dest_account': '987654321098',
                                                     'amount': 30}))
    assert response.status_code == 200
    assert response.json_body == {'status': 'success',
                                  'src': {'account_number': '123456789012', 'account_type': 'checking', 'balance': 70}}
    # Transfer failed due to inactive account
    response = test_client.http.post("/accounts/checking/transfers",
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({'dest_account_type': 'hsa', 'dest_account': '987654321098',
                                                     'amount': 20}))
    assert response.status_code == 400
    # assert response.json_body['error']['code'] == 5006


@pytest.mark.parametrize("caller_account_id", ["987654321098"])
def test_balance_after_transfer(test_client):
    response = test_client.http.get("/accounts/checking/balance", headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert response.json_body == {'status': 'success', 'balance': 130}


@pytest.mark.parametrize("caller_account_id", ["987654321098"])
def test_list_accounts_as_admin(test_client):
    # Get list as admin
    response = test_client.http.put("/admin_access", headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    response = test_client.http.get("/accounts", headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
    assert len(response.json_body['accounts']) == 6
    assert {'account_number': '123456789012', 'account_type': 'checking'} in response.json_body['accounts']
    assert {'account_number': '123456789012', 'account_type': 'savings'} in response.json_body['accounts']
    assert {'account_number': '123456789012', 'account_type': 'hsa'} in response.json_body['accounts']
    assert {'account_number': '987654321098', 'account_type': 'checking'} in response.json_body['accounts']
    assert {'account_number': '987654321098', 'account_type': 'savings'} in response.json_body['accounts']
    assert {'account_number': '987654321098', 'account_type': 'brokerage'} in response.json_body['accounts']
    response = test_client.http.delete("/admin_access", headers={'Content-Type': 'application/json'})
    assert response.status_code == 200
