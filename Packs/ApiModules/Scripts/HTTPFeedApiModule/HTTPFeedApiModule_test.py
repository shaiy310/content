from HTTPFeedApiModule import get_indicators_command, Client
import requests_mock


def test_get_indicators():
    with open('test_data/asn_ranges.txt') as asn_ranges_txt:
        asn_ranges = asn_ranges_txt.read().encode('utf8')

    with requests_mock.Mocker() as m:
        itype = 'ASN'
        args = {
            'indicator_type': itype,
            'limit': 35
        }
        feed_type = {
            'https://www.spamhaus.org/drop/asndrop.txt': {
                'indicator_type': 'ASN',
                'indicator': {
                    'regex': '^AS[0-9]+'
                },
                'fields': [
                    {
                        'asndrop_country': {
                            'regex': r'^.*;\W([a-zA-Z]+)\W+',
                            'transform': r'\1'
                        }
                    },
                    {
                        'asndrop_org': {
                            'regex': r'^.*\|\W+(.*)',
                            'transform': r'\1'
                        }
                    }
                ]
            }
        }
        m.get('https://www.spamhaus.org/drop/asndrop.txt', content=asn_ranges)
        client = Client(
            url="https://www.spamhaus.org/drop/asndrop.txt",
            source_name='spamhaus',
            fieldnames='indicator',
            ignore_regex='^;.*',
            feed_url_to_config=feed_type
        )
        args['indicator_type'] = 'ASN'
        hr, indicators_ec, raw_json = get_indicators_command(client, args)
        indicators_ec = indicators_ec.get('HTTP.Indicator')
        assert len(indicators_ec) == 35
        for ind_json in raw_json:
            ind_val = ind_json.get('value')
            ind_type = ind_json.get('type')
            ind_rawjson = ind_json.get('rawJSON')
            assert ind_val
            assert ind_type == itype
            assert ind_rawjson['value'] == ind_val
            assert ind_rawjson['type'] == ind_type
