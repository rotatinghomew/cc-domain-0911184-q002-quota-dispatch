import json
from urllib.parse import quote
from urllib.request import Request, urlopen


class SessionPool:
    def __init__(self, base_url, credentials):
        self.base_url = base_url
        self.credentials = dict(credentials)

    def request(self, tenant, asset):
        token = self.credentials[tenant]
        request = Request(self.base_url + '/asset/' + quote(asset),
                          headers={'Authorization': token, 'X-Tenant': tenant})
        with urlopen(request, timeout=5) as response:
            payload = json.load(response)
        if payload['tenant'] != tenant or payload['asset'] != asset:
            raise ValueError('response ownership mismatch')
        return payload
