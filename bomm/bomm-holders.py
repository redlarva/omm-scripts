import argparse
import concurrent.futures
import json
import os
import time

from checkscore.repeater import retry
from iconsdk.builder.call_builder import CallBuilder
from iconsdk.icon_service import IconService
from iconsdk.providers.http_provider import HTTPProvider

ADDRESSES = {
  'bOMM': 'cxeaff5a10cb72bf85965b8b4af3e708ab772b7921'
  # contracts['bOMM']="cx81f0fd355a1d4fcc65e8fc1ea90f050fa33edfb4"
  # contracts['rewardWeightController']="cxb60dae4b6660555677f93918f7d4bbb7dd8860bd"
}

SERVER_URL = "https://ctz.solidwallet.io"


def argumentParser():
  parser = argparse.ArgumentParser()

  parser.add_argument("-tkn", "--token", help="Token", type=str, default="oICX")
  parser.add_argument("-nid", "--nid", help="NID", type=int, default="1")

  args = parser.parse_args()

  return args


class BOMMHolders(object):
  def __init__(self, ):
    super(BOMMHolders, self).__init__()

    self.wallets = []
    self.data = []

    self.icon_service = IconService(HTTPProvider(SERVER_URL, 3))

    self.addresses = ADDRESSES

  def _get_bOMM_balance(self, wallet):
    result = self._call_tx(self.addresses['bOMM'], "getLocked",
                           {"_owner": wallet})
    return {
      "ommToken": int(result.get("amount"), 16) / 10 ** 18,
      "expire": int(result.get("amount"), 16)
    }

  @retry(Exception, tries=3, delay=1, back_off=2)
  def _call_tx(self, contract, method, params):
    params = {} if params is None else params
    call = CallBuilder() \
      .from_('hx91bf040426f226b3bfcd2f0b5967bbb0320525ce') \
      .to(contract) \
      .method(method) \
      .params(params) \
      .build()
    response = self.icon_service.call(call)
    return response

  def get_deposit_wallets(self):
    batch_size = 100
    index = 0
    while batch_size == 100:
      deposit_wallets = self._call_tx(self.addresses['bOMM'],
                                      'getUsers',
                                      {'start': index, "end": index + 100})
      self.wallets.extend(deposit_wallets)
      index += 100
      batch_size = len(deposit_wallets)
    deposit_wallets = self._call_tx(self.addresses['bOMM'],
                                    'getUsers', {'start': index, "end": index + 100})
    self.wallets.extend(deposit_wallets)

  def snapshot(self, _token):
    self.token = _token
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=min(32, os.cpu_count() + 20)) as executor:
      executor.map(self._get_balances, self.wallets)
    _data = self._get_data()
    _sum = 0
    for item in _data:
      print(item['balance'])
      _sum += item['balance']

    print(f"The sum of {_token} balances is: {_sum}")

    with open(f'{int(time.time())}_{token}-holders.json', 'w') as outfile:
      json.dump(_data, outfile)

  def _get_balances(self, wallet):
    _token_address = self.addresses[self.token]
    _balance = self._call_tx(_token_address, 'balanceOf', {'_owner': wallet})
    _balance = int(_balance, 16) / 10 ** 18
    if _balance > 0:
      _principalBalances = self._call_tx(_token_address, 'principalBalanceOf',
                                         {'_user': wallet})
      _row = {
        "wallet": wallet,
        "principal_balance": int(_principalBalances, 16) / 10 ** 18,
        "balance": _balance
      }
      self.data.append(_row)

  def _get_data(self):
    return sorted(self.data, reverse=True, key=lambda _row: _row['balance'])


if __name__ == '__main__':
  args = argumentParser()
  nid = args.nid
  token = args.token
  print(nid, token)
  before = time.perf_counter()
  instance = BOMMHolders(nid)

  instance.get_deposit_wallets()

  after = time.perf_counter()
  print(f"The time taken to fetch wallets: {after - before} seconds")

  instance.snapshot(token)

  after = time.perf_counter()
  print(f"The time taken to calculate: {after - before} seconds")
