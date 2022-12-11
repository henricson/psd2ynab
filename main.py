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


def check_valid_requisition():
    if not os.path.exists('requisition_cache.txt'):
        return False
    with open('requisition_cache.txt', 'r') as requisition_file:
        requisition_object = json.loads(requisition_file.read())
        if (datetime.now(timezone.utc) - datetime.strptime(requisition_object["created"],
                                                           "%Y-%m-%dT%H:%M:%S.%f%z")).days < 89:
            return requisition_object
        return False


def create_requisition(token, bank_id):
    requisition_cache = check_valid_requisition()
    if requisition_cache is False:
        response = requests.post('https://ob.nordigen.com/api/v2/requisitions/',
                                 headers={"Authorization": "Bearer " + token},
                                 data={"institution_id": bank_id, "redirect": "https://www.google.com"})
        response.raise_for_status()
        jsonResponse = response.json()
        cache_requisition(jsonResponse)
        print(
            "Please go to the following link and log in to your bank account. Please come back to the CLI when you are done.")
        print(jsonResponse["link"])
        input("Please press enter to continue when you have completed the login.")
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
    print(ynab_transactions)
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
    bank_id_local = input("Enter the index of the bank you wish to link: ")
    if not bank_id_local.isdigit():
        print("Please enter a valid number.")
        prompt_bank()
    return bank_id_local


if __name__ == '__main__':
    try:
        token = aquire_token(nordgen_client_id, nordgen_client_secret)
        banks = list_banks(token, country_code)

        bank_id = prompt_bank()
        requisition = create_requisition(token, banks[int(bank_id)]["id"])
        accounts = list_accounts(token, requisition["id"])
        print(accounts)
        available_account_ids = []
        for (key, value) in enumerate(accounts):
            account_details = get_account_details(token, value)
            available_account_ids.append(str(key) + ": " + account_details["name"])
        print("Select the account you want to import transactions from:")
        for account in available_account_ids:
            print(account)
        account_id = input("Enter the index: ")
        if not account_id.isdigit():
            print("Please enter a valid number. Exiting.")
            exit(1)
        transactions = list_transactions(token, accounts[int(account_id)])
        ynab_transactions = map_transactions_to_ynab(transactions)
        print(ynab_transactions)
        import_response = ynab_upload_transactions(ynab_transactions)
        print(str(len(ynab_transactions)) + " transactions uploaded to YNAB.")
        print(import_response)
    except Exception as e:
        print(e)
        exit(1)
