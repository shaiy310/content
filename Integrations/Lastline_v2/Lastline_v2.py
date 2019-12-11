import hashlib
from typing import Dict
from urllib3 import disable_warnings
import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *


INTEGRATION_COMMAND_NAME = "lastline"
INTEGRATION_NAME = "Lastline v2"
disable_warnings()


class Client(BaseClient):
    MD5_LEN = 32
    SHA1_LEN = 40
    SHA256_LEN = 64
    DEFAULT_THRESHOLD = 70

    def __init__(self, base_url: str, api_params: Dict, verify=True, proxy=False):
        self.command_params = api_params
        super(Client, self).__init__(base_url, verify, proxy)

    def file(self):
        hash_type = hash_type_checker(self.command_params.get('file'))
        self.command_params[hash_type] = self.command_params.get('file')
        result = self.http_request('/analysis/submit/file')
        human_readable, context_entry = report_generator(result)
        return human_readable, context_entry, result

    def check_status(self):
        result = self.http_request('/analysis/get')
        human_readable, context_entry = report_generator(result)
        return human_readable, context_entry, result

    def get_report(self):
        result = self.http_request('/analysis/get')
        if 'data' in result and 'score' not in result['data']:
            uuid = self.command_params.get('uuid')
            raise DemistoException(f'task {uuid} is not ready')
        human_readable, context_entry = report_generator(result)
        return human_readable, context_entry, result

    def get_task_list(self):
        for param in ('before', 'after'):
            if param in self.command_params:
                self.command_params[param] = self.command_params[param].replace('T', ' ')
        result = self.http_request('/analysis/get_completed')
        if 'data' in result:
            context_entry = self.get_status_and_time(result['data'].get('tasks'))
            human_readable = '|UUID|Time|Status|\n|--|--|--|'
            for uuid, task_time, status in context_entry:
                human_readable += f'\n|{uuid}|{task_time}|{status}|'
            return human_readable, {}, result

    def upload_file(self):
        entry_id = self.command_params.get('EntryID')
        self.command_params['push_to_portal'] = True
        file_params = demisto.getFilePath(entry_id)
        self.command_params['md5'] = file_hash(file_params.get('path'))
        result = self.http_request('/analysis/submit/file',
                                   headers={'Content-Type': 'multipart/form-data'},
                                   files={'file': file_params.get('path')})
        human_readable, context_entry = report_generator(result)
        return human_readable, context_entry, result

    def upload_url(self):
        result = self.http_request('/analysis/submit/url')
        human_readable, context_entry = report_generator(result)
        return human_readable, context_entry, result

    def test_module_command(self):
        self.command_params['url'] = 'https://www.google.com'
        self.upload_url()
        return 'ok'

    def get_status_and_time(self, uuids):
        task_list = []
        for uuid in uuids:
            self.command_params['uuid'] = uuid
            result = self.http_request('/analysis/get')
            if 'data' in result:
                task_time = result['data'].get('submission')
                if 'score' in result['data']:
                    status = 'Completed'
                else:
                    status = 'Analyzing'
            else:
                task_time = status = ''
            task_list.append([uuid, task_time.replace(' ', 'T'), status])
        return task_list

    def http_request(self, path: str, headers=None, files=None) -> Dict:
        result: Dict = self._http_request('POST', path, params=self.command_params, headers=headers, files=files)
        lastline_exception_handler(result)
        return result


def lastline_exception_handler(result: Dict):
    if result.get("success") is not None:
        if result.get("success") == 0:
            error_msg = "error "
            if 'error_code' in result:
                error_msg += "(" + str(result['error_code']) + ") "
            if 'error' in result:
                error_msg += result['error']
            raise DemistoException(error_msg)
    else:
        raise DemistoException('No response')


def hash_type_checker(hash_file: str) -> str:
    if len(hash_file) == Client.MD5_LEN:
        return 'md5'
    if len(hash_file) == Client.SHA1_LEN:
        return 'sha1'
    if len(hash_file) == Client.SHA256_LEN:
        return 'sha256'
    raise DemistoException(f'{INTEGRATION_NAME} File command support md5/ sha1/ sha256 only.')


def report_generator(result: Dict, threshold=None):
    context_entry: Dict = get_report_context(result, threshold)
    if 'File' in context_entry:
        key = 'File'
    elif 'URL' in context_entry:
        key = 'URL'
    else:
        key = ''
    score = result['data'].get('score')
    uuid = result['data'].get('task_uuid')
    submission_time = result['data'].get('submission')
    indicator = context_entry['DBotScore'].get('Indicator')
    if score is not None:
        meta_data = f'**Score: {score}**\n\nTask UUID: {uuid}\nSubmission Time: {submission_time}'
    else:
        meta_data = '**Status: Analyzing**'
    human_readable = tableToMarkdown(name=f'Lastline analysis for {key.lower()}: {indicator}',
                                     metadata=meta_data,
                                     t=context_entry.get(key))
    return human_readable, context_entry


def get_report_context(result: Dict, threshold=None) -> Dict:
    key = 'File'
    context_entry: Dict = {}
    if 'data' in result:
        data: Dict = {}
        dbotscore: Dict = {
            'Vendor': 'Lastline',
            'Score': 0
        }
        if 'score' in result['data']:
            status = 'Completed'
            if threshold is None:
                threshold = Client.DEFAULT_THRESHOLD
            score = result['data']['score']
            if score > threshold:
                dbotscore['Score'] = 3
                data['Malicious'] = {
                    'Vendor': 'Lastline',
                    'Score': score
                }
            elif score > 30:
                dbotscore['Score'] = 2
            else:
                dbotscore['Score'] = 1
        else:
            status = 'Analyzing'
        lastline: Dict = {
            'Submission': {'Status': status},
            'UUID': result['data'].get('task_uuid'),
            'SubmissionTime': result['data'].get('submission')
        }
        if 'analysis_subject' in result['data']:
            analysis_subject: Dict = result['data']['analysis_subject']
            temp_dict: Dict = {
                'YaraSignatures': analysis_subject.get('yara_signatures'),
                'DNSqueries': analysis_subject.get('dns_queries'),
                'NetworkConnections': analysis_subject.get('network_connections'),
                'DownloadedFiles': analysis_subject.get('downloaded_files'),
                'Process': analysis_subject.get('process'),
                'DomainDetections': analysis_subject.get('domain_detections'),
                'IPdetections': analysis_subject.get('ip_detections'),
                'URLdetections': analysis_subject.get('url_detections')
            }
            temp_dict = {keys: values for keys, values in temp_dict.items() if values}
            lastline['Submission'].update(temp_dict)

            if 'url' in analysis_subject:
                key = 'URL'
                dbotscore['Indicator'] = analysis_subject['url']
                data['Data'] = analysis_subject.get('url')
            else:
                dbotscore['Indicator'] = analysis_subject.get('md5')
                dbotscore['Type'] = 'hash'
                data['MD5'] = analysis_subject.get('md5')
                data['SHA1'] = analysis_subject.get('sha1')
                data['SHA256'] = analysis_subject.get('sha256')
                data['Type'] = analysis_subject.get('mime_type')
            dbotscore['Type'] = key
            context_entry['Lastline'] = lastline
            context_entry[key] = data
        if dbotscore['Score'] != 0:
            context_entry['DBotScore'] = dbotscore
    return context_entry


def file_hash(path: str) -> str:
    block_size = 65536
    file_hasher = hashlib.md5()
    with open(path, 'rb') as file_obj:
        buf = file_obj.read(block_size)
        while len(buf) > 0:
            file_hasher.update(buf)
            buf = file_obj.read(block_size)
    return file_hasher.hexdigest()


def main():
    params = demisto.params()
    base_url = params.get('url')
    verify_ssl = not params.get('insecure', False)
    proxy = params.get('proxy')
    api_params = {
        'key': params.get('api_key'),
        'api_token': params.get('api_token')
    }
    api_params.update(demisto.args())
    client = Client(base_url, api_params, verify=verify_ssl, proxy=proxy)
    command = demisto.command()
    demisto.debug(f'Command being called is {command}')

    # Switch case
    commands = {
        'test-module': Client.test_module_command,
        'file': Client.file,
        f'{INTEGRATION_COMMAND_NAME}-check-status': Client.check_status,
        f'{INTEGRATION_COMMAND_NAME}-get-report': Client.get_report,
        f'{INTEGRATION_COMMAND_NAME}-get-task-list': Client.get_task_list,
        f'{INTEGRATION_COMMAND_NAME}-upload-file': Client.upload_file,
        f'{INTEGRATION_COMMAND_NAME}-upload-url': Client.upload_url
    }
    try:
        demisto.info(command)
        if command in commands:
            readable_output, outputs, raw_response = commands[command](client)
            return_outputs(readable_output, outputs, raw_response)
        else:
            raise DemistoException(f'{demisto.command()} is not a command')
    # Log exceptions
    except Exception as every_error:
        err_msg = f'Error in {INTEGRATION_NAME} Integration [{every_error}]'
        return_error(err_msg, error=every_error)


if __name__ in ("__builtin__", "builtins"):
    main()
