username_context = {
    'Domain(val.Name && val.Name == obj.Name)': {
        'Name': 'jondon', 'Pwned-V2': {
            'Compromised': {
                'Vendor': 'Have I Been Pwned? V2', 'Reporters': 'Gawker, hackforums.net'
            }
        }, 'Malicious': {'Vendor': 'Have I Been Pwned? V2', 'Description': 'The domain has been compromised'
                         }
    }, 'DBotScore': {
        'Indicator': 'jondon', 'Type': 'domain', 'Vendor': 'Have I Been Pwned? V2', 'Score': 3
    }
}
domain_context = {
    'Domain(val.Name && val.Name == obj.Name)': {
        'Name': 'adobe.com', 'Pwned-V2': {
            'Compromised': {
                'Vendor': 'Have I Been Pwned? V2', 'Reporters': 'Adobe'
            }
        }, 'Malicious': {'Vendor': 'Have I Been Pwned? V2', 'Description': 'The domain has been compromised'
                        }
    }, 'DBotScore': {'Indicator': 'adobe.com', 'Type': 'domain', 'Vendor': 'Have I Been Pwned? V2', 'Score': 3
                     }
}
