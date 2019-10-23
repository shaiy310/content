import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

'''IMPORTS'''
from google.cloud import kms_v1
from google.cloud.kms_v1 import enums
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from json import JSONDecodeError
import base64
from typing import Any, Dict, Tuple, List

"""
For further information about the API used in the integration see:

1) Google KMS API Client libraries information:
    https://cloud.google.com/kms/docs/reference/libraries

2) Git resource with some API use examples:
    https://github.com/GoogleCloudPlatform/python-docs-samples/tree/master/kms/api-client

"""

INTEGRATION_NAME = 'Google Key Management System'
# lowercase with `-` dividers
INTEGRATION_COMMAND_NAME = 'google-kms-'
# No dividers
INTEGRATION_CONTEXT_NAME = 'GoogleKMS'

DEMISTO_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
RFC3339_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


class Client:
    def __init__(self, params: Dict[str, Any]):
        self.project = params.get('project')
        self.location = params.get('location')
        self.key_ring = params.get('key_ring')
        self.service_account = params.get('service_account')
        self.role = params.get('role')

        # Creates an API client for the KMS API.
        try:
            self.kms_client = self._init_kms_client()

        except JSONDecodeError:
            raise Exception("Service Account json is not formatted well please re-enter it.")

        handle_proxy()

    def _init_kms_client(self):
        """Creates the Python API client for Google Cloud KMS using service account credentials.
        """
        credentials_file_name = demisto.uniqueFile() + '.json'
        credentials_file_path = os.path.join(os.getcwd(), credentials_file_name)

        with open(credentials_file_path, 'w') as creds_file:
            json_object = json.loads(self.service_account)
            json.dump(json_object, creds_file)

        return kms_v1.KeyManagementServiceClient.from_service_account_json(credentials_file_path)


"""HELPER FUNCTIONS"""


def arg_dict_creator(string: Any):
    """Creates a Dict from a CSV string.

    Args:
        string(str): CSV string - formatted as 'field1:value1,field2:value2'.

    Returns:
        Dict from string representation.
    """
    if not string:
        return None

    split_string = string.split(',')
    arg_dict = {}
    for section in split_string:
        key, value = section.split(':', 1)
        arg_dict[key] = value

    return arg_dict


def key_context_creation(res: Any, project_id: str, location_id: str, key_ring_id: str) -> Dict:
    """Creates GoogleKMS.CryptoKey context.

    Args:
        res(Any): `~google.cloud.kms_v1.types.CryptoKey` instance.
        project_id(str): the project id
        location_id(str): the location id
        key_ring_id(str): the KeyRing id

    Returns:
        Dict representing GoogleKMS.CryptoKey context.
    """
    # remove the CryptoKey path and leave only the name
    pre_name = f"projects/{project_id}/locations/{location_id}/keyRings/{key_ring_id}/cryptoKeys/"
    name = str(res.name).replace(pre_name, '')

    key_context = {
        'Name': name,
        'Purpose': enums.CryptoKey.CryptoKeyPurpose(res.purpose).name,
        'CreationTime': datetime.fromtimestamp(int(res.create_time.seconds)).strftime(DEMISTO_DATETIME_FORMAT),
        'NextRotationTime': datetime.fromtimestamp(int(res.next_rotation_time.seconds)).strftime(DEMISTO_DATETIME_FORMAT),
        'RotationPeriod': f'{str(res.rotation_period.seconds)}s',
        'Labels': arg_dict_creator(str(res.labels)[1:-1]),
        'VersionTemplate': {
            'ProtectionLevel': enums.ProtectionLevel(res.version_template.protection_level).name,
            'Algorithm': enums.CryptoKeyVersion.CryptoKeyVersionAlgorithm(res.version_template.algorithm).name,
        }
    }
    # if primary CryptoKeyVersion exists and is returned create context for it.
    # Note: As part of the API - Asymmetric keys do not return primary CryptoKeyVersion info.
    if res.primary and res.primary.name and len(res.primary.name) > 0:
        key_context['PrimaryCryptoKeyVersion'] = {
            'Name': res.primary.name,
            'State': enums.CryptoKeyVersion.CryptoKeyVersionState(res.primary.state).name,
            'CreationTime': datetime.fromtimestamp(int(res.primary.create_time.seconds)).strftime(DEMISTO_DATETIME_FORMAT),
            'ProtectionLevel': enums.ProtectionLevel(res.primary.protection_level).name,
            'Algorithm': enums.CryptoKeyVersion.CryptoKeyVersionAlgorithm(res.primary.algorithm).name,
            'GenerateTime': datetime.fromtimestamp(int(res.primary.generate_time.seconds)).strftime(DEMISTO_DATETIME_FORMAT)
        }

    return key_context


def crypto_key_to_json(crypto_key: Any) -> Dict:
    """Creates a json dict from `~google.cloud.kms_v1.types.CryptoKey` instance to use as raw response.

    Args:
        crypto_key(Any): `~google.cloud.kms_v1.types.CryptoKey` instance.

    Returns:
        A json Dict containing the raw response.
    """
    key_json = {
        'name': crypto_key.name,
        'purpose': enums.CryptoKey.CryptoKeyPurpose(crypto_key.purpose).name,
        'create_time': {
            'seconds': crypto_key.create_time.seconds,
            'nanos': crypto_key.create_time.nanos

        },
        'next_rotation_time': {
            'seconds': crypto_key.next_rotation_time.seconds,
            'nanos': crypto_key.next_rotation_time.nanos
        },
        'rotation_period': {
            'seconds': crypto_key.rotation_period.seconds
        },
        'labels': arg_dict_creator(str(crypto_key.labels)[1:-1]),
        'version_template': {
            'protection_level': enums.ProtectionLevel(crypto_key.version_template.protection_level).name,
            'algorithm': enums.CryptoKeyVersion.CryptoKeyVersionAlgorithm(crypto_key.version_template.algorithm).name,
        }
    }

    if crypto_key.primary:
        key_json['primary'] = {
            'name': crypto_key.primary.name,
            'state': enums.CryptoKeyVersion.CryptoKeyVersionState(crypto_key.primary.state).name,
            'create_time': {
                'seconds': crypto_key.primary.create_time.seconds,
                'nanos': crypto_key.primary.create_time.nanos
            },
            'protection_level': enums.ProtectionLevel(crypto_key.primary.protection_level).name,
            'algorithm': enums.CryptoKeyVersion.CryptoKeyVersionAlgorithm(crypto_key.primary.algorithm).name,
            'generate_time': {
                'seconds': crypto_key.primary.generate_time.seconds,
                'nanos': crypto_key.primary.generate_time.nanos
            }
        }

    return key_json


def demisto_args_extract(client: Client, args: Dict[str, Any]) -> Tuple[str, str, str, str]:
    """Extracts IDs to use for KMS functions.

    Args:
        args(dict): Demisto arguments.
        client(Client): User Client.

    Returns:
        A tuple containing strings representing the required IDs.
    """
    project_id = client.project

    location_id = args.get('location')
    if location_id == 'default':
        location_id = client.location

    key_ring_id = args.get('key_ring')
    if key_ring_id == 'default':
        key_ring_id = client.key_ring

    crypto_key_id = args.get('crypto_key')
    return str(project_id), str(location_id), str(key_ring_id), str(crypto_key_id)


def get_update_mask(args: Dict[str, Any]) -> Dict:
    """ Creates the 'updateMask' parameter for the command
    which is a comma separated list of fields to update.

    Args:
        args(dict): Demisto args indicating which field to update.

    Returns:
        A Dict to use as the params for update command.
    """
    update_mask = []
    if args.get('labels') is not None:
        update_mask.append('labels')

    if args.get('next_rotation_time') is not None:
        update_mask.append('next_rotation_time')

    if args.get('purpose') is not None:
        update_mask.append('purpose')

    if args.get('rotation_period') is not None:
        update_mask.append('rotation_period')

    if args.get('attestation') is not None:
        update_mask.append('primary.attestation')

    if args.get('state') is not None:
        update_mask.append('primary.state')

    if args.get('algorithm') is not None:
        update_mask.append('version_template.algorithm')

    if args.get('protection_level') is not None:
        update_mask.append('version_template.protection_level')

    return {
        'paths': update_mask
    }


def get_update_command_body(args: Dict[str, Any], update_mask: List) -> Dict:
    """Creates update command request body, in accordance with the updateMask.

    Args:
        args(Dict): Demisto arguments containing the updated values.
        update_mask(List): List of fields to update.

    Returns:
        Dict to be used as body for update command
    """
    body = {}  # type:Dict[str,Any]
    if 'labels' in update_mask:
        # Add label dictionary to body
        body['labels'] = arg_dict_creator(args.get('labels'))

    if 'next_rotation_time' in update_mask:
        if str(args.get('next_rotation_time')).isdigit():
            # If next_rotation_time given is a timestamp enter it as is
            body['next_rotation_time'] = {'seconds': int(str(args.get('next_rotation_time')))}

        else:
            # If next_rotation_time is date string, convert it to timestamp
            body['next_rotation_time'] = {'seconds': int(datetime.strptime(str(args.get('next_rotation_time')),
                                                                           RFC3339_DATETIME_FORMAT).timestamp())}

    if 'purpose' in update_mask:
        # Add purpose enum to body
        body['purpose'] = enums.CryptoKey.CryptoKeyPurpose[args.get('purpose')].value

    if 'rotation_period' in update_mask:
        # Add rotation_period to body
        body['rotation_period'] = {'seconds': int(str(args.get('rotation_period')))}

    if 'primary.attestation' in update_mask or 'primary.state' in update_mask:
        # Init the 'primary' sub-dictionary
        body['primary'] = {}

        if 'primary.attestation' in update_mask:
            # Add attestation dict to 'primary' sub-dictionary
            body['primary']['attestation'] = arg_dict_creator(args.get('attestation'))

        if 'primary.state' in update_mask:
            # Add state enum to 'primary' sub-dictionary
            body['primary']['state'] = enums.CryptoKeyVersion.CryptoKeyVersionState[args.get('state')].value

    if 'version_template.algorithm' in update_mask or 'version_template.protection_level' in update_mask:
        # Init the 'version_template' sun-dictionary
        body['version_template'] = {}

        if 'version_template.algorithm' in update_mask:
            # Add algorithm enum to 'version_template' sun-dictionary
            val = enums.CryptoKeyVersion.CryptoKeyVersionAlgorithm[args.get('algorithm')].value
            body['version_template']['algorithm'] = val

        if 'version_template.protection_level' in update_mask:
            # Add protection_level to 'version_template' sun-dictionary
            val = enums.ProtectionLevel[args.get('protection_level')].value
            body['version_template']['protection_level'] = val

    return body


def get_primary_key_version(project_id: str, location_id: str, key_ring_id: str, crypto_key_id: str,
                            client: Client) -> str:
    """ Return primary CryptoKeyVersion of a given CryptoKey.

    Args:
        project_id(str): Project of the CryptoKey.
        location_id(str): Location the CryptoKey is assigned to.
        key_ring_id(str): Key Ring in which the CryptoKey exists.
        crypto_key_id(str): The CryptoKey id.
        client(Client): User's Client.

    Returns:
        A string with the full path to the primary CryptoKeyVersion
    """
    # The resource name of the CryptoKey.
    crypto_key_name = client.kms_client.crypto_key_path(project_id, location_id, key_ring_id, crypto_key_id)

    # Get the CryptoKey and extract it's primary version path.
    crypto_key = client.kms_client.get_crypto_key(crypto_key_name)
    if crypto_key.primary.name is None:
        raise Exception(f"CryptoKey {crypto_key_name} has no primary CryptoKeyVersion")

    return str(crypto_key.primary.name)


"""GENERAL FUNCTIONS"""


def create_crypto_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Dict, Dict]:
    """Create a new CryptoKey.

    Args:
        client(Client): User Client.
        args(Dict): Demisto arguments.
    """
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)

    # The resource name of the KeyRing associated with the CryptoKey.
    key_ring_name = client.kms_client.key_ring_path(project_id, location_id, key_ring_id)

    if args.get('next_rotation_time'):
        # change next_rotation time from date to timestamp if needed.
        if not str(args.get('next_rotation_time')).isdigit():
            next_rotation_time = {
                'seconds': int(datetime.strptime(str(args.get('next_rotation_time')), RFC3339_DATETIME_FORMAT).timestamp())
            }

        else:
            next_rotation_time = {
                'seconds': int(str(args.get('next_rotation_time')))
            }

    else:
        # if not next rotation time given - set it to 90 days from now (default by Google)
        next_rotation_time = {
            'seconds': int((datetime.now() + timedelta(days=90)).timestamp())
        }

    # Create the CryptoKey object template
    crypto_key = {
        'purpose': enums.CryptoKey.CryptoKeyPurpose[args.get('purpose')].value,
        'next_rotation_time': next_rotation_time,
        'labels': arg_dict_creator(args.get('labels')),
        'rotation_period': {
            'seconds': int(str(args.get('rotation_period')))
        },
    }

    # Additional info in case CryptoKeyVersion is created
    if not args.get('skip_initial_version_creation') == 'true':
        crypto_key['primary'] = {
            'state': enums.CryptoKeyVersion.CryptoKeyVersionState[args.get('state')].value,
            'attestation': arg_dict_creator(args.get('attestation'))
        }
        crypto_key['version_template'] = {
            'algorithm': enums.CryptoKeyVersion.CryptoKeyVersionAlgorithm[args.get('algorithm')].value,
            'protection_level': enums.ProtectionLevel[args.get('protection_level')].value
        }

    # Create a CryptoKey for the given KeyRing.
    response = client.kms_client.create_crypto_key(key_ring_name, crypto_key_id, crypto_key,
                                                   args.get('skip_initial_version_creation') == 'true')

    context = key_context_creation(response, project_id, location_id, key_ring_id)

    return (
        tableToMarkdown("Google KMS CryptoKey info:", context, removeNull=True),
        {
            f'{INTEGRATION_CONTEXT_NAME}.CryptoKey(val.Name == obj.Name)': context,
        },
        crypto_key_to_json(response)
    )


def symmetric_encrypt_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Any, Any]:
    """Encrypt plaintext to ciphertext using a symmetric key.

    Args:
        client(Client): User Client.
        args(Dict): Demisto arguments.

    Returns:
        The encrypted ciphertext.
    """
    # handle given plaintext - revert it to base 64.
    if args.get('is_base64') == 'false':
        plaintext = base64.b64encode(bytes(str(args.get('plaintext')), 'utf-8'))

    else:
        plaintext = base64.b64decode(str(args.get('plaintext')))

    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)

    additional_authenticated_data = None
    if args.get('additional_authenticated_data'):
        additional_authenticated_data = base64.b64decode(str(args.get('additional_authenticated_data')))

    # The resource name of the CryptoKey.
    crypto_key_name = client.kms_client.crypto_key_path_path(project_id, location_id, key_ring_id, crypto_key_id)

    # Use the KMS API to encrypt the data.
    response = client.kms_client.encrypt(crypto_key_name, plaintext,
                                         additional_authenticated_data=additional_authenticated_data)

    # return the created ciphertext cleaned from additional characters.
    ciphertext = str(base64.b64encode(response.ciphertext))[2:-1]

    symmetric_encrypt_context = {
        'CryptoKey': crypto_key_id,
        'IsBase64': args.get('is_base64') == 'true',
        'Ciphertext': ciphertext
    }

    return (f"The text has been encrypted.\nCiphertext: {ciphertext}",
            {
                f'{INTEGRATION_CONTEXT_NAME}.SymmetricEncrypt(val.CryptoKey == obj.CryptoKey '
                f'&& val.IsBase64 == obj.IsBase64 && val.Ciphertext == obj.Ciphertext)': symmetric_encrypt_context,
            }, None)


def symmetric_decrypt_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Any, Any]:
    """Decrypt ciphertext to plaintext using a symmetric key.

    Args:
        client(Client): User Client.
        args(Dict): Demisto agruments.

    Returns:
        The decrypted text.
    """
    ciphertext = base64.b64decode(str(args.get('ciphertext')))
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)

    additional_authenticated_data = None
    if args.get('additional_authenticated_data'):
        additional_authenticated_data = base64.b64decode(str(args.get('additional_authenticated_data')))

    # The resource name of the CryptoKey.
    crypto_key_name = client.kms_client.crypto_key_path_path(project_id, location_id, key_ring_id, crypto_key_id)

    # Use the KMS API to decrypt the data.
    response = client.kms_client.decrypt(crypto_key_name, ciphertext,
                                         additional_authenticated_data=additional_authenticated_data)

    # handle the resulting plain text if it supposed to be in base64 and clean added characters.
    if args.get('is_base64') == 'true':
        plaintext = str(base64.b64encode(response.plaintext))[2:-1]

    else:
        plaintext = str(base64.b64decode(response.plaintext))[2:-1]

    symmetric_decrypt_context = {
        'CryptoKey': crypto_key_id,
        'IsBase64': args.get('is_base64') == 'true',
        'Plaintext': plaintext
    }

    return (f"The text has been decrypted.\nPlaintext: {plaintext}",
            {
                f'{INTEGRATION_CONTEXT_NAME}.SymmetricDecrypt(val.CryptoKey == obj.CryptoKey '
                f'&& val.IsBase64 == obj.IsBase64 && val.Plaintext == obj.Plaintext)': symmetric_decrypt_context,
            }, None)


def get_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Dict, Dict]:
    """Gets a CryptoKey.

    Args:
        client(Client): User Client.
        args(Dict): Demisto Arguments.
    """
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)

    # The resource name of the CryptoKey.
    crypto_key_name = client.kms_client.crypto_key_path(project_id, location_id, key_ring_id, crypto_key_id)

    # Get CryptoKey info.
    response = client.kms_client.get_crypto_key(crypto_key_name)

    context = key_context_creation(response, project_id, location_id, key_ring_id)

    return (
        tableToMarkdown("Google KMS CryptoKey info:", context, removeNull=True),
        {
            f'{INTEGRATION_CONTEXT_NAME}.CryptoKey(val.Name == obj.Name)': context,
        },
        crypto_key_to_json(response)
    )


def disable_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Any, Any]:
    """Disable a given CryptoKeyVersion.

    Args:
        client(Client): User Client.
        args(Dict): Demisto arguments.
    """
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)
    crypto_key_version = args.get('crypto_key_version')

    if crypto_key_version == 'default':
        # if no CryptoKeyVersion given extract the primary CryptoKeyVersion.
        crypto_key_version_name = get_primary_key_version(project_id, location_id, key_ring_id, crypto_key_id, client)

    else:
        # Construct the resource name of the CryptoKeyVersion.
        crypto_key_version_name = client.kms_client.crypto_key_version_path(project_id, location_id, key_ring_id,
                                                                            crypto_key_id, crypto_key_version)

    # if not CryptoKeyVersion is given nor was is extracted from the CryptoKey - raise error to the user.
    if crypto_key_version_name is None or len(crypto_key_version_name) == 0:
        raise Exception("Please insert primary CryptoKeyVersion ID")

    # Use the KMS API to disable the CryptoKeyVersion.
    new_state = enums.CryptoKeyVersion.CryptoKeyVersionState.DISABLED
    version = {'name': crypto_key_version_name, 'state': new_state}
    update_mask = {'paths': ["state"]}

    # Print results
    response = client.kms_client.update_crypto_key_version(version, update_mask)
    return (f'CryptoKeyVersion {crypto_key_version_name}\'s state has been set to '
            f'{enums.CryptoKeyVersion.CryptoKeyVersionState(response.state).name}.', None, None)


def enable_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Any, Any]:
    """Enable a CryptoKeyVersion.

    Args:
        client(Client): User Client.
        args(Dict): Demisto arguments.
    """
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)
    crypto_key_version = args.get('crypto_key_version')

    if crypto_key_version == 'default':
        # if no CryptoKeyVersion given extract the primary CryptoKeyVersion.
        crypto_key_version_name = get_primary_key_version(project_id, location_id, key_ring_id, crypto_key_id, client)

    else:
        # Construct the resource name of the CryptoKeyVersion.
        crypto_key_version_name = client.kms_client.crypto_key_version_path(project_id, location_id, key_ring_id,
                                                                            crypto_key_id, crypto_key_version)

    # if not CryptoKeyVersion is given nor was is extracted from the CryptoKey - raise error to the user.
    if crypto_key_version_name is None or len(crypto_key_version_name) == 0:
        raise Exception("Please insert primary CryptoKeyVersion ID")

    # Use the KMS API to enable the CryptoKeyVersion.
    new_state = enums.CryptoKeyVersion.CryptoKeyVersionState.ENABLED
    version = {'name': crypto_key_version_name, 'state': new_state}
    update_mask = {'paths': ["state"]}

    # Print results
    response = client.kms_client.update_crypto_key_version(version, update_mask)
    return(f'CryptoKeyVersion {crypto_key_version_name}\'s state has been set to '
           f'{enums.CryptoKeyVersion.CryptoKeyVersionState(response.state).name}.', None, None)


def destroy_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Any, Any]:
    """Schedule the destruction of a given CryptoKeyVersion.

    Args:
        client(Client): User Client.
        args(Dict): Demisto arguments.
    """
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)
    crypto_key_version = args.get('crypto_key_version')

    if crypto_key_version == 'default':
        # if no CryptoKeyVersion given extract the primary CryptoKeyVersion.
        crypto_key_version_name = get_primary_key_version(project_id, location_id, key_ring_id, crypto_key_id, client)

    else:
        # Construct the resource name of the CryptoKeyVersion.
        crypto_key_version_name = client.kms_client.crypto_key_version_path(project_id, location_id, key_ring_id,
                                                                            crypto_key_id, crypto_key_version)

    # if not CryptoKeyVersion is given nor was is extracted from the CryptoKey - raise error to the user.
    if crypto_key_version_name is None or len(crypto_key_version_name) == 0:
        raise Exception("Please insert primary CryptoKeyVersion ID")

    # Use the KMS API to mark the CryptoKeyVersion for destruction.
    response = client.kms_client.destroy_crypto_key_version(crypto_key_version_name)

    # Print results
    return (f'CryptoKeyVersion {crypto_key_version_name}\'s state has been set to '
            f'{enums.CryptoKeyVersion.CryptoKeyVersionState(response.state).name}, it will be destroyed in 24h.',
            None, None)


def restore_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Any, Any]:
    """Restores a CryptoKeyVersion scheduled for destruction.

    Args:
        client(Client): User Client.
        args(Dict): Demisto arguments.
    """
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)
    crypto_key_version = args.get('crypto_key_version')

    if crypto_key_version == 'default':
        # if no CryptoKeyVersion given extract the primary CryptoKeyVersion.
        crypto_key_version_name = get_primary_key_version(project_id, location_id, key_ring_id, crypto_key_id, client)

    else:
        # Construct the resource name of the CryptoKeyVersion.
        crypto_key_version_name = client.kms_client.crypto_key_version_path(project_id, location_id, key_ring_id,
                                                                            crypto_key_id, crypto_key_version)

    # if not CryptoKeyVersion is given nor was is extracted from the CryptoKey - raise error to the user.
    if crypto_key_version_name is None or len(crypto_key_version_name) == 0:
        raise Exception("Please insert primary CryptoKeyVersion ID")

    # Use the KMS API to restore the CryptoKeyVersion.
    response = client.kms_client.restore_crypto_key_version(crypto_key_version_name)

    # Print results
    return (f'CryptoKeyVersion {crypto_key_version_name}\'s state has been set to '
            f'{enums.CryptoKeyVersion.CryptoKeyVersionState(response.state).name}.', None, None)


def update_key_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Dict, Dict]:
    """Update a given CryptoKey.

    Args:
        client(Client): User Client.
        args(Dict): Demisto arguments.
    """
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)

    # The resource name of the CryptoKey.
    crypto_key_name = client.kms_client.crypto_key_path(project_id, location_id, key_ring_id, crypto_key_id)

    # create a list of fields to be updated using the command - the field is called update mask in the API.
    update_mask = get_update_mask(args)

    # create the body of the update request.
    crypto_key = get_update_command_body(args=args, update_mask=update_mask['paths'])
    crypto_key['name'] = crypto_key_name

    # update command using the KMS API.
    response = client.kms_client.update_crypto_key(crypto_key=crypto_key, update_mask=update_mask)

    context = key_context_creation(response, project_id, location_id, key_ring_id)
    return (
        tableToMarkdown("Google KMS CryptoKey info:", context, removeNull=True),
        {
            f'{INTEGRATION_CONTEXT_NAME}.CryptoKey(val.Name == obj.Name)': context,
        },
        crypto_key_to_json(response)
    )


def list_keys_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Dict, List]:
    """List All keys in a KeyRing.

    Args:
        client(Client): User Client.
        args(Dict): Demisto arguments.

    """
    project_id, location_id, key_ring_id, _ = demisto_args_extract(client, args)

    # Get the full path to the KeyRing in which to list the keys.
    key_ring_name = client.kms_client.key_ring_path(project_id, location_id, key_ring_id)

    # if needed add state filter.
    filter_state = args.get('key_state', None)

    response = client.kms_client.list_crypto_keys(key_ring_name, filter_=filter_state)

    overall_context = []  # type: List
    overall_raw = []  # type: List
    for crypto_key in response:
        overall_context.append(key_context_creation(crypto_key, project_id, location_id, key_ring_id))
        overall_raw.append(crypto_key_to_json(crypto_key))

    headers = ['CreationTime', 'Name', 'Labels', 'NextRotationTime', 'Purpose', 'RotationPeriod',
               'PrimaryCryptoKeyVersion', 'VersionTemplate']

    return (
        tableToMarkdown("CryptoKeys:", overall_context, removeNull=True, headers=headers),
        {
            f'{INTEGRATION_CONTEXT_NAME}.CryptoKey(val.Name == obj.Name)': overall_context,
        },
        overall_raw
    )


def asymmetric_encrypt_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Any, Any]:
    """Encrypt plainttext using an asymmetric key.

    Args:
        client(Client): User's client.
        args(dict): Demisto arguments.

    Returns:
        The encrypted ciphertext.
    """
    # handle the plaintext - convert to base64
    if args.get('is_base64') == 'false':
        plaintext = base64.b64encode(bytes(str(args.get('plaintext')), 'utf-8'))

    else:
        plaintext = base64.b64decode(str(args.get('plaintext')))

    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)
    crypto_key_version = args.get('crypto_key_version')

    # Construct the resource name of the CryptoKeyVersion.
    crypto_key_version_name = client.kms_client.crypto_key_version_path(project_id, location_id, key_ring_id,
                                                                        crypto_key_id, crypto_key_version)
    # get the CryptoKeyVersion info and check it's algorithm.
    crypto_key_version_info = client.kms_client.get_crypto_key_version(crypto_key_version_name)
    key_algo = enums.CryptoKeyVersion.CryptoKeyVersionAlgorithm(crypto_key_version_info.algorithm).name

    # Algorithm must be a "DECRYPT" type asymmetric algorithm - if not, raise an error to the user.
    if 'DECRYPT' not in key_algo:
        raise ValueError(f"{crypto_key_version_name} is not a valid asymmetric CryptoKeyVersion")

    # get public key of the asymmetric encryption.
    public_key_response = client.kms_client.get_public_key(crypto_key_version_name)
    key_txt = public_key_response.pem.encode('ascii')
    public_key = serialization.load_pem_public_key(key_txt, default_backend())

    # using the CryptoKeyVersion algorithm - create the necessary padding for the encryption.
    if 'SHA256' in key_algo:
        # create padding with SHA256
        pad = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                           algorithm=hashes.SHA256(),
                           label=None)
    else:
        # create padding with SHA512
        pad = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA512()),
                           algorithm=hashes.SHA512(),
                           label=None)

    # encrypt plaintext and return the cipertext without added characters.
    ciphertext = str(base64.b64encode(public_key.encrypt(plaintext, pad)))[2:-1]

    asymmetric_encrypt_context = {
        'CryptoKey': crypto_key_id,
        'IsBase64': args.get('is_base64') == 'true',
        'Ciphertext': ciphertext
    }

    return (f"The text has been encrypted.\nCiphertext: {ciphertext}",
            {
                f'{INTEGRATION_CONTEXT_NAME}.AsymmetricEncrypt(val.CryptoKey == obj.CryptoKey '
                f'&& val.IsBase64 == obj.IsBase64 && val.Ciphertext == obj.Ciphertext)': asymmetric_encrypt_context,
            }, None)


def asymmetric_decrypt_command(client: Client, args: Dict[str, Any]) -> Tuple[str, Any, Any]:
    """Decrypt chipertext to plaintext using asymmetric key.

    Args:
        client(Client): User's Client.
        args(dict): Demisto arguments.

    Returns:
        The decrypted plaintext.
    """
    project_id, location_id, key_ring_id, crypto_key_id = demisto_args_extract(client, args)
    crypto_key_version = args.get('crypto_key_version')

    # Construct the resource name of the CryptoKeyVersion.
    crypto_key_version_name = client.kms_client.crypto_key_version_path(project_id, location_id, key_ring_id,
                                                                        crypto_key_id, crypto_key_version)

    ciphertext = base64.b64decode(str(args.get('ciphertext')))

    response = client.kms_client.asymmetric_decrypt(crypto_key_version_name, ciphertext)

    # handle the created plaintext back to base64 if needed and clear added characters.
    if args.get('is_base64') == 'true':
        plaintext = str(base64.b64encode(response.plaintext))[2:-1]

    else:
        plaintext = str(base64.b64decode(response.plaintext))[2:-1]

    asymmetric_decrypt_context = {
        'CryptoKey': crypto_key_id,
        'IsBase64': args.get('is_base64') == 'true',
        'Plaintext': plaintext
    }

    return (f"The text has been decrypted.\nPlaintext: {plaintext}",
            {
                f'{INTEGRATION_CONTEXT_NAME}.AsymmetricDecrypt(val.CryptoKey == obj.CryptoKey '
                f'&& val.IsBase64 == obj.IsBase64 && val.Plaintext == obj.Plaintext)': asymmetric_decrypt_context,
            }, None)


def test_function(client: Client) -> None:
    """Test's user's input:
        for Encrypter, Decrypter, Encrypter/Decrypter Roles - checks Service account json formatting only.
        for Project-Admin and KMS-Admin Roles - checks the Service account json formatting and connection to project.

    Args:
        client(Client): User Client.
    """
    # if the user role is Encrypt/Decrypt related then no additional checks are possible.
    if client.role in ['Project-Admin', 'KMS-Admin']:
        # listing the KeyRings in order to check responses from the API.
        location_path = client.kms_client.location_path(client.project, client.location)
        # the response is a iterable containing the KeyRings info.
        response = client.kms_client.list_key_rings(location_path)

        # Count the number of existing KeyRings.
        if not list(response):
            raise Exception("No response - please check Project in Google Cloud KMS and Default Location")


def main():
    COMMANDS = {
        f'{INTEGRATION_COMMAND_NAME}create-key': (create_crypto_key_command, ['Project-Admin', 'KMS-Admin']),

        f'{INTEGRATION_COMMAND_NAME}symmetric-decrypt': (symmetric_decrypt_key_command, ['Decrypter',
                                                                                         'Encrypter/Decrypter',
                                                                                         'Project-Admin']),

        f'{INTEGRATION_COMMAND_NAME}symmetric-encrypt': (symmetric_encrypt_key_command, ['Encrypter',
                                                                                         'Encrypter/Decrypter',
                                                                                         'Project-Admin']),

        f'{INTEGRATION_COMMAND_NAME}get-key': (get_key_command, ['Project-Admin', 'KMS-Admin']),

        f'{INTEGRATION_COMMAND_NAME}update-key': (update_key_command, ['Project-Admin', 'KMS-Admin']),

        f'{INTEGRATION_COMMAND_NAME}destroy-key': (destroy_key_command, ['Project-Admin', 'KMS-Admin']),

        f'{INTEGRATION_COMMAND_NAME}restore-key': (restore_key_command, ['Project-Admin', 'KMS-Admin']),

        f'{INTEGRATION_COMMAND_NAME}disable-key': (disable_key_command, ['Project-Admin', 'KMS-Admin']),

        f'{INTEGRATION_COMMAND_NAME}enable-key': (enable_key_command, ['Project-Admin', 'KMS-Admin']),

        f'{INTEGRATION_COMMAND_NAME}list-keys': (list_keys_command, ['Project-Admin', 'KMS-Admin']),

        f'{INTEGRATION_COMMAND_NAME}asymmetric-encrypt': (asymmetric_encrypt_command, ['Encrypter',
                                                                                       'Encrypter/Decrypter',
                                                                                       'Project-Admin']),

        f'{INTEGRATION_COMMAND_NAME}asymmetric-decrypt': (asymmetric_decrypt_command, ['Decrypter',
                                                                                       'Encrypter/Decrypter',
                                                                                       'Project-Admin'])
    }

    command = demisto.command()
    LOG(f'{INTEGRATION_NAME}: command is {command}')
    try:
        client = Client(demisto.params())

        if command == 'test-module':
            test_function(client)
            demisto.results('ok')

        if command not in COMMANDS:
            raise NotImplementedError(f'Command "{command}" is not implemented.')

        cmd_func = COMMANDS.get(command)[0]  # type: ignore
        cmd_role = list(COMMANDS.get(command)[1])  # type: ignore

        if client.role not in cmd_role:
            raise PermissionError(f"Your Service Account Role does not permit the use of {command} command.")

        results = cmd_func(client, demisto.args())  # type: ignore
        return_outputs(*results)

    except Exception as e:
        return_error(f'{INTEGRATION_NAME}: {str(e)}', e)


if __name__ in ['__main__', 'builtin', 'builtins']:
    main()
