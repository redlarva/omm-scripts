import argparse
import csv
import json
import requests
import time
import sys

from checkscore.repeater import retry

LIMIT = 1000
print(sys.getrecursionlimit())
sys.setrecursionlimit(LIMIT)
print(sys.getrecursionlimit())

API = 'https://tracker.icon.community/api/v1/logs'
OMM_sICX_POOL_ID = '0x7'
LP_ADDED_TIMESTAMP = 1629954000000000

OMM_sICX = "cx687fa54d7b8328fc560dc7a68a0d44d7f1091a25"

# LP_ADDED_TIMESTAMP = 1640753927183022

ADDRESS = {
  'LENDING_POOL': 'cxcb455f26a2c01c686fa7f30e1e3661642dd53c0d',
  'oICX': 'cx0fb973aaab3a26cc99022ba455e5bdfed1d6f0d9',
  'reward': 'cx4f2d730ad969f5c839229de42184c5e47aefef6f',
  'DEX': 'cxa0af3165c08318e988cb30993b3048335b94af6c'
}

LIST_API = "https://main.tracker.solidwallet.io/v3/contract/txList"
TX_DETAIL_API = "https://main.tracker.solidwallet.io/v3/transaction/txDetail"


def argumentParser():
  parser = argparse.ArgumentParser()

  parser.add_argument("-tkn", "--token", help="Token", type=str, default="oICX")
  parser.add_argument("-nid", "--nid", help="NID", type=int, default="1")
  parser.add_argument("-p", "--page", help="Page", type=int, default="1")

  args = parser.parse_args()

  return args


class LiquidityProvider(object):
  def __init__(self):
    super(LiquidityProvider, self).__init__()
    self.has_threshold_reach = False;
    self.wallets = []
    self.OMM_SICX_WALLET = []

  @retry(Exception, tries=20, delay=1, back_off=2)
  def _get_request(self, page):

    payload = {'page': page, 'count': 100, "addr": ADDRESS['DEX']}

    req = requests.get(LIST_API, params=payload)

    return json.loads(req.text).get("data")

  @retry(Exception, tries=20, delay=1, back_off=2)
  def get_tx_details(self, txHash):

    payload = {'txHash': txHash}

    req = requests.get(TX_DETAIL_API, params=payload)

    return json.loads(req.text).get("data")

  def _fetch_wallets_reward(self, page: int):
    print(f"---------{page}--------")
    _data = self._get_request(page)

    for row in _data:
      try:
        txHash = row.get("txHash")
        details = self.get_tx_details(txHash)

        data = json.loads(details.get("dataString"))

        if data.get("method") == 'transfer' and data.get("params").get(
            "_to") == "cx015c7f8884d43519aa2bcf634140bd7328730cb6":
          if data.get("params").get("_id") == OMM_sICX_POOL_ID:
            self.OMM_SICX_WALLET.append(row.get("fromAddr"))
          self.wallets.append(row.get("fromAddr"))
      except Exception as e:
        print(row)
    if self.has_threshold_reach >= page + 1 and len(_data) == 100:
      self._fetch_wallets_reward(page + 1)

  def get_wallets(self, page: int):
    self._fetch_wallets_reward(page)
    print(set(self.wallets))
    print(set(self.OMM_SICX_WALLET))
    with open(f'{int(time.time())}-lp.json', 'w') as outfile:
      json.dump(list(set(self.wallets)), outfile)

    with open(f'{int(time.time())}-OMM_SICX_WALLET-lp.json', 'w') as outfile:
      json.dump(list(set(self.OMM_SICX_WALLET)), outfile)


if __name__ == '__main__':
  args = argumentParser()
  nid = args.nid
  token = args.token
  page = args.page
  # print(nid, token)
  before = time.perf_counter()
  instance = LiquidityProvider()
  instance.has_threshold_reach = page + 100
  instance.get_wallets(page)
