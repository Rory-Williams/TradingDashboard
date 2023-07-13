import pandas as pd
import matplotlib.pyplot as plt
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly
import plotly.graph_objects as go
import plotly.subplots
# import pandas as pd
from ta.trend import macd, macd_diff, macd_signal, ema_indicator, sma_indicator
from ta.momentum import StochasticOscillator
import plotly.express as px
import datetime
from itertools import repeat
import time
import numpy as np

pd.options.mode.chained_assignment = None

class TradingData:
    def __init__(self, csv_path: str, initial_slice: int):
        self.raw_df = pd.read_csv(csv_path, header=None, index_col=False)
        self.columns = ['Open time', 'Open', 'High', 'Low', 'Close',
           'Volume', 'Close time', 'Quote asset volume', 'Number of trades',
           'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']
        self.raw_df.columns = self.columns
        # print(self.raw_df.head())
        self.raw_df['Open time'] = pd.to_datetime(self.raw_df['Open time'], unit='ms')
        self.raw_df.loc[:, 'Taker buy base asset volume pct'] = self.raw_df['Taker buy base asset volume'] / self.raw_df['Volume']
        self.num_for_str_months = 4000
        self.num_for_str_days = 50
        self.slice_df(initial_slice)

    def slice_df(self, num_vals: int):
        '''take a slice from the raw df data to use
        Also generate a datelist string'''
        if num_vals == 0:
            self.df = self.raw_df
        else:
            self.df = self.raw_df.iloc[-num_vals:]

        self.date_dict = {}  # dictionary of index vals and associated dates
        self.date_idxs = []
        if len(self.df) > self.num_for_str_months:
            date_str_to_search = '%m'
        elif len(self.df) < self.num_for_str_days:
            date_str_to_search = '%h/%d/%m'
        else:
            date_str_to_search = '%d/%m'

        # list of unique day dates e.g. 09/05
        self.datelist = self.df['Open time'].dt.strftime(date_str_to_search).unique()
        if len(self.datelist) > 30:
            self.datelist = self.datelist[::4]
            print(f'datelist: {self.datelist}')

        for date in self.datelist:
            date_index = self.df[self.df['Open time'].dt.strftime(date_str_to_search) == date].index[0]
            self.date_idxs.append(date_index)
            self.date_dict[str(date_index)] = date


    def update_df_ma(self, ma_method: str, short_ma: int, long_ma: int, trade_cost_pct: float, **kwargs):
        '''updates the rolling average columns in the self.df and buy columns when crosses
        Returns df, self.transaction_df'''
        if kwargs['signal_ma']:
            signal_ma = kwargs['signal_ma']
        if kwargs['trade_strat_dict']:
            trade_strat_dict = kwargs['trade_strat_dict']  # contains info on stoploss, stoch, volpct trade strategy methods
        else:
            trade_strat_dict = {}

        if ma_method == 'MACD':
            # print('MACD selected')
            self.df.loc[:, 'MA_Short'] = macd(close=self.df.loc[:, 'Close'], window_fast=short_ma, window_slow=long_ma)
            self.macd_diff = macd_diff(close=self.df.loc[:, 'Close'], window_fast=short_ma, window_slow=long_ma, window_sign=signal_ma)
            self.df.loc[:, 'MA_Long'] = macd_signal(close=self.df.loc[:, 'Close'], window_fast=short_ma, window_slow=long_ma, window_sign=signal_ma)

        elif ma_method == 'EMA':
            # print('EMA selected')
            # short_multiplier = 2 / (short_ma+1)
            # long_multiplier = 2 / (long_ma + 1)
            # self.df.loc[:, 'MA_Short'] = self.df.loc[:, 'Close'].rolling(short_ma).mean()
            # self.df.loc[:, 'MA_Long'] = self.df.loc[:, 'Close'].rolling(long_ma).mean()
            # # EMA: {Close - EMA(previous day)} x multiplier + EMA(previous day).
            # for i in range(short_ma, len(self.df)):
            #     self.df['MA_Short'].iloc[i] = self.df['Close'].iloc[i] * short_multiplier + (1 - short_multiplier) * \
            #                              self.df['MA_Short'].iloc[i - 1]
            # for i in range(long_ma, len(self.df)):
            #     self.df['MA_Long'].iloc[i] = self.df['Close'].iloc[i] * long_multiplier + (1 - long_multiplier) * \
            #                                   self.df['MA_Long'].iloc[i - 1]

            self.df.loc[:, 'MA_Short'] = ema_indicator(close=self.df.loc[:, 'Close'], window=short_ma)
            self.df.loc[:, 'MA_Long'] = ema_indicator(close=self.df.loc[:, 'Close'], window=long_ma)

        else:  # (simple method default)
            # create simple rolling mean and shifted value columns to later find gradients
            # print('SIMPLE selected')
            # self.df.loc[:, 'MA_Short'] = self.df.loc[:, 'Close'].rolling(short_ma).mean()
            # self.df.loc[:, 'MA_Long'] = self.df.loc[:, 'Close'].rolling(long_ma).mean()
            self.df.loc[:, 'MA_Short'] = sma_indicator(close=self.df.loc[:, 'Close'], window=short_ma)
            self.df.loc[:, 'MA_Long'] = sma_indicator(close=self.df.loc[:, 'Close'], window=long_ma)

        previous_short = self.df['MA_Short'].shift(1)
        previous_long = self.df['MA_Long'].shift(1)

        # create and assign crossings in new transaction column
        self.df.loc[(self.df['EMA_Short'] >= self.df['EMA_Long']) & (previous_short <= previous_long), 'transactions'] = 'Pos Cross'
        self.df.loc[(self.df['EMA_Short'] <= self.df['EMA_Long']) & (previous_short >= previous_long), 'transactions'] = 'Neg Cross'


        if len(trade_strat_dict) > 0:  # running with stop loss
            buyprice = 0
            style = trade_strat_dict['stoploss_type']
            for stoploss in range(trade_strat_dict['stoploss_start'],trade_strat_dict['stoploss_end'],trade_strat_dict['stoploss_int']):
                record_sales = False  # used to eliminate other sell signals
                for row in self.df.itertuples():
                    # find stop loss points. Only check if have previously bought
                    # check if should be recording negative crosses (only want to record a sell if ar in bough position)
                    # update any sales records from stop losses
                    if record_sales:
                        if row[-1] == 'Neg Cross':
                            record_sales = False
                        elif style == 'BuyPrice':
                            if row[5] < buyprice * (1 - stoploss):
                                self.df.loc[row[0], 'transactions'] = 'Stoploss'
                                record_sales = False
                        elif style == 'TrailingPrice':
                            if row[5] <= buyprice:
                                self.df.loc[row[0], 'transactions'] = 'Trail Stoploss'
                                record_sales = False

                    # check if updating record signal, else delete any crossing points
                    else:
                        if row[-1] == 'Pos Cross':
                            record_sales = True
                        elif row[-1] == 'Neg Cross':  # replace any existing crossings as ignoring sells
                            self.df.loc[row[0], 'transactions'] = np.nan

                    # update trailing buy prices
                    if style == 'BuyPrice':
                        if row[-1] == 'Pos Cross':  # buy so update buyprice
                            buyprice = row[5]
                    elif style == 'TrailingPrice':
                        if row[5] * (1 - stoploss) > buyprice:
                            buyprice = (1 - stoploss) * row[5]

        buy_crossing = self.df[self.df['transactions'] == 'Pos Cross']
        sell_crossing = self.df[(self.df['transactions'].notnull()) & (self.df['transactions'] != 'Pos Cross')]
        if len(buy_crossing) > len(sell_crossing):  # drop last row if buy
            buy_crossing = buy_crossing.iloc[:-1]

        sell_crossing_df = sell_crossing.add_prefix("Sell_")
        buy_crossing_df = buy_crossing.add_prefix("Buy_")
        sell_crossing_df = sell_crossing_df.reset_index(drop=True)  # reset index for comparisons
        buy_crossing_df = buy_crossing_df.reset_index(drop=True)

        #
        # # get dataframes to same size to concatinate, with buy first
        # if len(sell_crossing_df) > len(buy_crossing_df):
        #     sell_crossing_df.drop(index=sell_crossing_df.index[0], axis=0, inplace=True)
        # elif len(sell_crossing_df) < len(buy_crossing_df):
        #     buy_crossing_df.drop(index=buy_crossing_df.index[-1], axis=0, inplace=True)
        # sell_crossing_df = sell_crossing_df.reset_index(drop=True)  # reset index for comparisons
        # buy_crossing_df = buy_crossing_df.reset_index(drop=True)
        # sell_crossing_df = sell_crossing_df.add_prefix("Sell_")
        # buy_crossing_df = buy_crossing_df.add_prefix("Buy_")

        # concatinate and store in transaction df for use
        self.transaction_df = pd.concat([buy_crossing_df, sell_crossing_df], axis=1)
        self.transaction_df['Pct_profit'] = self.transaction_df['Sell_Close'] / self.transaction_df['Buy_Close']
        self.transaction_df['Pct_profit'] = self.transaction_df['Pct_profit'] - trade_cost_pct
        self.transaction_df['Pct_profit_cum'] = self.transaction_df['Pct_profit'].cumprod()
        # print(f'trans df: {self.transaction_df.tail()}')
        # print(f'profit pct: {self.transaction_df.Pct_profit_cum.iloc[-1]}')  # total cumulative profit pct
        # self.transaction_df.to_csv('Orders.csv', index=False)  # UNCOMMENT TO PRINT TRANSACTION DATA


    def check_ma_range(self, ma_types: list, short_ma_range: list, long_ma_range: list, trade_cost_pct: float, **kwargs):
        '''return df of ma profit for ranges of short and long ma.
        input as 3 item lists of start, end and interval'''
        timeframe_len = len(self.df)
        start_date = datetime.datetime.strftime(self.df['Open time'].iloc[0], "%Y-%m-%d")
        end_date = datetime.datetime.strftime(self.df['Open time'].iloc[-1], "%Y-%m-%d")
        timeframe = f'{start_date} to {end_date}'

        trade_strat_dict = kwargs['trade_strat_dict']

        if kwargs['macd_signal']:
            macd_signal = kwargs['macd_signal']
        elif ma_types == 'MACD':
            macd_signal = 9  # default if not provided
        else:
            macd_signal = 'N/A'

        self.ma_profit_df = pd.DataFrame(
            columns=['timeframe', 'timeframe_len', 'MA_type', 's_ma', 'l_ma', 'Pct_Profit', 'Num_Trades', 'MACD signal'])

        s_ma_list = [*range(short_ma_range[0], short_ma_range[1], short_ma_range[2])]
        if short_ma_range[1] not in s_ma_list:  # add end value onto ma list if not there due to int value
            s_ma_list.append(short_ma_range[1])
        l_ma_list = [*range(long_ma_range[0], long_ma_range[1], long_ma_range[2])]
        if short_ma_range[1] not in s_ma_list:
            l_ma_list.append(long_ma_range[1])

        # MAIN LOOP TO CHECK TRADE STRAT RANGES
        for ma in ma_types:
            for s_ma in s_ma_list:
                for l_ma in l_ma_list:

                    self.update_df_ma(ma, s_ma, l_ma, trade_cost_pct, signal_ma=macd_signal, trade_strat_dict=trade_strat_dict)

                    num_trades = len(self.transaction_df)
                    if not num_trades:  # set final profit to 0 if no trades
                        final_profit_pct = 0
                    else:
                        final_profit_pct = self.transaction_df.Pct_profit_cum.iloc[-1]

                    if (  # add ma if not already in data frame. Likely useful when start to save dataframe
                            len(self.ma_profit_df.loc[
                                    (self.ma_profit_df['timeframe'] == timeframe) & (self.ma_profit_df['s_ma'] == s_ma) & (
                                            self.ma_profit_df['l_ma'] == l_ma) & (self.ma_profit_df['MA_type'] == ma)])
                    ) == 0:
                        self.ma_profit_df.loc[len(self.ma_profit_df.index)] = [timeframe, timeframe_len, ma, s_ma, l_ma,
                                                                       final_profit_pct,
                                                                       num_trades, macd_signal]




