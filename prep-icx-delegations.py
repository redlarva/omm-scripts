"""
Get ICX delegated to a prep on OMM
Wallet addresses and the amount of ICX they delegated to a prep at this time
"""

import requests
import json
import time
import concurrent.futures
from pprint import pprint
from checkscore.repeater import retry

# mainnet
OMM_TOKEN = "cx1a29259a59f463a67bb2ef84398b30ca56b5830a"
DELEGATION = "cx841f29ec6ce98b527d49a275e87d427627f1afe5"
YOUR_PREP_ADDRESS = "" 
ENDPOINT = "https://ctz.solidwallet.io/api/v3"

class FetchData(object):
    def __init__(self, prep: str):
        super(FetchData, self).__init__()
        self.prep_address = prep
        self.stakers_list = []
        self.info = {}
    
    @retry(Exception, tries=3, delay=1, back_off=2)
    def get_request(self, payload: str):
        r = requests.post(ENDPOINT, data=payload)
        return json.loads(r.text)['result']
    
    def make_rpc_dict(self, _to_contract: str, method: str, params) -> str:
        rpc_dict = {
                'jsonrpc': '2.0',
                'method': 'icx_call',
                'id': 1234,
                'params': {
                    "from": "hxaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "to": f"{_to_contract}",  
                    "dataType": "call",
                    "data": {
                        "method": f"{method}",
                        "params": params
                    }
            }
        }
        return json.dumps(rpc_dict)

    
    def populate_stakers_list(self, skip: int = 0):
        params: dict = {
            "_start": f'{skip}',
            "_end": f'{skip+100}',
        }
        payload: str = self.make_rpc_dict(OMM_TOKEN, "getStakersList", params)
        wallets: list = self.get_request(payload)
        self.stakers_list.extend(wallets)
        if len(wallets) >= 100:
            self.populate_stakers_list(skip+100)

    def calculate_delegation_info(self, _user: str):
        print(f"Fetch delegation info for: {_user}")
        params: dict = {"_user": _user}
        payload: str = self.make_rpc_dict(DELEGATION, "getUserDelegationDetails", params)
        info: list = self.get_request(payload)
        for i in info:
            if i.get("_address") == self.prep_address:
                self.info[_user] = int(i.get("_votes_in_icx"), 16) ## / 10 ** 18 ICX
    
    def get_stakers_list(self) -> list:
        return self.stakers_list
    
    def get_delegation_info(self) -> dict:
        return self.info

if __name__ == "__main__":
    instance = FetchData(YOUR_PREP_ADDRESS)
    instance.populate_stakers_list()
    stakers_list: list = instance.get_stakers_list()

    # use multithreading to get delegation info of stakers
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        executor.map(instance.calculate_delegation_info, stakers_list)

    delegation_info: dict = instance.get_delegation_info()
    # save this delegation_info somewhere
    with open(f"{int(time.time())}_omm_delegations.json", "w") as outfile:
        json.dump(delegation_info, outfile)