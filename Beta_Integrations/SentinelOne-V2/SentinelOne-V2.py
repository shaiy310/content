import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

''' IMPORTS '''

import json
import requests
from distutils.util import strtobool

# Disable insecure warnings
requests.packages.urllib3.disable_warnings()

''' GLOBALS/PARAMS '''

USERNAME = demisto.params().get('credentials').get('identifier')
PASSWORD = demisto.params().get('credentials').get('password')
TOKEN = demisto.params().get('token')
SERVER = demisto.params()['url'][:-1] if (demisto.params()['url'] and demisto.params()['url'].endswith('/')) \
    else demisto.params()['url']
USE_SSL = not demisto.params().get('unsecure', False)
FETCH_TIME = demisto.params().get('fetch_time', '3 days')
FETCH_THREAT_RANK = int(demisto.params().get('fetch_threat_rank', 5))
BASE_URL = SERVER + '/web/api/v2.0/'
HEADERS = {
    'Authorization': 'ApiToken ' + TOKEN,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# remove proxy if not set to true in params
if not demisto.params().get('proxy'):
    del os.environ['HTTP_PROXY']
    del os.environ['HTTPS_PROXY']
    del os.environ['http_proxy']
    del os.environ['https_proxy']

''' HELPER FUNCTIONS '''


def http_request(method, url_suffix, params={}, data=None):
    res = requests.request(
        method,
        BASE_URL + url_suffix,
        verify=USE_SSL,
        params=params,
        data=data,
        headers=HEADERS
    )

    if res.status_code not in {200}:
        try:
            errors = ''
            for error in res.json().get('errors'):
                errors = '\n' + errors + error.get('detail')
            return_error('Error in API call to Sentinel One [%d] - %s \nError details: %s' % (
            res.status_code, res.reason, errors))
        except Exception as e:
            return_error('Error in API call to Sentinel One [%d] - %s' % (res.status_code, res.reason))

    return res.json()


''' COMMANDS + REQUESTS FUNCTIONS '''


def test_module():
    """
    Performs basic get request to get activities types.
    """
    http_request('GET', 'activities/types')
    return True


def get_activities_request(created_after=None, user_emails=None, group_ids=None, created_until=None,
                           activities_ids=None, include_hidden=None, created_before=None, threats_ids=None,
                           activity_types=None, user_ids=None, created_from=None, created_between=None, agent_ids=None,
                           limit=None):

    endpoint_url = 'activities'

    params = {
        'created_at__gt': created_after,
        'userEmails': user_emails,
        'groupIds': group_ids,
        'created_at__lte': created_until,
        'ids': activities_ids,
        'includeHidden': include_hidden,
        'created_at__lt': created_before,
        'threatIds': threats_ids,
        'activityTypes': activity_types,
        'userIds': user_ids,
        'created_at__gte': created_from,
        'createdAt_between': created_between,
        'agentsIds': agent_ids,
        'limit': limit
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def get_activities_command():
    """
    Get a list of activities.
    """
    context = {}
    contents = []
    headers = ['ID', 'Primary description', 'Data', 'User ID', 'Created at', 'Updated at', 'Threat ID']

    created_after = demisto.args().get('created_after')
    user_emails = demisto.args().get('user_emails')
    group_ids = argToList(demisto.args().get('group_ids', []))
    created_until = demisto.args().get('created_until')
    activities_ids = argToList(demisto.args().get('activities_ids', []))
    include_hidden = demisto.args().get('include_hidden')
    created_before = demisto.args().get('created_before')
    threats_ids = argToList(demisto.args().get('threats_ids', []))
    activity_types = argToList(demisto.args().get('activity_types', []))
    user_ids = argToList(demisto.args().get('user_ids', []))
    created_from = demisto.args().get('created_from')
    created_between = demisto.args().get('created_between')
    agent_ids = argToList(demisto.args().get('agent_ids', []))
    limit = int(demisto.args().get('limit', 50))

    activities = get_activities_request(created_after, user_emails, group_ids, created_until, activities_ids,
                                        include_hidden, created_before, threats_ids,
                                        activity_types, user_ids, created_from, created_between, agent_ids, limit)
    if activities:
        for activity in activities:
            contents.append({
                'ID': activity.get('id'),
                'Created at': activity.get('createdAt'),
                'Primary description': activity.get('primaryDescription'),
                'User ID': activity.get('userId'),
                'Data': activity.get('data'),
                'Threat ID': activity.get('threatId'),
                'Updated at': activity.get('updatedAt')
            })

        context['SentinelOne.Activity(val.ID && val.ID === obj.ID)'] = activities

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown('Sentinel One Activities', contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_groups_request(group_type=None, group_ids=None, group_id=None, is_default=None, name=None, query=None,
                       rank=None, limit=None):

    endpoint_url = 'groups'

    params = {
        'type': group_type,
        'groupIds': group_ids,
        'id': group_id,
        'isDefault': is_default,
        'name': name,
        'query': query,
        'rank': rank,
        'limit': limit
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def get_groups_command():
    """
    Gets the group data.
    """

    context = {}
    contents = []
    headers = ['ID', 'Name', 'Type', 'Creator', 'Creator ID', 'Created at', 'Rank']

    group_type = demisto.args().get('type')
    group_id = demisto.args().get('id')
    group_ids = argToList(demisto.args().get('groupIds', []))
    is_default = demisto.args().get('isDefault')
    name = demisto.args().get('name')
    query = demisto.args().get('query')
    rank = demisto.args().get('rank')
    limit = int(demisto.args().get('limit', 50))

    groups = get_groups_request(group_type, group_id, group_ids, is_default, name, query, rank, limit)
    if groups:
        for group in groups:
            contents.append({
                'ID': group.get('id'),
                'Type': group.get('type'),
                'Name': group.get('name'),
                'Creator ID': group.get('creatorId'),
                'Creator': group.get('creator'),
                'Created at': group.get('createdAt'),
                'Rank': group.get('rank')
            })

        context['SentinelOne.Group(val.ID && val.ID === obj.ID)'] = groups

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown('Sentinel One Groups', contents, headers, removeNull=True),
        'EntryContext': context
    })


def delete_group_request(group_id=None):

    endpoint_url = 'groups/' + group_id

    response = http_request('DELETE', endpoint_url)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def delete_group():
    """
    Deletes a group by ID.
    """
    group_id = demisto.args().get('group_id')

    delete_group_request(group_id)
    demisto.results('The group was deleted successfully')


def move_agent_request(group_id, agents_id):

    endpoint_url = 'groups/' + group_id + '/move-agents'

    payload = {
        "filter": {
            "agentIds": agents_id
        }
    }

    response = http_request('PUT', endpoint_url, data=json.dumps(payload))
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def move_agent_to_group_command():
    """
    Move agents to a new group.
    """
    group_id = demisto.args().get('group_id')
    agents_id = argToList(demisto.args().get('agents_ids'))
    context = {}

    agents_groups = move_agent_request(group_id, agents_id)

    # Parse response into context & content entries
    if agents_groups.get('agentsMoved') and int(agents_groups.get('agentsMoved')) > 0:
        agents_moved = True
    else:
        agents_moved = False
    date_time_utc = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    context_entries = contents = {
        'Date': date_time_utc,
        'AgentsMoved': agents_groups.get('agentsMoved'),
        'AffectedAgents': agents_moved
    }

    context['SentinelOne.Agents(val.Date && val.Date === obj.Date)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown('Sentinel One - Shutdown Agents \n' + 'Total of: ' + str(
            agents_groups.get('AgentsMoved')) + ' agents were Shutdown successfully', contents, removeNull=True),
        'EntryContext': context
    })


def get_agent_processes_request(agents_ids=None):

    endpoint_url = 'agents/processes'

    params = {
        'ids': agents_ids
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def get_agent_processes():
    """
    Retrieve running processes for a specific agent.
    Note: This feature is obsolete and an empty array will always be returned
    """
    headers = ['ProcessName', 'StartTime', 'Pid', 'MemoryUsage', 'CpuUsage', 'ExecutablePath']
    contents = []
    context = {}
    agents_ids = demisto.args().get('agents_ids')

    processes = get_agent_processes_request(agents_ids)

    if processes:
        for process in processes:
            contents.append({
                'ProcessName': process.get('processName'),
                'CpuUsage': process.get('cpuUsage'),
                'MemoryUsage': process.get('memoryUsage'),
                'StartTime': process.get('startTime'),
                'ExecutablePath': process.get('executablePath'),
                'Pid': process.get('pid')
            })
        context['SentinelOne.Agents(val.Pid && val.Pid === obj.Pid)'] = processes

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown('Sentinel One Agent processes', contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_threats_command():
    """
    Gets a list of threats.
    """
    # Init main vars
    contents = []
    context = {}
    context_entries = []
    title = ''

    # Get arguments
    content_hash = demisto.args().get('content_hash')
    mitigation_status = argToList(demisto.args().get('mitigation_status'))
    created_before = demisto.args().get('created_before')
    created_after = demisto.args().get('created_after')
    created_until = demisto.args().get('created_until')
    created_from = demisto.args().get('created_from')
    resolved = bool(strtobool(demisto.args().get('resolved', 'false')))
    display_name = demisto.args().get('display_name_like')
    query = demisto.args().get('query', '')
    threat_ids = argToList(demisto.args().get('threat_ids', []))
    limit = int(demisto.args().get('limit', 20))
    classifications = argToList(demisto.args().get('classifications', []))
    rank = int(demisto.args().get('rank', 0))

    # Make request and get raw response
    threats = get_threats_request(content_hash, mitigation_status, created_before, created_after, created_until,
                                  created_from, resolved, display_name, query, threat_ids, limit, classifications)

    # Parse response into context & content entries
    if threats:
        title = 'Sentinel One - Getting Threat List \n' + \
                'Provides summary information and details for all the threats that matched your search criteria.'
        for threat in threats:
            if not rank or (rank and threat.get('rank') >= rank):
                contents.append({
                    'ID': threat.get('id'),
                    'Agent Computer Name': threat.get('agentComputerName'),
                    'Created Date': threat.get('createdDate'),
                    'Site ID': threat.get('siteId'),
                    'Classification': threat.get('classification'),
                    'Mitigation Status': threat.get('mitigationStatus'),
                    'Agent ID': threat.get('agentId'),
                    'Site Name': threat.get('siteName'),
                    'Rank': threat.get('rank'),
                    'Marked As Benign': threat.get('markedAsBenign'),
                    'File Content Hash': threat.get('fileContentHash')
                })
                context_entries.append({
                    'ID': threat.get('id'),
                    'AgentComputerName': threat.get('agentComputerName'),
                    'CreatedDate': threat.get('createdDate'),
                    'SiteID': threat.get('siteId'),
                    'Classification': threat.get('classification'),
                    'MitigationStatus': threat.get('mitigationStatus'),
                    'AgentID': threat.get('agentId'),
                    'Rank': threat.get('rank'),
                    'MarkedAsBenign': threat.get('markedAsBenign'),
                    'FileContentHash': threat.get('fileContentHash'),
                    'InQuarantine': threat.get('inQuarantine'),
                    'FileMaliciousContent': threat.get('fileMaliciousContent'),
                    'ThreatName': threat.get('threatName'),
                    'FileSha256': threat.get('fileSha256'),
                    'AgentOsType': threat.get('agentOsType'),
                    'Description': threat.get('description'),
                    'FileDisplayName': threat.get('fileDisplayName'),
                    'FilePath': threat.get('filePath'),
                    'Username': threat.get('username')



                })

        context['SentinelOne.Threats(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, removeNull=True),
        'EntryContext': context
    })


def get_threats_request(content_hash=None, mitigation_status=None, created_before=None, created_after=None,
                        created_until=None, created_from=None, resolved=None, display_name=None, query=None,
                        threat_ids=None, limit=None, classifications=None):

    endpoint_url = 'threats'

    params = {
        'contentHash': content_hash,
        'mitigationStatus': mitigation_status,
        'created_at__lt': created_before,
        'created_at__gt': created_after,
        'created_at__lte': created_until,
        'created_at__gte': created_from,
        'resolved': resolved,
        'displayName__like': display_name,
        'query': query,
        'ids': threat_ids,
        'limit': limit,
        'classifications': classifications,
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def get_hash_command():
    """
    Get hash reputation and classification.
    """
    # Init main vars
    contents = []
    context = {}
    headers = ['Hash', 'Rank', 'Classification Source', 'Classification']

    # Get arguments
    hash_ = demisto.args().get('hash')

    # Make request and get raw response
    hash_reputation = get_hash_reputation_request(hash_)
    hash_classification = get_hash_classification_request(hash_)

    # Parse response into context & content entries
    title = 'Sentinel One - Hash Reputation and Classification \n' + \
            'Provides hash reputation (rank from 0 to 10):'
    contents = context_entries = {
        'Rank': hash_reputation.get('rank'),
        'Hash': hash_,
        'Classification Source': hash_classification.get('classificationSource'),
        'Classification': hash_classification.get('classification')
    }

    context['SentinelOne.Hash(val.Hash && val.Hash === obj.Hash)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_hash_reputation_request(hash_):
    endpoint_url = 'hashes/' + hash_ + '/reputation'

    response = http_request('GET', endpoint_url)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def get_hash_classification_request(hash_):

    endpoint_url = 'hashes/' + hash_ + '/classification'

    response = http_request('GET', endpoint_url)
    if response.get('errors'):
        return_error(response.get('errors'))
    if response.get('data'):
        if response.get('data').get('classification'):
            return response.get('data')
        else:
            return {}
    return {}


def mark_as_threat_command():
    """
    Mark suspicious threats as threats
    """
    # Init main vars
    headers = ['ID', 'Marked As Threat']
    contents = []
    context = {}
    context_entries = []

    # Get arguments
    threat_ids = argToList(demisto.args().get('threat_ids'))
    target_scope = demisto.args().get('target_scope')

    # Make request and get raw response
    affected_threats = mark_as_threat_request(threat_ids, target_scope)

    # Parse response into context & content entries
    if affected_threats.get('affected') and int(affected_threats.get('affected')) > 0:
        title = 'Total of ' + str(affected_threats.get('affected')) + ' provided threats were marked successfully'
        affected = True
    else:
        affected = False
        title = 'No threats were marked'
    for threat_id in threat_ids:
        contents.append({
            'Marked As Threat': affected,
            'ID': threat_id,
        })
        context_entries.append({
            'MarkedAsThreat': affected,
            'ID': threat_id,
        })

    context['SentinelOne.Threats(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown('Sentinel One - Marking suspicious threats as threats \n' + title, contents,
                                         headers, removeNull=True),
        'EntryContext': context
    })


def mark_as_threat_request(threat_ids, target_scope):
    endpoint_url = 'threats/mark-as-threat'

    payload = {
        "filter": {
            "ids": threat_ids
        },
        "data": {
            "targetScope": target_scope
        }
    }

    response = http_request('POST', endpoint_url, data=json.dumps(payload))
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def mitigate_threat_command():
    """
    Apply a mitigation action to a group of threats
    """
    # Init main vars
    headers = ['ID', 'Mitigation Action', 'Mitigated']
    contents = []
    context = {}
    context_entries = []

    # Get arguments
    threat_ids = argToList(demisto.args().get('threat_ids'))
    action = demisto.args().get('action')

    # Make request and get raw response
    mitigated_threats = mitigate_threat_request(threat_ids, action)

    # Parse response into context & content entries
    if mitigated_threats.get('affected') and int(mitigated_threats.get('affected')) > 0:
        mitigated = True
        title = 'Total of ' + str(mitigated_threats.get('affected')) + ' provided threats were mitigated successfully'
    else:
        mitigated = False
        title = 'No threats were mitigated'
    for threat_id in threat_ids:
        contents.append({
            'Mitigated': mitigated,
            'ID': threat_id,
            'Mitigation Action': action
        })
        context_entries.append({
            'Mitigated': mitigated,
            'ID': threat_id,
            'Mitigation': {
                'Action': action
            }
        })

    context['SentinelOne.Threats(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown('Sentinel One - Mitigating threats \n' + title, contents, headers,
                                         removeNull=True),
        'EntryContext': context
    })


def mitigate_threat_request(threat_ids, action):
    endpoint_url = 'threats/mitigate/' + action

    payload = {
        "filter": {
            "ids": threat_ids
        }
    }

    response = http_request('POST', endpoint_url, data=json.dumps(payload))
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def resolve_threat_command():
    """
    Mark threats as resolved
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    context_entries = []

    # Get arguments
    threat_ids = argToList(demisto.args().get('threat_ids'))

    # Make request and get raw response
    resolved_threats = resolve_threat_request(threat_ids)

    # Parse response into context & content entries
    if resolved_threats.get('affected') and int(resolved_threats.get('affected')) > 0:
        resolved = True
        title = 'Total of ' + str(resolved_threats.get('affected')) + ' provided threats were resolved successfully'
    else:
        resolved = False
        title = 'No threats were resolved'

    for threat_id in threat_ids:
        contents.append({
            'Resolved': resolved,
            'ID': threat_id
        })
        context_entries.append({
            'Resolved': resolved,
            'ID': threat_id
        })

    context['SentinelOne.Threats(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown('Sentinel One - Resolving threats \n' + title, contents, headers,
                                         removeNull=True),
        'EntryContext': context
    })


def resolve_threat_request(threat_ids):
    endpoint_url = 'threats/mark-as-resolved'

    payload = {
        "filter": {
            "ids": threat_ids
        }
    }

    response = http_request('POST', endpoint_url, data=json.dumps(payload))
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def get_exclusion_list_command():
    """
    List all white items matching the input filter
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    context_entries = []
    title = ''

    # Get arguments
    item_ids = argToList(demisto.args().get('item_ids', []))
    os_types = argToList(demisto.args().get('os_types', []))
    exclusion_type = demisto.args().get('exclusion_type')
    limit = int(demisto.args().get('limit', 10))

    # Make request and get raw response
    exclusion_items = get_exclusion_list_request(item_ids, os_types, exclusion_type, limit)

    # Parse response into context & content entries
    if exclusion_items:
        title = 'Sentinel One - Listing exclusion items \n' + \
                'provides summary information and details for ' \
                'all the exclusion items that matched your search criteria.'
        for exclusion_item in exclusion_items:
            contents.append({
                'ID': exclusion_item.get('id'),
                'Type': exclusion_item.get('type'),
                'CreatedAt': exclusion_item.get('createdAt'),
                'Value': exclusion_item.get('value'),
                'Source': exclusion_item.get('source'),
                'UserID': exclusion_item.get('userId'),
                'UpdatedAt': exclusion_item.get('updatedAt'),
                'OsType': exclusion_item.get('osType'),
                'UserName': exclusion_item.get('userName'),
                'Mode': exclusion_item.get('mode')
            })
            context_entries.append({
                'ID': exclusion_item.get('id'),
                'Type': exclusion_item.get('type'),
                'CreatedAt': exclusion_item.get('createdAt'),
                'Value': exclusion_item.get('value'),
                'Source': exclusion_item.get('source'),
                'UserID': exclusion_item.get('userId'),
                'UpdatedAt': exclusion_item.get('updatedAt'),
                'OsType': exclusion_item.get('osType'),
                'UserName': exclusion_item.get('userName'),
                'Mode': exclusion_item.get('mode')
            })

        context['SentinelOne.Exclusions(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_exclusion_list_request(item_ids, os_types, exclusion_type, limit):

    endpoint_url = 'exclusions'

    params = {
        "ids": item_ids,
        "osTypes": os_types,
        "type": exclusion_type,
        "limit": limit
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def create_exclusion_item_command():
    """
    Create white item.
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    context_entries = []
    title = ''

    # Get arguments
    group_ids = argToList(demisto.args().get('group_ids', []))
    site_ids = argToList(demisto.args().get('site_ids', []))
    exclusion_type = demisto.args().get('exclusion_type')
    exclusion_value = demisto.args().get('exclusion_value')
    os_type = demisto.args().get('os_type')
    description = demisto.args().get('description')
    exclusion_mode = demisto.args().get('exclusion_mode')
    path_exclusion_type = demisto.args().get('path_exclusion_type')

    # Make request and get raw response
    new_item = create_exclusion_item_request(exclusion_type, exclusion_value, os_type, description, exclusion_mode,
                                             path_exclusion_type, group_ids, site_ids)

    # Parse response into context & content entries
    if new_item:
        title = 'Sentinel One - Adding an exclusion item \n' + \
                'The provided item was successfully added to the exclusion list'
        contents.append({
            'ID': new_item.get('id'),
            'Type': new_item.get('type'),
            'Created At': new_item.get('createdAt')
        })
        context_entries.append({
            'ID': new_item.get('id'),
            'Type': new_item.get('type'),
            'CreatedAt': new_item.get('createdAt')
        })

        context['SentinelOne.Exclusions(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def create_exclusion_item_request(exclusion_type, exclusion_value, os_type, description, exclusion_mode,
                                  path_exclusion_type, group_ids, site_ids):
    endpoint_url = 'exclusions'

    payload = {
        "filter": {
            "groupIds": group_ids,
            "siteIds": site_ids
        },
        "data": {
            "type": exclusion_type,
            "value": exclusion_value,
            "osType": os_type,
            "description": description,
            "mode": exclusion_mode
        }
    }

    if path_exclusion_type:
        payload['data']['pathExclusionType'] = path_exclusion_type

    response = http_request('POST', endpoint_url, data=json.dumps(payload))
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')[0]
    return {}


def get_static_indicators_command():
    """
    Get an export of all threat static indicators
    """
    # Init main vars
    headers = ['Category ID', 'ID', 'Category Name', 'Description']
    contents = []
    context = {}
    context_entries = []
    title = ''

    # Get arguments
    limit = int(demisto.args().get('limit', 50))

    # Make request and get raw response
    static_indicators = get_static_indicators_request()
    if limit:
        static_indicators = static_indicators[:limit]

    # Parse response into context & content entries
    if static_indicators:
        title = 'Sentinel One - Getting Static Indicators \n' + \
                'Provides summary information and details for all threat static indicators.'
        for static_indicator in static_indicators:
            contents.append({
                'ID': static_indicator.get('id'),
                'Description': static_indicator.get('description'),
                'Category Name': static_indicator.get('categoryName'),
                'Category ID': static_indicator.get('categoryId')
            })
            context_entries.append({
                'ID': static_indicator.get('id'),
                'Description': static_indicator.get('description'),
                'CategoryName': static_indicator.get('categoryName'),
                'CategoryID': static_indicator.get('categoryId')
            })

        context['SentinelOne.Indicators(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_static_indicators_request():
    endpoint_url = 'threats/static-indicators'

    response = http_request('GET', endpoint_url)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        if 'indicators' in response.get('data'):
            return response.get('data').get('indicators')
    return {}


def get_sites_command():
    """
    List all sites with filtering options
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    context_entries = []
    title = ''

    # Get arguments
    updated_at = demisto.args().get('updated_at')
    query = demisto.args().get('query')
    site_type = demisto.args().get('site_type')
    features = demisto.args().get('features')
    state = demisto.args().get('state')
    suite = demisto.args().get('suite')
    admin_only = bool(strtobool(demisto.args().get('admin_only', 'false')))
    account_id = demisto.args().get('account_id')
    site_name = demisto.args().get('site_name')
    created_at = demisto.args().get('created_at')
    limit = int(demisto.args().get('limit', 50))
    site_ids = argToList(demisto.args().get('site_ids', []))

    # Make request and get raw response
    sites, all_sites = get_sites_request(updated_at, query, site_type, features, state, suite, admin_only, account_id,
                                         site_name, created_at, limit, site_ids)

    # Parse response into context & content entries
    if sites:
        title = 'Sentinel One - Gettin List of Sites \n' + \
                'Provides summary information and details for all sites that matched your search criteria.'
        for site in sites:
            contents.append({
                'ID': site.get('id'),
                'Creator': site.get('creator'),
                'Name': site.get('name'),
                'Type': site.get('siteType'),
                'Account Name': site.get('accountName'),
                'State': site.get('state'),
                'Health Status': site.get('healthStatus'),
                'Suite': site.get('suite'),
                'Created At': site.get('createdAt'),
                'Expiration': site.get('expiration'),
                'Unlimited Licenses': site.get('unlimitedLicenses'),
                'Total Licenses': all_sites.get('totalLicenses'),
                'Active Licenses': all_sites.get('activeLicenses')
            })
            context_entries.append({
                'ID': site.get('id'),
                'Creator': site.get('creator'),
                'Name': site.get('name'),
                'Type': site.get('siteType'),
                'AccountName': site.get('accountName'),
                'State': site.get('state'),
                'HealthStatus': site.get('healthStatus'),
                'Suite': site.get('suite'),
                'CreatedAt': site.get('createdAt'),
                'Expiration': site.get('expiration'),
                'UnlimitedLicenses': site.get('unlimitedLicenses'),
                'TotalLicenses': all_sites.get('totalLicenses'),
                'ActiveLicenses': all_sites.get('activeLicenses')
            })

        context['SentinelOne.Sites(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_sites_request(updated_at, query, site_type, features, state, suite, admin_only, account_id, site_name,
                      created_at, limit, site_ids):

    endpoint_url = 'sites'

    params = {
        "updatedAt": updated_at,
        "query": query,
        "siteType": site_type,
        "features": features,
        "state": state,
        "suite": suite,
        "adminOnly": admin_only,
        "accountId": account_id,
        "name": site_name,
        "createdAt": created_at,
        "limit": limit,
        "siteIds": site_ids
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data').get('sites'), response.get('data').get('allSites')
    return {}


def get_site_command():
    """
    Get a specific site by ID
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    context_entries = []
    title = ''

    # Get arguments
    site_id = demisto.args().get('site_id')

    # Make request and get raw response
    site = get_site_request(site_id)

    # Parse response into context & content entries
    if site:
        title = 'Sentinel One - Summary About Site: ' + site_id + '\n' + \
                'Provides summary information and details for specific site ID'
        contents.append({
            'ID': site.get('id'),
            'Creator': site.get('creator'),
            'Name': site.get('name'),
            'Type': site.get('siteType'),
            'Account Name': site.get('accountName'),
            'State': site.get('state'),
            'Health Status': site.get('healthStatus'),
            'Suite': site.get('suite'),
            'Created At': site.get('createdAt'),
            'Expiration': site.get('expiration'),
            'Unlimited Licenses': site.get('unlimitedLicenses'),
            'Total Licenses': site.get('totalLicenses'),
            'Active Licenses': site.get('activeLicenses'),
            'AccountID': site.get('accountId'),
            'IsDefault': site.get('isDefault')
        })
        context_entries.append({
            'ID': site.get('id'),
            'Creator': site.get('creator'),
            'Name': site.get('name'),
            'Type': site.get('siteType'),
            'AccountName': site.get('accountName'),
            'State': site.get('state'),
            'HealthStatus': site.get('healthStatus'),
            'Suite': site.get('suite'),
            'CreatedAt': site.get('createdAt'),
            'Expiration': site.get('expiration'),
            'UnlimitedLicenses': site.get('unlimitedLicenses'),
            'TotalLicenses': site.get('totalLicenses'),
            'ActiveLicenses': site.get('activeLicenses'),
            'AccountID': site.get('accountId'),
            'IsDefault': site.get('isDefault')
        })

        context['SentinelOne.Sites(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_site_request(site_id):
    endpoint_url = 'sites/' + site_id

    response = http_request('GET', endpoint_url)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def expire_site_command():
    """
    Expire specific site by ID
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    title = ''

    # Get arguments
    site_id = demisto.args().get('site_id')

    # Make request and get raw response
    site = expire_site_request(site_id)

    # Parse response into context & content entries
    if site:
        title = 'Sentinel One - Expire Site: ' + site_id + '\n' + 'Site has been expired successfully'
        context_entries = contents = {
            'ID': site.get('id'),
            'Expired': True
        }

        context['SentinelOne.Sites(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def expire_site_request(site_id):
    endpoint_url = 'sites/' + site_id + '/expire-now'

    response = http_request('POST', endpoint_url)
    if response.get('errors'):
        return_error(response.get('errors'))
    if response.get('data'):
        return response.get('data')
    return {}


def reactivate_site_command():
    """
    Reactivate specific site by ID
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    title = ''

    # Get arguments
    site_id = demisto.args().get('site_id')

    # Make request and get raw response
    site = reactivate_site_request(site_id)

    # Parse response into context & content entries
    if site:
        title = 'Sentinel One - Reactivated Site: ' + site_id + '\n' + 'Site has been reactivated successfully'
        context_entries = contents = {
            'ID': site.get('id'),
            'Reactivated': site.get('success')
        }

        context['SentinelOne.Sites(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def reactivate_site_request(site_id):
    endpoint_url = 'sites/' + site_id + '/reactivate'

    payload = {
        "data": {}
    }

    response = http_request('PUT', endpoint_url, data=json.dumps(payload))
    if response.get('errors'):
        return_error(response.get('errors'))
    if response.get('data'):
        return response.get('data')
    return {}


def get_threat_summary_command():
    """
    Get dashboard threat summary
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    title = ''

    # Get arguments
    site_ids = argToList(demisto.args().get('site_ids', []))
    group_ids = argToList(demisto.args().get('group_ids', []))

    # Make request and get raw response
    threat_summary = get_threat_summary_request(site_ids, group_ids)

    # Parse response into context & content entries
    if threat_summary:
        title = 'Sentinel One - Dashboard Threat Summary'
        context_entries = contents = {
            'Active': threat_summary.get('active'),
            'Total': threat_summary.get('total'),
            'Mitigated': threat_summary.get('mitigated'),
            'Suspicious': threat_summary.get('suspicious'),
            'Blocked': threat_summary.get('blocked')
        }

        context['SentinelOne.ThreatSummary(val && val === obj)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_threat_summary_request(site_ids, group_ids):
    endpoint_url = 'private/threats/summary'

    params = {
        "siteIds": site_ids,
        "groupIds": group_ids
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def list_agents_command():
    """
    List all agents matching the input filter
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    context_entries = []
    title = ''

    # Get arguments
    active_threats = demisto.args().get('min_active_threats')
    computer_name = demisto.args().get('computer_name')
    scan_status = demisto.args().get('scan_status')
    os_type = demisto.args().get('os_type')
    created_at = demisto.args().get('created_at')

    # Make request and get raw response
    agents = list_agents_request(active_threats, computer_name, scan_status, os_type, created_at)

    # Parse response into context & content entries
    if agents:
        title = 'Sentinel One - List of Agents \n ' \
                'Provides summary information and details for all the agents that matched your search criteria'
        for agent in agents:
            contents.append({
                'ID': agent.get('id'),
                'Network Status': agent.get('networkStatus'),
                'Agent Version': agent.get('agentVersion'),
                'Is Decomissioned': agent.get('isDecommissioned'),
                'Is Active': agent.get('isActive'),
                'Last ActiveDate': agent.get('lastActiveDate'),
                'Registered At': agent.get('registeredAt'),
                'External IP': agent.get('externalIp'),
                'Threat Count': agent.get('activeThreats'),
                'Encrypted Applications': agent.get('encryptedApplications'),
                'OS Name': agent.get('osName'),
                'Computer Name': agent.get('computerName'),
                'Domain': agent.get('domain'),
                'Created At': agent.get('createdAt'),
                'Site Name': agent.get('siteName')
            })
            context_entries.append({
                'ID': agent.get('id'),
                'NetworkStatus': agent.get('networkStatus'),
                'AgentVersion': agent.get('agentVersion'),
                'IsDecomissioned': agent.get('isDecommissioned'),
                'IsActive': agent.get('isActive'),
                'LastActiveDate': agent.get('lastActiveDate'),
                'RegisteredAt': agent.get('registeredAt'),
                'ExternalIP': agent.get('externalIp'),
                'ThreatCount': agent.get('activeThreats'),
                'EncryptedApplications': agent.get('encryptedApplications'),
                'OSName': agent.get('osName'),
                'ComputerName': agent.get('computerName'),
                'Domain': agent.get('domain'),
                'CreatedAt': agent.get('createdAt'),
                'SiteName': agent.get('siteName')
            })

        context['SentinelOne.Agents(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def list_agents_request(active_threats, computer_name, scan_status, os_type, created_at):
    endpoint_url = 'agents'

    params = {
        "activeThreats__gt": active_threats,
        "computerName": computer_name,
        "scanStatus": scan_status,
        "osType": os_type,
        "createdAt__gte": created_at
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def get_agent_command():
    """
    Get single agent via ID
    """
    # Init main vars
    headers = []
    contents = []
    context = {}
    context_entries = []
    title = ''

    # Get arguments
    agent_id = demisto.args().get('agent_id')

    # Make request and get raw response
    agent = get_agent_request(agent_id)

    # Parse response into context & content entries
    if agent:
        title = 'Sentinel One - Get Agent Details \nProvides details for the following agent ID : ' + agent_id
        contents.append({
            'ID': agent.get('id'),
            'Network Status': agent.get('networkStatus'),
            'Agent Version': agent.get('agentVersion'),
            'Is Decomissioned': agent.get('isDecommissioned'),
            'Is Active': agent.get('isActive'),
            'Last ActiveDate': agent.get('lastActiveDate'),
            'Registered At': agent.get('registeredAt'),
            'External IP': agent.get('externalIp'),
            'Threat Count': agent.get('activeThreats'),
            'Encrypted Applications': agent.get('encryptedApplications'),
            'OS Name': agent.get('osName'),
            'Computer Name': agent.get('computerName'),
            'Domain': agent.get('domain'),
            'Created At': agent.get('createdAt'),
            'Site Name': agent.get('siteName')
        })
        context_entries.append({
            'ID': agent.get('id'),
            'NetworkStatus': agent.get('networkStatus'),
            'AgentVersion': agent.get('agentVersion'),
            'IsDecomissioned': agent.get('isDecommissioned'),
            'IsActive': agent.get('isActive'),
            'LastActiveDate': agent.get('lastActiveDate'),
            'RegisteredAt': agent.get('registeredAt'),
            'ExternalIP': agent.get('externalIp'),
            'ThreatCount': agent.get('activeThreats'),
            'EncryptedApplications': agent.get('encryptedApplications'),
            'OSName': agent.get('osName'),
            'ComputerName': agent.get('computerName'),
            'Domain': agent.get('domain'),
            'CreatedAt': agent.get('createdAt'),
            'SiteName': agent.get('siteName')
        })

        context['SentinelOne.Agents(val.ID && val.ID === obj.ID)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown(title, contents, headers, removeNull=True),
        'EntryContext': context
    })


def get_agent_request(agent_id):
    endpoint_url = 'agents'

    params = {
        "ids": [agent_id]
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')[0]
    return {}


def create_query_request(query, from_date, to_date):

    endpoint_url = 'dv/init-query'

    payload = {
        "query": query,
        "fromDate": from_date,
        "toDate": to_date
    }

    response = http_request('POST', endpoint_url, data=payload)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def create_query():

    query = demisto.args().get('query')
    from_date = demisto.args().get('from_date')
    to_date = demisto.args().get('to_date')

    query_id = create_query_request(query, from_date, to_date)

    demisto.results('The query ID is ' + query_id)


def get_events_request(query_id=None, limit=None):

    endpoint_url = 'events'

    params = {
        'query_id': query_id,
        'limit': limit
    }

    response = http_request('GET', endpoint_url, params)
    if response.get('errors'):
        return_error(response.get('errors'))
    if 'data' in response:
        return response.get('data')
    return {}


def get_events():
    """
    Get all Deep Visibility events from query
    """
    contents = []
    context_entries = []
    context = {}

    query_id = demisto.args().get('query_id')
    limit = int(demisto.args().get('limit', 10))

    events = get_events_request(query_id, limit)
    if events:
        for event in events:
            contents.append({
                'Sha1': event.get('sha1'),
                'DstIp': event.get('dstIp'),
                'SrcIp': event.get('srcIp'),
                'FileFullName': event.get('fileFullName'),
                'ProcessName': event.get('processName')
            })

            context_entries.append({
                'Sha1': event.get('sha1'),
                'DstIp': event.get('dstIp'),
                'SrcIp': event.get('srcIp'),
                'FileFullName': event.get('fileFullName'),
                'ProcessName': event.get('processName')
            })

        context['SentinelOne.Event(val.sha1 && val.sha1 === obj.sha1)'] = context_entries

    demisto.results({
        'Type': entryTypes['note'],
        'ContentsFormat': formats['json'],
        'Contents': contents,
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': tableToMarkdown('SentinelOne Events', contents, removeNull=True),
        'EntryContext': context
    })


def fetch_incidents():
    last_run = demisto.getLastRun()
    last_fetch = last_run.get('time')

    # handle first time fetch
    if last_fetch is None:
        last_fetch, _ = parse_date_range(FETCH_TIME, to_timestamp=True)

    incidents = []
    threats = get_threats_request()
    for threat in threats:
        # If no fetch threat rank is provided, bring everything, else only fetch above the threshold
        if not FETCH_THREAT_RANK or (FETCH_THREAT_RANK and threat.get('rank') >= FETCH_THREAT_RANK):
            incident = threat_to_incident(threat)
            incident_date = date_to_timestamp(incident['occurred'], '%Y-%m-%dT%H:%M:%S.%fZ')
            # update last run
            if incident_date > last_fetch:
                last_fetch = incident_date
                incidents.append(incident)

    demisto.setLastRun({'time': last_fetch})
    demisto.incidents(incidents)


def threat_to_incident(threat):
    incident = {}
    incident['name'] = 'Sentinel One Threat: ' + threat.get('classification')
    incident['occurred'] = threat.get('createdDate')
    incident['rawJSON'] = json.dumps(threat)
    return incident


''' COMMANDS MANAGER / SWITCH PANEL '''

LOG('command is %s' % (demisto.command()))

try:
    if demisto.command() == 'test-module':
        # This is the call made when pressing the integration test button.
        test_module()
        demisto.results('ok')
    elif demisto.command() == 'fetch-incidents':
        fetch_incidents()
    elif demisto.command() == 'sentinelone-get-activities':
        get_activities_command()
    elif demisto.command() == 'sentinelone-get-threats':
        get_threats_command()
    elif demisto.command() == 'sentinelone-mark-as-threat':
        mark_as_threat_command()
    elif demisto.command() == 'sentinelone-mitigate-threat':
        mitigate_threat_command()
    elif demisto.command() == 'sentinelone-resolve-threat':
        resolve_threat_command()
    elif demisto.command() == 'sentinelone-get-static-indicators':
        get_static_indicators_command()
    elif demisto.command() == 'sentinelone-threat-summary':
        get_threat_summary_command()
    elif demisto.command() == 'sentinelone-get-hash':
        get_hash_command()
    elif demisto.command() == 'sentinelone-get-exclusion-list':
        get_exclusion_list_command()
    elif demisto.command() == 'sentinelone-create-exclusion-item':
        create_exclusion_item_command()
    elif demisto.command() == 'sentinelone-get-sites':
        get_sites_command()
    elif demisto.command() == 'sentinelone-get-site':
        get_site_command()
    elif demisto.command() == 'sentinelone-expire-site':
        expire_site_command()
    elif demisto.command() == 'sentinelone-reactivate-site':
        reactivate_site_command()
    elif demisto.command() == 'sentinelone-list-agents':
        list_agents_command()
    elif demisto.command() == 'sentinelone-get-agent':
        get_agent_command()
    elif demisto.command() == 'sentinelone-get-groups':
        get_groups_command()
    elif demisto.command() == 'sentinelone-move-agent':
        move_agent_to_group_command()
    elif demisto.command() == 'sentinelone-delete-group':
        delete_group()
    elif demisto.command() == 'sentinelone-agent-processes':
        get_agent_processes()
    elif demisto.command() == 'sentinelone-create-query':
        create_query()
    elif demisto.command() == 'sentinelone-get-events':
        get_events()


except Exception as e:
    LOG(e.message)
    LOG.print_log()
    raise
