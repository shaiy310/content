from FeedMicrosoftIntune import Client

BASE_URL = 'https://docs.microsoft.com/en-us/intune/fundamentals/intune-endpoints'


def test_build_iterator():
    expected_domain = 'login.microsoftonline.com'
    expected_domain_glob = '*.manage.microsoft.com'
    expected_ip = '52.175.12.209'
    expected_cidr = '40.82.248.224/28'
    client = Client(
        base_url=BASE_URL,
        verify=False,
        proxy=False,
    )
    indicators = client.build_iterator()
    domain_indicators = {indicator['value'] for indicator in indicators if indicator['type'] == 'Domain'}
    domain_glob_indicators = {indicator['value'] for indicator in indicators if indicator['type'] == 'DomainGlob'}
    ip_indicators = {indicator['value'] for indicator in indicators if indicator['type'] == 'IP'}
    cidr_indicators = {indicator['value'] for indicator in indicators if indicator['type'] == 'CIDR'}
    assert expected_domain in domain_indicators
    assert expected_domain_glob in domain_glob_indicators
    assert expected_ip in ip_indicators
    assert expected_cidr in cidr_indicators
