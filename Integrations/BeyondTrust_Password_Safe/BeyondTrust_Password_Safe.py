import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

''' IMPORTS '''

import json
import requests

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()

''' GLOBALS/PARAMS '''

USERNAME = demisto.params().get('credentials', {}).get('identifier')
PASSWORD = demisto.params().get('credentials', {}).get('password')
API_KEY = demisto.params().get('key')
SYSTEM_NAME = demisto.params().get('system_name')
# Remove trailing slash to prevent wrong URL path to service
SERVER = demisto.params()['url'][:-1] \
    if (demisto.params()['url'] and demisto.params()['url'].endswith('/')) else demisto.params()['url']
# Should we use SSL
USE_SSL = not demisto.params().get('insecure', False)
# Service base URL
BASE_URL = SERVER + '/BeyondTrust/api/public/v3'
# Headers to be sent in requests
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
}

SESSION = requests.session()
RAISE_EXCEPTION_ON_ERROR: bool = False

''' HELPER FUNCTIONS '''


def http_request(method, suffix_url, data=None):
    url = BASE_URL + suffix_url
    try:
        res = SESSION.request(
            method,
            url,
            verify=USE_SSL,
            data=data,
            headers=HEADERS
        )
    except requests.exceptions.SSLError:
        ssl_error = 'Could not connect to BeyondTrust: Could not verify certificate.'
        if RAISE_EXCEPTION_ON_ERROR:
            raise Exception(ssl_error)
        return return_error(ssl_error)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
            requests.exceptions.TooManyRedirects, requests.exceptions.RequestException) as e:
        connection_error = 'Could not connect to BeyondTrust: {}'.format(str(e))
        if RAISE_EXCEPTION_ON_ERROR:
            raise Exception(connection_error)
        return return_error(connection_error)

    # Handle error responses gracefully
    if res.status_code not in {200, 201, 204}:
        if res.status_code == 401:
            return_error('Could not connect to BeyondTrust - wrong credentials')
        else:
            return_error(f'Error in API call to BeyondSafe Integration [{res.status_code}] - {res.content})')
    try:
        return res.json()
    except ValueError:
        return None


def signin():

    suffix_url = '/Auth/SignAppin'
    header = {'Authorization': f'PS-Auth key={API_KEY}; runas={USERNAME}; pwd=[{PASSWORD}];'}
    SESSION.headers.update(header)
    SESSION.post(BASE_URL + suffix_url, verify=USE_SSL)


def signout():
    suffix_url = '/auth/signout'
    SESSION.post(BASE_URL + suffix_url)


''' COMMANDS + REQUESTS FUNCTIONS '''


def get_managed_accounts_request():
    suffix_url = '/managedaccounts'
    response = http_request('GET', suffix_url)

    return response


def get_managed_accounts():
    """
    Returns a list of Managed Accounts that can be requested by the current user.
    """
    data = []
    headers = ['AccountName', 'AccountID', 'AssetName', 'AssetID', 'DomainName', 'LastChangeDate', 'NextChangeDate']
    managed_accounts = get_managed_accounts_request()
    for account in managed_accounts:
        data.append({
            'LastChangeDate': account.get('LastChangeDate'),
            'NextChangeDate': account.get('NextChangeDate'),
            'AssetID': account.get('SystemId'),
            'AssetName': account.get('SystemName'),
            'DomainName': account.get('DomainName'),
            'AccountID': account.get('AccountId'),
            'AccountName': account.get('AccountName')

        })

    entry_context = {'BeyondTrust.Account(val.AccountID === obj.AccountID)': managed_accounts}

    return_outputs(tableToMarkdown('BeyondTrust Managed Accounts', data, headers, removeNull=True), entry_context,
                   managed_accounts)


def get_managed_systems_request():
    suffix_url = '/managedsystems'
    response = http_request('GET', suffix_url)

    return response


def get_managed_systems():
    """
    Returns a list of Managed Systems.
    """
    data = []
    managed_systems = get_managed_systems_request()
    for managed_system in managed_systems:
        data.append({
            'ManagedAssetID': managed_system.get('ManagedSystemID'),
            'ChangeFrequencyDays': managed_system.get('ChangeFrequencyDays'),
            'AssetID': managed_system.get('AssetID'),
            'DatabaseID': managed_system.get('DatabaseID'),
            'DirectoryID': managed_system.get('DirectoryID'),
            'AssetName': managed_system.get('SystemName'),
            'PlatformID': managed_system.get('PlatformID'),
            'Port': managed_system.get('Port')
        })

    entry_context = {'BeyondTrust.System(val.ManagedSystemID === obj.ManagedSystemID)': managed_systems}

    return_outputs(tableToMarkdown('BeyondTrust Managed Systems', data, removeNull=True), entry_context,
                   managed_systems)


def create_release_request(data: dict):
    suffix_url = '/requests'
    response = http_request('POST', suffix_url, data=data)

    return response


def create_release():
    """
    Creates a new release request.
    Retrieves the credentials for an approved and active (not expired) credentials release request.

    demisto parameter: (string) access_type
        The type of access requested (View, RDP, SSH). Defualt is "View".

    demisto parameter: (int) system_id
        ID of the Managed System to request.

    demisto parameter: (int) account_id
        ID of the Managed Account to request.

    demisto parameter: (int) duration_minutes
        The request duration (in minutes).

    demisto parameter: (string) reason
        The reason for the request.

    demisto parameter: (int) access_policy_schedule_id
        The Schedule ID of an Access Policy to use for the request. If omitted, automatically selects the best schedule.

    demisto parameter: (bool) conflict_option
        The conflict resolution option to use if an existing request is found for the same user,
        system, and account ("reuse" or "renew").
    """
    access_type = demisto.args().get('access_type')
    system_id = demisto.args().get('system_id')
    account_id = demisto.args().get('account_id')
    duration_minutes = demisto.args().get('duration_minutes')
    reason = demisto.args().get('reason')
    conflict_option = demisto.args().get('conflict_option')

    data = {
        'SystemId': system_id,
        'AccountId': account_id,
        'DurationMinutes': duration_minutes
    }

    if access_type:
        data['AccessType'] = access_type

    if reason:
        data['Reason'] = reason

    if conflict_option:
        data['ConflictOption'] = conflict_option

    request = create_release_request(str(data))
    request_id = str(request)

    credentials = get_credentials_request(request_id)

    response = {
        'RequestID': request_id,
        'Password': credentials
    }

    entry_context = {'BeyondTrust.Request(val.AccountID === obj.AccountID)': createContext(response)}
    return_outputs(tableToMarkdown('The new release was created successfully.', response), entry_context, response)


def get_credentials_request(request_id: str):

    suffix_url = '/credentials/' + request_id
    response = http_request('GET', suffix_url)

    return response


def get_credentials():
    """
    Retrieves the credentials for an approved and active (not expired) credentials release request.

    demisto parameter: (int) request_id
        ID of the Request for which to retrieve the credentials
    """

    request_id = demisto.args().get('request_id')
    request = str(request_id)
    response = get_credentials_request(request)

    demisto.results('The credentials for BeyondTrust request: ' + response)


def check_in_credentials_request(request_id: str, data: dict):
    suffix_url = f'/Requests/{request_id}/Checkin'
    response = http_request('PUT', suffix_url, data=json.dumps(data))

    return response


def check_in_credentials():
    """
    Checks-in/releases a request before it has expired.

    demisto parameter: (int) request_id
        ID of the request to release.

    demisto parameter: (string) reason
        A reason or comment why the request is being released.

    """
    request_id = demisto.args().get('request_id')
    reason = str(demisto.args().get('reason')).encode('utf-8')

    data = {'Reason': reason if reason else ''}

    check_in_credentials_request(request_id, data)

    demisto.results('The release was successfully checked-in/released')


def change_credentials_request(account_id: str, data: dict) -> requests.Response:

    suffix_url = f'/ManagedAccounts/{account_id}/Credentials'
    response = http_request('PUT', suffix_url, data=json.dumps(data))

    return response


def change_credentials():
    """
    Updates the credentials for a Managed Account, optionally applying the change to the Managed System.

    demisto parameter: (int) account_id
        ID of the account for which to set the credentials.

    demisto parameter: (string) password
        The new password to set. If not given, generates a new, random password.

    demisto parameter: (string) public_key
        The new public key to set on the host. This is required if PrivateKey is given and updateSystem=true.

    demisto parameter: (string) private_key
        The private key to set (provide Passphrase if encrypted).

    demisto parameter: (string) pass_phrase
        The passphrase to use for an encrypted private key.

    demisto parameter: (bool) update_system
        Whether to update the credentials on the referenced system.

    """
    account_id = demisto.args().get('account_id')
    password = demisto.args().get('password')
    public_key = demisto.args().get('public_key')
    private_key = demisto.args().get('private_key')
    pass_phrase = demisto.args().get('pass_phrase')
    update_system = demisto.args().get('update_system')

    data = {
        'AccountId': account_id
    }

    if password:
        data['Password'] = password

    if private_key:
        if public_key and update_system is True:
            data['PrivateKey'] = private_key
            data['PublicKey'] = public_key
        else:
            return_error('Missing public key')

    if pass_phrase:
        data['Passphrase'] = pass_phrase

    change_credentials_request(account_id, data)

    demisto.results('The password has been changed')


def fetch_credentials():

    credentials = []
    identifier = demisto.args().get('identifier')
    duration_minutes = 1
    account_info = get_managed_accounts_request()

    for account in account_info:
        account_name = account.get('AccountName')
        system_name = account.get('SystemName')
        if SYSTEM_NAME and system_name != SYSTEM_NAME:
            continue
        item = {
            'SystemId': account.get('SystemId'),
            'AccountId': account.get('AccountId'),
            'DurationMinutes': duration_minutes
        }

        release_id = create_release_request(str(item))

        password = get_credentials_request(str(release_id))

        credentials.append({
            'user': account_name,
            'password': password,
            'name': system_name
        })

    if identifier:
        credentials = list(filter(lambda c: c.get('name', '') == identifier, credentials))

    demisto.credentials(credentials)


''' COMMANDS MANAGER / SWITCH PANEL '''

LOG('Command being called is %s' % (demisto.command()))

try:
    handle_proxy()
    signin()
    if demisto.command() == 'test-module':
        # This is the call made when pressing the integration test button.
        get_managed_accounts_request()
        demisto.results('ok')
    elif demisto.command() == 'beyondtrust-get-managed-accounts':
        get_managed_accounts()
    elif demisto.command() == 'beyondtrust-get-managed-systems':
        get_managed_systems()
    elif demisto.command() == 'beyondtrust-create-release-request':
        create_release()
    elif demisto.command() == 'beyondtrust-get-credentials':
        get_credentials()
    elif demisto.command() == 'beyondtrust-check-in-credentials':
        check_in_credentials()
    elif demisto.command() == 'beyondtrust-change-credentials':
        change_credentials()
    elif demisto.command() == 'fetch-credentials':
        fetch_credentials()

# Log exceptions
except Exception as e:
    LOG(e.message)
    LOG.print_log()
    raise
finally:
    signout()
