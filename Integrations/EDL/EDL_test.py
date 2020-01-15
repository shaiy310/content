"""Imports"""
import json
import pytest
import demistomock as demisto

IOC_RES_LEN = 38

'''Tests'''


@pytest.mark.helper_commands
class TestHelperFunctions:
    @pytest.mark.get_edl_ioc_values
    def test_get_edl_ioc_values_1(self, mocker):
        """Test on_demand"""
        from EDL import get_edl_ioc_values
        with open('EDL_test/TestHelperFunctions/iocs_cache_values_text.json', 'r') as iocs_text_values_f:
            iocs_text_dict = json.loads(iocs_text_values_f.read())
            params = {'format': 'text', 'on_demand': True, 'edl_size': 50}
            mocker.patch.object(demisto, 'getIntegrationContext', return_value=iocs_text_dict)
            ioc_list = get_edl_ioc_values(params)
            for ioc_row in ioc_list:
                assert ioc_row in iocs_text_dict

    @pytest.mark.get_edl_ioc_values
    def test_get_edl_ioc_values_2(self, mocker):
        """Test update by not on_demand with no refresh"""
        import CommonServerPython as CSP
        mocker.patch.object(CSP, 'parse_date_range', return_value=(1578383899, 1578383899))
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/iocs_cache_values_text.json', 'r') as iocs_text_values_f:
            iocs_text_dict = json.loads(iocs_text_values_f.read())
            params = {'format': 'text', 'on_demand': False, 'edl_size': 50, 'cache_refresh_rate': '1 minute'}
            mocker.patch.object(demisto, 'getIntegrationContext', return_value=iocs_text_dict)
            mocker.patch.object(edl, 'refresh_edl_context', return_value=iocs_text_dict)
            mocker.patch.object(demisto, 'getLastRun', return_value={'last_run': 1578383898000})
            ioc_list = edl.get_edl_ioc_values(params)
            for ioc_row in ioc_list:
                assert ioc_row in iocs_text_dict

    @pytest.mark.get_edl_ioc_values
    def test_get_edl_ioc_values_3(self, mocker):
        """Test update by not on_demand with refresh"""
        import CommonServerPython as CSP
        mocker.patch.object(CSP, 'parse_date_range', return_value=(1578383898, 1578383898))
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/iocs_cache_values_text.json', 'r') as iocs_text_values_f:
            iocs_text_dict = json.loads(iocs_text_values_f.read())
            params = {'format': 'text', 'on_demand': False, 'edl_size': 50, 'cache_refresh_rate': '1 minute'}
            mocker.patch.object(demisto, 'getIntegrationContext', return_value=iocs_text_dict)
            mocker.patch.object(edl, 'refresh_edl_context', return_value=iocs_text_dict)
            mocker.patch.object(demisto, 'getLastRun', return_value={'last_run': 1578383898000})
            ioc_list = edl.get_edl_ioc_values(params)
            for ioc_row in ioc_list:
                assert ioc_row in iocs_text_dict

    @pytest.mark.list_to_str
    def test_list_to_str_1(self):
        """Test invalid"""
        from EDL import list_to_str
        with pytest.raises(AttributeError):
            invalid_list_value = 2
            list_to_str(invalid_list_value)

        with pytest.raises(AttributeError):
            invalid_list_value = {'invalid': 'invalid'}
            list_to_str(invalid_list_value)

    @pytest.mark.list_to_str
    def test_list_to_str_2(self):
        """Test empty"""
        from EDL import list_to_str
        assert list_to_str(None) == ''
        assert list_to_str([]) == ''
        assert list_to_str({}) == ''

    @pytest.mark.list_to_str
    def test_list_to_str_3(self):
        """Test non empty fields"""
        from EDL import list_to_str
        valid_list_value = [1, 2, 3, 4]
        assert list_to_str(valid_list_value) == '1,2,3,4'
        assert list_to_str(valid_list_value, '.') == '1.2.3.4'
        assert list_to_str(valid_list_value, map_func=lambda x: f'{x}a') == '1a,2a,3a,4a'

    @pytest.mark.get_params_port
    def test_get_params_port_1(self):
        """Test invalid"""
        from CommonServerPython import DemistoException
        from EDL import get_params_port
        params = {'longRunningPort': 'invalid'}
        with pytest.raises(DemistoException):
            get_params_port(params)

    @pytest.mark.get_params_port
    def test_get_params_port_2(self):
        """Test empty"""
        from EDL import get_params_port
        params = {'longRunningPort': ''}
        with pytest.raises(ValueError):
            get_params_port(params)

    @pytest.mark.get_params_port
    def test_get_params_port_3(self):
        """Test valid"""
        from EDL import get_params_port
        params = {'longRunningPort': '80'}
        assert get_params_port(params) == 80

    @pytest.mark.refresh_edl_context
    def test_refresh_edl_context_1(self, mocker):
        """Test out_format=text"""
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.loads(iocs_json_f.read())
            mocker.patch.object(edl, 'find_indicators_to_limit', return_value=iocs_json)
            edl_vals = edl.refresh_edl_context(indicator_query='', out_format='text')
            for ioc in iocs_json:
                ip = ioc.get('value')
                assert ip in edl_vals

    @pytest.mark.refresh_edl_context
    def test_refresh_edl_context_2(self, mocker):
        """Test out_format=json"""
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.loads(iocs_json_f.read())
            mocker.patch.object(edl, 'find_indicators_to_limit', return_value=iocs_json)
            edl_vals = edl.refresh_edl_context(indicator_query='', out_format='json')
            assert isinstance(edl_vals, str)
            edl_vals = json.loads(edl_vals)
            assert iocs_json == edl_vals

    @pytest.mark.refresh_edl_context
    def test_refresh_edl_context_3(self, mocker):
        """Test out_format=csv"""
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.loads(iocs_json_f.read())
            mocker.patch.object(edl, 'find_indicators_to_limit', return_value=iocs_json)
            edl_vals = edl.refresh_edl_context(indicator_query='', out_format='csv')
            with open('EDL_test/TestHelperFunctions/iocs_out_csv.txt', 'r') as iocs_out_f:
                iocs_out = iocs_out_f.read()
                assert iocs_out == edl_vals

    @pytest.mark.refresh_edl_context
    def test_refresh_edl_context_4(self, mocker):
        """Test out_format=json-seq"""
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.loads(iocs_json_f.read())
            mocker.patch.object(edl, 'find_indicators_to_limit', return_value=iocs_json)
            edl_vals = edl.refresh_edl_context(indicator_query='', out_format='json-seq')
            with open('EDL_test/TestHelperFunctions/iocs_out_json_seq.txt', 'r') as iocs_out_f:
                iocs_out = iocs_out_f.read()
                assert iocs_out == edl_vals

    @pytest.mark.find_indicators_to_limit
    def test_find_indicators_to_limit_1(self, mocker):
        """Test find indicators limit"""
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.loads(iocs_json_f.read())
            limit = 30
            mocker.patch.object(edl, 'find_indicators_to_limit_loop', return_value=(iocs_json, 1))
            edl_vals = edl.find_indicators_to_limit(indicator_query='', limit=limit)
            assert len(edl_vals) == limit

    @pytest.mark.find_indicators_to_limit_loop
    def test_find_indicators_to_limit_loop_1(self, mocker):
        """Test find indicators stops when reached last page"""
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_dict = {'iocs': json.loads(iocs_json_f.read())}
            limit = 50
            mocker.patch.object(demisto, 'findIndicators', return_value=iocs_dict)
            edl_vals, nxt_pg = edl.find_indicators_to_limit_loop(indicator_query='', limit=limit)
            assert nxt_pg == 1  # assert entered into loop

    @pytest.mark.find_indicators_to_limit_loop
    def test_find_indicators_to_limit_loop_2(self, mocker):
        """Test find indicators stops when reached limit"""
        import EDL as edl
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_dict = {'iocs': json.loads(iocs_json_f.read())}
            limit = 30
            mocker.patch.object(demisto, 'findIndicators', return_value=iocs_dict)
            edl.PAGE_SIZE = IOC_RES_LEN
            edl_vals, nxt_pg = edl.find_indicators_to_limit_loop(indicator_query='', limit=limit,
                                                                 last_found_len=IOC_RES_LEN)
            assert nxt_pg == 1  # assert entered into loop

    @pytest.mark.create_values_out_dict
    def test_create_values_out_dict_1(self):
        """Test CSV out"""
        from EDL import create_values_out_dict, FORMAT_CSV
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.loads(iocs_json_f.read())
            csv_out = create_values_out_dict(iocs_json, FORMAT_CSV)
            # assert len(csv_out) == IOC_RES_LEN + 1
            with open('EDL_test/TestHelperFunctions/iocs_out_csv.txt', 'r') as iocs_out_f:
                expected_csv_out = iocs_out_f.read()
                for csv_line in csv_out.values():
                    assert csv_line in expected_csv_out

    @pytest.mark.create_values_out_dict
    def test_create_values_out_dict_2(self):
        """Test JSON out"""
        from EDL import create_values_out_dict, FORMAT_JSON, EDL_VALUES_KEY
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.load(iocs_json_f)
            json_out = json.loads(create_values_out_dict(iocs_json, FORMAT_JSON).get(EDL_VALUES_KEY))
            assert json_out == iocs_json

    @pytest.mark.create_values_out_dict
    def test_create_values_out_dict_3(self):
        """Test JSON_SEQ out"""
        from EDL import create_values_out_dict, FORMAT_JSON_SEQ, EDL_VALUES_KEY
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.loads(iocs_json_f.read())
            json_seq_out = create_values_out_dict(iocs_json, FORMAT_JSON_SEQ).get(EDL_VALUES_KEY)
            for seq_line in json_seq_out.split('\n'):
                assert json.loads(seq_line) in iocs_json

    @pytest.mark.create_values_out_dict
    def test_create_values_out_dict_4(self):
        """Test TEXT out"""
        from EDL import create_values_out_dict, FORMAT_TEXT, EDL_VALUES_KEY
        with open('EDL_test/TestHelperFunctions/demisto_iocs.json', 'r') as iocs_json_f:
            iocs_json = json.loads(iocs_json_f.read())
            text_out = create_values_out_dict(iocs_json, FORMAT_TEXT).get(EDL_VALUES_KEY)
            with open('EDL_test/TestHelperFunctions/iocs_cache_values_text.json', 'r') as iocs_txt_f:
                iocs_txt_json = json.load(iocs_txt_f)
                for line in text_out.split('\n'):
                    assert line in iocs_txt_json
