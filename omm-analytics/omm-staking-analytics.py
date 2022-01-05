import json
import requests
from checkscore.repeater import retry
from datetime import datetime

from helpers.constants import ADDRESS, GEOMETRY_LOG_API, US_PER_HR, GEOMETRY_TRANSACTION_DETAIL_API, EXA
from helpers.logger import logger
from helpers.mysql import connection,get_prev_timestamp

KEY = "OMM"
# cursor = mydb.cursor()

SQL_INSERT_OMM_STAKE = (
    "INSERT INTO omm_staking_stats"
    "(staking, unstaking,cancelUnstaking, timestamp, _index)"
    "VALUES (%s, %s,  %s,%s, %s) ON DUPLICATE KEY UPDATE staking=%s, unstaking=%s, cancelUnstaking=%s"
)
SQL_INSERT_OMM_STAKE_AMOUNT = (
    "INSERT INTO omm_staking_amount"
    "(staking, unstaking,cancelUnstaking, timestamp, _index)"
    "VALUES (%s, %s, %s, %s,%s) ON DUPLICATE KEY UPDATE staking=%s, unstaking=%s, cancelUnstaking=%s"
)

SQL_UPDATE_PREV_TIMESTAMP = ("UPDATE timestamp_history SET timestamp = %s WHERE _key = %s")


class ActiveUserData(object):
    def __init__(self):
        super(ActiveUserData, self).__init__()
        self.data = {
            "count": {"stake": [], "unstake": [], "cancelUnstake": []},
            "amount": {"stake": 0.0, "unstake": 0.0, "cancelUnstake": 0.0}
        }

    def add(self, method, address, amount):
        if address not in self.data["count"][method]:
            self.data["count"][method].append(address)
        self.data["amount"][method] = self.data["amount"][method] + amount

    def getSummary(self):
        count = self.data.get("count")
        amount = self.data.get("amount")

        stake_count = len(count.get('stake'))
        unstake_count = len(count.get('unstake'))
        cancel_unstake_count = len(count.get('cancelUnstake'))
        return {
            "addresses": {
                'staking': count.get('stake'),
                'unstaking': count.get('unstake'),
                'cancelUnstaking': count.get('unstake'),
            },
            "count": {
                'staking': stake_count,
                'unstaking': unstake_count,
                'cancelUnstaking': cancel_unstake_count,
            },
            "amount": {
                'staking': amount.get("stake"),
                'unstaking': amount.get("unstake"),
                'cancelUnstaking': amount.get("cancelUnstake"),
            }
        }


class OMMAnalytics(object):
    def __init__(self, index: int, starting_timestamp: int, ending_timestamp: int):
        self.index = index
        self.start_timestamp = starting_timestamp
        self.end_timestamp = ending_timestamp
        self.data = ActiveUserData()
        self.summary = {}
        self.block_timestamp = ending_timestamp
        self.threshold_reached = False

    @retry(Exception, tries=20, delay=1, back_off=2)
    def _get_log_request(self, skip, method, score):
        payload = {'skip': skip, 'method': method, "limit": 100, "score_address": score}
        req = requests.get(GEOMETRY_LOG_API, params=payload)
        return json.loads(req.text)

    @retry(Exception, tries=20, delay=1, back_off=2)
    def _add(self, transaction_hash):
        try:
            req = requests.get(f"{GEOMETRY_TRANSACTION_DETAIL_API}{transaction_hash}")
            tx_detail = json.loads(req.text)
            _data = json.loads(tx_detail.get("data"))
            method = tx_detail.get("method")
            address = tx_detail.get("from_address")
            amount = int(_data.get("params").get("_value"), 16) / EXA
            self.data.add(method, address, amount)
        except Exception as e:
            print(e)
            raise e

    def _fetch(self, skip):
        _data = self._get_log_request(skip, "SnapshotCreated", ADDRESS['OMM_TOKEN'])
        logger.info(f"....{skip}....omm stake/unstake")
        for row in _data:
            block_timestamp = int(row.get("block_timestamp"))
            transaction_hash = row.get("transaction_hash")
            self.threshold_reached = block_timestamp <= self.start_timestamp
            if not self.threshold_reached and block_timestamp <= self.end_timestamp:
                self._add(transaction_hash)
                self.block_timestamp = block_timestamp

        if not self.threshold_reached:
            self._fetch(skip + 100)
        else:
            logger.info(f"threshold reached at {skip}")

    def fetch(self):
        self._fetch(0)

    def _save_stake_unstake(self, timestamp: int):
        self.summary['omm'] = self.data.getSummary()

        count_val = (self.summary['omm']["count"]["staking"],
                     self.summary['omm']["count"]["unstaking"],
                     self.summary['omm']["count"]["cancelUnstaking"], timestamp, self.index,
                     self.summary['omm']["count"]["staking"],
                     self.summary['omm']["count"]["unstaking"],
                     self.summary['omm']["count"]["cancelUnstaking"],)
        amount_val = (self.summary['omm']["amount"]["staking"],
                      self.summary['omm']["amount"]["unstaking"],
                      self.summary['omm']["amount"]["cancelUnstaking"], timestamp, self.index,
                      self.summary['omm']["amount"]["staking"],
                      self.summary['omm']["amount"]["unstaking"],
                      self.summary['omm']["amount"]["cancelUnstaking"],)
        logger.info(f"inserting omm staking stats {self.index}-{timestamp}")
        logger.info("%s,%s,%s,%s,%s" % (self.summary['omm']["count"]["staking"],
                                        self.summary['omm']["count"]["unstaking"],
                                        self.summary['omm']["count"]["cancelUnstaking"], timestamp, self.index))
        with connection.cursor() as cursor:
            cursor.execute(SQL_INSERT_OMM_STAKE, count_val)
            cursor.execute(SQL_INSERT_OMM_STAKE_AMOUNT, amount_val)

    def save(self):
        timestamp = self.end_timestamp // 1_000_000
        self._save_stake_unstake(timestamp)

        with open(f'{timestamp}_users_info.json', 'w') as outfile:
            logger.info('... Saving users info json ...')
            json.dump(self.summary, outfile)




if __name__ == "__main__":
    with connection:
        prev_timestamp = get_prev_timestamp(KEY) // US_PER_HR * US_PER_HR
        current_timestamp = int(datetime.timestamp(datetime.now()) * 1_000_000)
        """
        # to get data between timestamps
        prev_timestamp = 1641297625_000_000
        current_timestamp = 1641304819_000_000
        """

        ts = current_timestamp // US_PER_HR * US_PER_HR
        for i in range(prev_timestamp, current_timestamp, US_PER_HR):
            index = i // US_PER_HR
            starting_timestamp = i
            ending_timestamp = i + US_PER_HR
            analytics = OMMAnalytics(index, starting_timestamp, ending_timestamp)
            analytics.fetch()
            analytics.save()

        _val = (analytics.block_timestamp, KEY,)
        logger.info('...Updating last update timestamp...')
        with connection.cursor() as cursor:
            cursor.execute(SQL_UPDATE_PREV_TIMESTAMP, _val)
        connection.commit()
