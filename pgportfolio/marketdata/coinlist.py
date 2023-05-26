from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from pgportfolio.marketdata.poloniex import Poloniex
from pgportfolio.tools.data import get_chart_until_success
import pandas as pd
from datetime import datetime
import logging
from pgportfolio.constants import *


class CoinList(object):
    def __init__(self, end, volume_average_days=1, volume_forward=0):
        # instantiate a polo obj to request data using api
        self._polo = Poloniex()
        # getting the last 24hrs trading pair volumes
        vol = self._polo.marketVolume()
        # getting the curren ticker data for all coins
        ticker = self._polo.marketTicker()

        pairs = []
        coins = []
        volumes = []
        prices = []

        logging.info("select coin online from %s to %s" % (datetime.fromtimestamp(end - (DAY * volume_average_days) -
                                                                                  volume_forward).
                                                           strftime('%Y-%m-%d %H:%M'),
                                                           datetime.fromtimestamp(end - volume_forward).
                                                           strftime('%Y-%m-%d %H:%M')))
        for k, v in vol.items():
            if k.startswith("BTC_") or k.endswith("_BTC"):
                pairs.append(k)
                reversed_key = f"{k.split('_')[1]}_{k.split('_')[0]}"
                for c, val in v.items():
                    if c != 'BTC':
                        if k.endswith('_BTC'):
                            try:
                                # reverse the exchange from 'to BTC' to 'from BTC'
                                # (aka how much BTC it needs to exchange for the other coin)
                                prices.append(1.0 / float(ticker[k]['last']))
                                coins.append('reversed_' + c)
                            except KeyError:
                                prices.append(float(ticker[reversed_key]['last']))
                                coins.append('reversed_' + c)
                        else:
                            try:
                                # how much
                                prices.append(float(ticker[k]['last']))
                                coins.append(c)
                            except KeyError:
                                prices.append(1.0 / float(ticker[reversed_key]['last']))
                                coins.append(c)
                    else:
                        volumes.append(self.__get_total_volume(pair=k, global_end=end,
                                                               days=volume_average_days,
                                                               forward=volume_forward))
        self._df = pd.DataFrame({'coin': coins, 'pair': pairs, 'volume': volumes, 'price': prices})
        self._df = self._df.set_index('coin')

    @property
    def allActiveCoins(self):
        return self._df

    @property
    def allCoins(self):
        return self._polo.marketStatus().keys()

    @property
    def polo(self):
        return self._polo

    def get_chart_until_success(self, pair, start, period, end):
        return get_chart_until_success(self._polo, pair, start, period, end)

    # get several days volume
    def __get_total_volume(self, pair, global_end, days, forward):
        # DAY is a constant denoting how many seconds a day has
        start = global_end - (DAY * days) - forward     # getting the date (in UNIX time) of the start
        end = global_end - forward      # the forward variable is shifting the entire volume duration forward

        # requesting data
        chart = self.get_chart_until_success(pair=pair, period=DAY, start=start, end=end)
        result = 0
        for one_day in chart:
            if pair.startswith("BTC_"):
                result += float(one_day['volume'])
            else:
                result += float(one_day["quoteVolume"])
        return result

    def topNVolume(self, n=5, order=True, minVolume=0):
        if minVolume == 0:
            r = self._df.loc[self._df['price'] > 2e-6]
            r = r.sort_values(by='volume', ascending=False)[:n]
            print(r)
            if order:
                return r
            else:
                return r.sort_index()
        else:
            return self._df[self._df.volume >= minVolume]
