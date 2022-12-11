import requests
import json
import os
from datetime import datetime, timezone
import re
from requests.exceptions import HTTPError
from settings import *


def aquire_token(secret_id, secret_key):
    try:
        response = requests.post('https://ob.nordigen.com/api/v2/token/new/',
                                 data={"secret_id": secret_id, "secret_key": secret_key})
        response.raise_for_status()
        jsonResponse = response.json()
        return jsonResponse["access"]

    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')


def list_banks(token, country_code):
    response = requests.get('https://ob.nordigen.com/api/v2/institutions/?country=' + country_code,
                            headers={"Authorization": "Bearer " + token})
    response.raise_for_status()
    jsonResponse = response.json()
    return jsonResponse


def create_agreement(token, bank_id, redirect_url):
    response = requests.post('https://ob.nordigen.com/api/v2/agreements/enduser',
                             headers={"Authorization": "Bearer " + token},
                             data={"institution_id  ": bank_id})
    response.raise_for_status()
    jsonResponse = response.json()
    return jsonResponse["id"]


def cache_requisition(requsition_object):
    with open('requisition_cache.txt', 'w') as convert_file:
        convert_file.write(json.dumps(requsition_object))


def check_valid_requisition(bank_id):
    if not os.path.exists('requisition_cache.txt'):
        return False
    with open('requisition_cache.txt', 'r') as requisition_file:
        requisition_object = json.loads(requisition_file.read())
        if (datetime.now(timezone.utc) - datetime.strptime(requisition_object["created"],
                                                           "%Y-%m-%dT%H:%M:%S.%f%z")).days < 89 and bank_id == \
                requisition_object["institution_id"]:
            return requisition_object
        print("Please log in again.")
        return False


def create_requisition(token, bank_id):
    requisition_cache = check_valid_requisition(bank_id)
    if requisition_cache is False:
        response = requests.post('https://ob.nordigen.com/api/v2/requisitions/',
                                 headers={"Authorization": "Bearer " + token},
                                 data={"institution_id": bank_id, "redirect": "https://www.google.com"})
        response.raise_for_status()
        jsonResponse = response.json()
        print(
            "Please go to the following link and log in to your bank account. Please come back to the CLI when you are done.")
        print(jsonResponse["link"])
        input("\nPlease press enter to continue when you have completed the login.\n")
        return jsonResponse
    else:
        return requisition_cache


def list_accounts(token, link_id):
    try:
        response = requests.get('https://ob.nordigen.com/api/v2/requisitions/' + link_id,
                                headers={"Authorization": "Bearer " + token})
        response.raise_for_status()
        jsonResponse = response.json()
        return jsonResponse["accounts"]
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')


def get_account_details(token, account_id):
    response = requests.get('https://ob.nordigen.com/api/v2/accounts/' + account_id + '/details',
                            headers={"Authorization": "Bearer " + token})
    response.raise_for_status()
    jsonResponse = response.json()
    return jsonResponse["account"]


def list_transactions(token, account_id):
    response = requests.get('https://ob.nordigen.com/api/v2/accounts/' + account_id + '/transactions',
                            headers={"Authorization": "Bearer " + token})
    response.raise_for_status()
    jsonResponse = response.json()
    return jsonResponse["transactions"]["booked"]


def clean_text(rgx_list, text):
    new_text = text
    for rgx_match in rgx_list:
        new_text = re.sub(rgx_match, '', new_text)
    return new_text


def map_transactions_to_ynab(psd2_transactions):
    ynab_transactions = [{"account_id": ynab_account_id, "date": t.get("bookingDate"),
                          "amount": int(float(t.get("transactionAmount").get("amount")) * 1000),
                          "payee_name": clean_text(
                              ["Visa, ", "Varekjøp, Kl\. [0-9]{2}.[0-9]{2} Versjon 2 Aut. [0-9]{6}, "],
                              t.get("creditorName", t.get("additionalInformation",
                                                          t.get("remittanceInformationUnstructured")))),
                          "memo": t.get("additionalInformation", t.get("remittanceInformationUnstructured")),
                          "approved": True,
                          "import_id": t.get("transactionId", t.get("internalTransactionId")).replace("_",
                                                                                                      "")}
                         for t in
                         transactions]
    return ynab_transactions


def ynab_upload_transactions(ynab_transactions):
    try:
        response = requests.post("https://api.youneedabudget.com/v1/budgets/" + ynab_budget_id + "/transactions",
                                 headers={"Authorization": "Bearer " + ynab_personal_access_token,
                                          "Content-Type": "application/json"},
                                 data=json.dumps({"transactions": ynab_transactions}))
        response.raise_for_status()
        jsonResponse = response.json()
        return jsonResponse
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')


def prompt_bank():
    print("Please select the bank you want to connect to (country code set to: " + country_code + "):")
    for (key, value) in enumerate(banks):
        print(str(key) + ": ", value["name"])
    bank_id_local = input("\nEnter the index of the bank you wish to link: ")
    if not bank_id_local.isdigit():
        print("Please enter a valid number.")
        prompt_bank()
    return bank_id_local


def prompt_account():
    account_id_local = input("\nEnter the index of the account you wish to import: ")
    if not account_id_local.isdigit():
        print("Please enter a valid number.")
        prompt_account()
    return account_id_local


def get_account_task(value, token):
    account_details = get_account_details(token, value)
    return {"name": account_details["name"], "id": value}


if __name__ == '__main__':
    import multiprocessing
    from multiprocessing import freeze_support

    try:
        token = aquire_token(nordgen_client_id, nordgen_client_secret)
        banks = list_banks(token, country_code)

        bank_id = prompt_bank()
        requisition = create_requisition(token, banks[int(bank_id)]["id"])
        cache_requisition(requisition)
        accounts = list_accounts(token, requisition["id"])
        available_account_ids = []
        print("\nAvailable accounts:\n")

        with multiprocessing.Pool() as pool:
            # call the function for each item in parallel, get results as tasks complete
            for key, bank in enumerate(pool.starmap(get_account_task, [(a, token) for a in accounts])):
                available_account_ids.append(bank["id"])
                print(str(key) + ": " + bank["name"])

        account_id = prompt_account()
        print("\nFetching and importing transactions into YNAB....\n")
        transactions = list_transactions(token, available_account_ids[int(account_id)])
        ynab_transactions = map_transactions_to_ynab(transactions)
        import_response = ynab_upload_transactions(ynab_transactions)

        print(str(len(import_response["data"]["transaction_ids"])) + " transactions uploaded to YNAB.")
        print(str(len(
            import_response["data"]["duplicate_import_ids"])) + " duplicante transactions not uploaded to YNAB.")
    except Exception as e:
        print(e)
        exit(1)
