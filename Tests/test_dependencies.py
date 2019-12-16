import json
import math

class TestVertex:
    def __init__(self, test_name):
        self.neighbors = {}
        self.test_name = test_name

        self.visited = False

    def add_neighbor(self, neighbor_test):
        neighbor_name = neighbor_test.test_name
        self.neighbors[neighbor_name] = neighbor_test

    def get_connected_component(self, tests_in_component):
        tests_in_component.append(self.test_name)
        self.visited = True
        for neighbor_name in self.neighbors:
            neighbor_vertex = self.neighbors[neighbor_name]
            if not neighbor_vertex.visited:
                tests_in_component = neighbor_vertex.get_connected_component(tests_in_component)
        return tests_in_component



class TestsGraph:
    def __init__(self):
        self.test_vertices = {}
        self.clusters = []

    def add_test_graph_vertices(self, tests_data):
        for test_playbook_record in tests_data:
            playbook_name_in_record = test_playbook_record.get("playbookID")
            if playbook_name_in_record and playbook_name_in_record not in self.test_vertices:
                new_test_vertex = TestVertex(playbook_name_in_record)
                self.test_vertices[playbook_name_in_record] = new_test_vertex


    def add_test_graph_neighbors(self, tests_data):
        integration_to_tests_mapping = get_integration_to_tests_mapping(tests_data)
        for integration_name in integration_to_tests_mapping:
            tests_using_integration = integration_to_tests_mapping[integration_name]
            for i in range(len(tests_using_integration)):
                first_test_name = tests_using_integration[i]
                first_test_vertex = self.test_vertices[first_test_name]

                for j in range(i+1, len(tests_using_integration)):
                    second_test_name = tests_using_integration[j]
                    second_test_vertex = self.test_vertices[second_test_name]

                    first_test_vertex.add_neighbor(second_test_vertex)
                    second_test_vertex.add_neighbor(first_test_vertex)

    def get_clusters(self):
        clusters = []
        for test_name in self.test_vertices:
            test_vertex = self.test_vertices[test_name]
            if not test_vertex.visited:
                test_connected_component = test_vertex.get_connected_component([])
                clusters.append(test_connected_component)
        self.clusters = clusters

    def build_tests_graph_from_conf_json(self, tests_file_path):
        with open(tests_file_path, 'r') as myfile:
            conf_json_string = myfile.read()

        tests_data = json.loads(conf_json_string)["tests"]
        dependent_tests = get_test_dependencies(tests_file_path)[0]

        dependent_tests_data = [test_record for test_record in tests_data if test_record.get("playbookID") in dependent_tests]

        self.add_test_graph_vertices(dependent_tests_data)
        self.add_test_graph_neighbors(dependent_tests_data)
        self.get_clusters()


def get_integration_to_tests_mapping(tests_data):
    integration_to_tests_mapping = {}
    for test_playbook_record in tests_data:
        record_playbook_name = test_playbook_record.get("playbookID", None)
        record_integrations = get_tested_integrations(test_playbook_record)
        for integration_name in record_integrations:
            if integration_name in integration_to_tests_mapping:
                if not record_playbook_name in integration_to_tests_mapping[integration_name]:
                    integration_to_tests_mapping[integration_name].append(record_playbook_name)
            else:
                integration_to_tests_mapping[integration_name] = [record_playbook_name]
    return integration_to_tests_mapping


def get_tested_integrations(test_playbook_record):
    tested_integrations = test_playbook_record.get("integrations", [])
    if isinstance(tested_integrations, list):
        return tested_integrations
    else:
        return [tested_integrations]


def get_integration_dependencies():
    with open('conf.json', 'r') as myfile:
        conf_json_string = myfile.read()

    conf_json_obj = json.loads(conf_json_string)

    integration_tests_count = {}
    for test_record in conf_json_obj["tests"]:
        integrations_used = get_tested_integrations(test_record)
        for integration_name in integrations_used:
            if integration_name in integration_tests_count:
                integration_tests_count[integration_name] += 1
            else:
                integration_tests_count[integration_name] = 1

    dependent_integrations = [integration_name for integration_name in integration_tests_count if integration_tests_count[integration_name] > 1]
    independent_integrations = [integration_name for integration_name in integration_tests_count if integration_tests_count[integration_name] <= 1]
    print("Number of dependent integrations is: {0}, number of independent is: {1}".format(len(dependent_integrations), len(independent_integrations)))
    return dependent_integrations, independent_integrations


def get_test_dependencies(tests_file_path):
    dependent_integrations = get_integration_dependencies()[0]

    with open(tests_file_path, 'r') as myfile:
        conf_json_string = myfile.read()
    conf_json_obj = json.loads(conf_json_string)

    dependent_tests = []
    all_tests = []
    for test_record in conf_json_obj["tests"]:
        integrations_used = get_tested_integrations(test_record)
        playbook = test_record.get("playbookID", None)
        if playbook not in all_tests:
            all_tests.append(playbook)
        dependent_integrations_used = [integration for integration in integrations_used if integration in dependent_integrations]
        if dependent_integrations_used and playbook not in dependent_tests:
            dependent_tests.append(playbook)

    independent_tests = [test for test in all_tests if test not in dependent_tests]
    print("Number of dependent tests: {0}, number of total tests: {1}".format(len(dependent_tests), len(all_tests)))
    return dependent_tests, independent_tests, all_tests


def get_dependent_integrations_clusters_data(tests_file_path):
    tests_graph = TestsGraph()
    tests_graph.build_tests_graph_from_conf_json(tests_file_path)
    return tests_graph.clusters


def get_tests_allocation(number_of_instances, tests_file_path):
    dependent_tests, independent_tests, all_tests = get_test_dependencies(tests_file_path)
    dependent_tests_clusters = get_dependent_integrations_clusters_data(tests_file_path)
    dependent_tests_clusters.sort(key=len, reverse=True) # Sort the clusters from biggest to smallest
    tests_allocation = []
    number_of_tests_left = len(all_tests)

    while number_of_tests_left > 0:
        allocations_left = number_of_instances - len(tests_allocation)
        tests_left = number_of_tests_left
        desired_tests_per_allocation = math.ceil(tests_left / allocations_left)  # We prefer an equal division of tests.
        current_allocation = []
        current_allocation_size = 0

        # If we have one allocation left, add all tests to it and finish
        if allocations_left == 1:
            for tests_cluster in dependent_tests_clusters:
                current_allocation.extend(tests_cluster)
            for test_name in independent_tests:
                current_allocation.append(test_name)
            tests_allocation.append(current_allocation)
            break

        first_cluster = dependent_tests_clusters.pop(0)
        first_cluster_size = len(first_cluster)
        current_allocation.extend(first_cluster)
        current_allocation_size += first_cluster_size
        number_of_tests_left -= first_cluster_size

        if current_allocation_size > desired_tests_per_allocation:
            continue

        clusters_added = 0
        for cluster in dependent_tests_clusters:
            cluster_size = len(cluster)
            if current_allocation_size + cluster_size > desired_tests_per_allocation:
                break
            current_allocation.extend(cluster)
            current_allocation_size += cluster_size
            number_of_tests_left -= cluster_size
            clusters_added += 1

        del dependent_tests_clusters[:clusters_added]

        while current_allocation_size < desired_tests_per_allocation and len(independent_tests) > 0:
            current_allocation.append(independent_tests.pop(0))
            number_of_tests_left -= 1
            current_allocation_size += 1

        tests_allocation.append(current_allocation)

    return tests_allocation


#get_test_dependencies()
#tests_graph = TestsGraph()
#clusters = get_dependent_integrations_clusters_data()
#cluster_size_arr = [len(cluster) for cluster in clusters]

