import json
import requests
from checkscore.repeater import retry
from datetime import datetime

from helpers.constants import ADDRESS, GEOMETRY_LOG_API, US_PER_HR, TOKENS
from helpers.logger import logger
from helpers.mysql import connection
from helpers.utils import get_unique_count, get_total_count, zero_if_none

KEY = 'RESERVE'

SQL_INSERT_OMM_STATS = (
    "INSERT INTO reserve_stats "
    "(_index, timestamp, deposit, borrow, redeem, repay, unique_address, reserve)"
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    "ON DUPLICATE KEY UPDATE deposit=%s, borrow=%s, redeem=%s, repay=%s, unique_address=%s"
)

SQL_INSERT_TXN_AMOUNT = (
    "INSERT INTO reserve_amount "
    "(_index, timestamp, deposit, borrow, redeem, repay, reserve)"
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    "ON DUPLICATE KEY UPDATE deposit=%s, borrow=%s, redeem=%s, repay=%s"
)

SQL_UPDATE_PREV_TIMESTAMP = ("UPDATE timestamp_history SET timestamp = %s WHERE _key = %s")


class ActiveUserData(object):
    def __init__(self):
        super(ActiveUserData, self).__init__()
        self.data = {
            "deposit": {"sicx": [],"usds": [],"iusdc": [],"bnusd": [],"baln": [],"omm": []},
            "borrow": {"sicx": [], "usds": [], "iusdc": [], "bnusd": [], "baln": []},
            "redeem": {"sicx": [],"usds": [],"iusdc": [],"bnusd": [],"baln": [],"omm": []},
            "repay": {"sicx": [], "usds": [], "iusdc": [], "bnusd": [], "baln": []},
        }

        self.amount = {
            "sicx": {"deposit": 0, "borrow": 0, "redeem": 0, "repay": 0},
            "usds": {"deposit": 0, "borrow": 0, "redeem": 0, "repay": 0},
            "iusdc": {"deposit": 0, "borrow": 0, "redeem": 0, "repay": 0},
            "bnusd": {"deposit": 0, "borrow": 0, "redeem": 0, "repay": 0},
            "baln": {"deposit": 0, "borrow": 0, "redeem": 0, "repay": 0},
            "omm": {"deposit": 0, "borrow": 0, "redeem": 0, "repay": 0},
        }

    def _addAmount(self, method, reserve, amount):
        amount = int(amount, 16)
        decimals = 18
        if reserve == "iusdc":
            decimals = 6
        amount = amount / (10 ** decimals)
        self.amount[reserve][method] += amount

    def add(self, method, reserve, address, amount):
        method = method.lower()
        if address not in self.data[method][reserve]:
            self.data[method][reserve].append(address)
        # add amount
        self._addAmount(method, reserve, amount)

    def getSummary(self):
        txns = self.data
        amount = self.amount
        summary = {}

        info = {"omm": {}, "baln": {}, "sicx": {}, "usds": {}, "iusdc": {}, "bnusd": {}}
        count = {"omm": {},"baln": {},"sicx": {},"usds": {},"iusdc": {},"bnusd": {}}

        for method, values in txns.items():
            for token, addresses in values.items():
                info[token][method] = addresses
                count[token][method] = len(set(addresses))

        for key, value in info.items():
            info[key]["unique_addr_count"] = get_unique_count(value)

        depositors_count = get_unique_count(txns.get("deposit"))
        borrowers_count = get_unique_count(txns.get("borrow"))
        repayers_count = get_unique_count(txns.get("repay"))
        redeemers_count = get_unique_count(txns.get("redeem"))
        unique_addr_count = get_total_count(txns)

        _summary = {
            "depositors_count": depositors_count,
            "borrowers_count": borrowers_count,
            "repayers_count": repayers_count,
            "redeemers_count": redeemers_count,
            "unique_addr_count": unique_addr_count,
        }

        summary = txns
        summary['summary'] = _summary
        return summary, count, info

    def getAmountSummary(self):
        return self.amount


class OMMAnalytics(object):
    def __init__(self, index: int, starting_timestamp: int, ending_timestamp: int):
        self.index = index
        self.timestamp = ending_timestamp
        self.start_timestamp = starting_timestamp
        self.end_timestamp = ending_timestamp
        self.data = ActiveUserData()
        self.summary = {}

    @retry(Exception, tries=20, delay=1, back_off=2)
    def _get_log_request(self, skip, method, score):
        payload = {"skip": skip, "method": method, "limit": 100, "score_address": score}
        req = requests.get(GEOMETRY_LOG_API, params=payload)
        return json.loads(req.text)

    def _fetch_users(self, skip, method):
        _data = self._get_log_request(skip, method, ADDRESS["LENDING_POOL"])
        logger.info(f"....{skip}....{method}")
        for row in _data:
            block_timestamp = int(row.get("block_timestamp"))
            self.threshold_reached = self.start_timestamp >= block_timestamp
            if (not self.threshold_reached) and (block_timestamp <= self.end_timestamp):
                self.timestamp = block_timestamp
                method = row.get("method")
                indexed = json.loads(row.get("indexed"))
                if method == "RedeemUnderlying":
                    self.data.add("Redeem", TOKENS[indexed[1]], indexed[2], indexed[3])
                else:
                    self.data.add(method, TOKENS[indexed[1]], indexed[2], indexed[3])

        if not self.threshold_reached:
            self._fetch_users(skip + 100, method)
        else:
            logger.info(f"threshold reached at {skip}")

    def fetch(self):
        self._fetch_users(0, "Deposit")
        self._fetch_users(0, "Borrow")
        self._fetch_users(0, "RedeemUnderlying")
        self._fetch_users(0, "Repay")

    def _save_reserve_txns(self, timestamp: int):
        summary, count, info = self.data.getSummary()
        self.summary = summary

        for key, value in count.items():
            _val = (
                self.index,
                timestamp,
                zero_if_none(value.get("deposit")),
                zero_if_none(value.get("borrow")),
                zero_if_none(value.get("redeem")),
                zero_if_none(value.get("repay")),
                info[key]["unique_addr_count"],
                key.upper(),
                zero_if_none(value.get("deposit")),
                zero_if_none(value.get("borrow")),
                zero_if_none(value.get("redeem")),
                zero_if_none(value.get("repay")),
                info[key]["unique_addr_count"],
            )
            logger.info(f"inserting {key} stats")
            logger.info("%s,%s,%s,%s,%s,%s,%s,%s" % _val[:8])

            with connection.cursor() as cursor:
                cursor.execute(SQL_INSERT_OMM_STATS, _val)

        _val = (
            self.index,
            timestamp,
            self.summary['summary']['depositors_count'],
            self.summary['summary']['borrowers_count'],
            self.summary['summary']['redeemers_count'],
            self.summary['summary']['repayers_count'],
            self.summary['summary']['unique_addr_count'],
            "OVERALL",
            self.summary['summary']['depositors_count'],
            self.summary['summary']['borrowers_count'],
            self.summary['summary']['redeemers_count'],
            self.summary['summary']['repayers_count'],
            self.summary['summary']['unique_addr_count'],
        )
        logger.info(f"inserting overall stats")
        logger.info("%s,%s,%s,%s,%s,%s,%s,%s" % _val[:8])

        with connection.cursor() as cursor:
            cursor.execute(SQL_INSERT_OMM_STATS, _val)

        amount = self.getAmountSummary()

        for key, value in amount.items():
            _val = (
                self.index,
                timestamp,
                zero_if_none(value.get("deposit")),
                zero_if_none(value.get("borrow")),
                zero_if_none(value.get("redeem")),
                zero_if_none(value.get("repay")),
                key,
                zero_if_none(value.get("deposit")),
                zero_if_none(value.get("borrow")),
                zero_if_none(value.get("redeem")),
                zero_if_none(value.get("repay")),
            )
            logger.info(f"...inserting {key} amount...")
            logger.info("%s,%s,%s,%s,%s,%s,%s" % _val[:7])

            with connection.cursor() as cursor:
                cursor.execute(SQL_INSERT_TXN_AMOUNT, _val)

    def save(self):
        timestamp = self.end_timestamp // 1_000_000
        self._save_reserve_txns(timestamp)

        with open(f"{timestamp}_users_info.json", "w") as outfile:
            logger.info("... Saving users info json ...")
            json.dump(self.summary, outfile)

    def getSummary(self):
        return self.data.getSummary()

    def getAmountSummary(self):
        return self.data.getAmountSummary()

def _get_prev_timestamp() -> int:
    with connection.cursor() as cursor:
        cursor.execute("select `timestamp` from timestamp_history where _key=%s", (KEY,))
        value = cursor.fetchone()
        return value['timestamp'];

if __name__ == "__main__":
    with connection:
        prev_timestamp = _get_prev_timestamp() // US_PER_HR * US_PER_HR
        current_timestamp = int(datetime.timestamp(datetime.now()) * 1_000_000)

        # # to get data between timestamps
        # prev_timestamp = 1641297625_000_000 // US_PER_HR * US_PER_HR
        # current_timestamp = 1641304819_000_000

        ts = current_timestamp // US_PER_HR * US_PER_HR
        for i in range(prev_timestamp, current_timestamp, US_PER_HR):
            index = i // US_PER_HR
            starting_timestamp = i
            ending_timestamp = i + US_PER_HR
            analytics = OMMAnalytics(index, starting_timestamp, ending_timestamp)
            analytics.fetch()
            analytics.save()

        _val = (analytics.timestamp, KEY, )
        logger.info("...Updating last update timestamp...")
        with connection.cursor() as cursor:
            cursor.execute(SQL_UPDATE_PREV_TIMESTAMP, _val)
        connection.commit()
