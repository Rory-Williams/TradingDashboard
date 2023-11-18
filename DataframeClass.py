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
from math import ceil
from itertools import combinations

pd.options.mode.chained_assignment = None
pd.options.mode.copy_on_write = True

class TradingData:
    def __init__(self, csv_path: str, initial_slice: int):
        self.raw_df = pd.read_csv(csv_path, header=None, index_col=False)
        self.columns = ['Open time', 'Open', 'High', 'Low', 'Close',
           'Volume', 'Close time', 'Quote asset volume', 'Number of trades',
           'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']
        self.raw_df.columns = self.columns
        self.data_timeunit = ''  # used to determine data timeunit (H = hours, D = days, W = weeks)
        self.raw_df['Open time'] = pd.to_datetime(self.raw_df['Open time'], unit='ms')
        self.raw_df['Open time'] = self.raw_df['Open time'].apply(lambda dt: dt.replace(second=0, microsecond=0, minute=0))  # clean data by fixing hr times to 0
        self.raw_df.loc[:, 'Taker buy base asset volume pct'] = self.raw_df['Taker buy base asset volume'] / self.raw_df['Volume']
        self.slice_df('H', start_date=self.raw_df['Open time'].iloc[-initial_slice], end_date=self.raw_df['Open time'].iloc[-1])
        self.transaction_df = pd.DataFrame()



    def slice_df(self, data_timeunit: str, start_date, end_date):
        '''take a slice from the raw df data to use, with timeunit defined as (H/D/W)
        Also generate a datelist string.'''

        # initially convert dataframe to correct time unit
        if data_timeunit != self.data_timeunit:
            conversion = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum',
                          'Close time': 'last', 'Quote asset volume': 'sum', 'Number of trades': 'sum',
                          'Taker buy base asset volume': 'sum', 'Taker buy quote asset volume': 'sum', 'Ignore': 'min'}
            self.df = self.raw_df.copy()
            self.df.set_index('Open time', inplace=True)
            self.df = self.df.resample(data_timeunit).agg(conversion)
            self.df.reset_index(level=0, inplace=True)
            self.df.loc[:, 'Taker buy base asset volume pct'] = self.df['Taker buy base asset volume'] / self.df['Volume']
            self.df_length = len(self.df.index)
            self.raw_df_conv = self.df.copy()  # used to specify indexs outside of
            self.data_timeunit = data_timeunit  # set new data_timeunit
            # print('head', self.df.head())

        # print('cleaned start/end dates:', start_date, end_date)

        # Calculate absolute differences
        self.raw_df_conv['Start_Date_Diff'] = (self.raw_df_conv['Open time'] - start_date).abs()
        start_idx = self.raw_df_conv['Start_Date_Diff'].idxmin()
        self.raw_df_conv['End_Date_Diff'] = (self.raw_df_conv['Open time'] - end_date).abs()
        end_idx = self.raw_df_conv['End_Date_Diff'].idxmin()

        # print('df idxs:', start_idx, end_idx)
        self.df = self.raw_df_conv.loc[start_idx:end_idx]
        self.df_temp = self.df.copy()  # used for visual slider limit retention

        # setup timeline label values
        self.date_dict = {}  # dictionary of index vals and associated dates
        self.date_idxs = []
        if data_timeunit == 'D' or data_timeunit == 'H':
            date_str_to_search = '%d/%m/%y'
        else:
            date_str_to_search = '%m/%y'

        # list of unique day dates e.g. 09/05
        self.datelist = self.df['Open time'].dt.strftime(date_str_to_search).unique()
        # print('len datelist:', len(self.datelist))
        # print('last val:', self.datelist[-1])

        num_labels = 20
        if len(self.datelist) > num_labels:
            interval = ceil(len(self.datelist)/num_labels)
            self.datelist = self.datelist[::interval]

        for date in self.datelist:
            date_index = self.df[self.df['Open time'].dt.strftime(date_str_to_search) == date].index[0]
            self.date_idxs.append(date_index)
            self.date_dict[str(date_index)] = date  # used to store timeline labels against indexs

    def check_wyckoff(self, volume_ma, vol_diff_ma, wy_vol_max_slope_period,
                      price_ma_window, price_slope_period, price_slope_ma, price_slope_peak_delta, accum_time):
        # Define parameters for Wyckoff accumulation detection
        price_threshold = 0
        volume_threshold = 0
        # min_time_in_accumulation = 5  # Minimum number of days for an accumulation phase

        # Calculate daily price and volume changes
        # if 'Price Slope' not in self.df.columns:  # add in thing to prevent constant update
        self.df['Price ma'] = self.df['Close'].rolling(price_ma_window).mean()
        self.df['Price Slope pct'] = (self.df['Close'] - self.df['Open'].shift(price_slope_period)) / (self.df['Close'])
        self.df['Price Slope pct roll mean'] = self.df['Price Slope pct'].rolling(price_slope_ma).mean()


        # taker_buy_base_asset_volume = maker_sell_base_asset_volume
        # taker_sell_base_asset_volume = maker_buy_base_asset_volume
        # total_volume = taker_buy_base_asset_volume + taker_sell_base_asset_volume = maker_buy_base_asset_volume + maker_sell_base_asset_volume

        self.df['Volume ma'] = self.df['Volume'].rolling(volume_ma).mean()
        self.df.loc[
            self.df['Taker buy base asset volume'] >= self.df['Volume']/2, 'Volume Pct Variation'  # strong buy
        ] = (self.df['Volume'] - self.df['Volume ma'])/self.df['Volume ma']
        self.df.loc[
            self.df['Taker buy base asset volume'] < self.df['Volume'] / 2, 'Volume Pct Variation'  # strong sell
        ] = (self.df['Volume ma'] - self.df['Volume']) / self.df['Volume ma']
        self.df['Vol diff pct roll mean'] = self.df['Volume Pct Variation'].rolling(vol_diff_ma).mean()
        self.df['Vol Rolling future peak pct'] = self.df['Vol diff pct roll mean'].shift(wy_vol_max_slope_period).rolling(wy_vol_max_slope_period).max()


        # define accumulation stage as when short price gradient over certain period has a min/max diff of certain value
        # and the average price for period after does not go outside certain value
        price_slope_change_range_window = 5
        def peak_diff_func(series):
            series = series.values.tolist()
            largest_diff_with_sign = max([(b - a) for a, b in combinations(series, 2)], key=lambda x: (abs(x), x))  # find largest
            return largest_diff_with_sign

        self.df['Price Slope peak delta'] = self.df['Price Slope pct'].rolling(price_slope_change_range_window).apply(peak_diff_func)
        try:
            self.df.drop(['Accum_Price_Slope_Check'], axis=1, inplace=True)  # remove previous crossing data
        except:
            pass  # column doesnt exist

        # define accumulation phase
        self.df.loc[(self.df['Price Slope peak delta'] > price_slope_peak_delta) &
                    (self.df['Vol Rolling future peak pct'] > 0),
                    'Accum_Price_Slope_Check'] = 0




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
            # self.macd_diff = macd_diff(close=self.df.loc[:, 'Close'], window_fast=short_ma, window_slow=long_ma, window_sign=signal_ma)
            self.df.loc[:, 'MA_Long'] = macd_signal(close=self.df.loc[:, 'Close'], window_fast=short_ma, window_slow=long_ma, window_sign=signal_ma)

        elif ma_method == 'EMA':
            self.df.loc[:, 'MA_Short'] = ema_indicator(close=self.df.loc[:, 'Close'], window=short_ma)
            self.df.loc[:, 'MA_Long'] = ema_indicator(close=self.df.loc[:, 'Close'], window=long_ma)

        else:  # (simple method default)
            self.df.loc[:, 'MA_Short'] = sma_indicator(close=self.df.loc[:, 'Close'], window=short_ma)
            self.df.loc[:, 'MA_Long'] = sma_indicator(close=self.df.loc[:, 'Close'], window=long_ma)

        previous_short = self.df['MA_Short'].shift(1)
        previous_long = self.df['MA_Long'].shift(1)

        # create and assign crossings in new transaction column
        self.df.loc[(self.df['MA_Short'] >= self.df['MA_Long']) & (previous_short <= previous_long), 'transactions'] = 'Pos Cross'
        self.df.loc[(self.df['MA_Short'] <= self.df['MA_Long']) & (previous_short >= previous_long), 'transactions'] = 'Neg Cross'


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
        if len(buy_crossing.index) > 0 and len(sell_crossing.index) > 0:
            if len(buy_crossing) > len(sell_crossing):  # drop last row of buy for equal trades
                buy_crossing.drop(buy_crossing.tail(1).index, inplace=True)
            elif len(buy_crossing) < len(sell_crossing):  # drop first row of sell for equal trade
                sell_crossing.drop(sell_crossing.head(1).index, inplace=True)
            elif sell_crossing['Open time'].iloc[0] < buy_crossing['Open time'].iloc[0]:  # drop both rows to reorder trades
                buy_crossing.drop(buy_crossing.tail(1).index, inplace=True)
                sell_crossing.drop(sell_crossing.head(1).index, inplace=True)
        else:
            buy_crossing = pd.DataFrame(0, index=[0], columns=self.df.columns)
            sell_crossing = buy_crossing
            # print('df trans:', buy_crossing, sell_crossing)

        # make buy and sell same length
        sell_crossing_df = sell_crossing.add_prefix("Sell_")
        buy_crossing_df = buy_crossing.add_prefix("Buy_")
        sell_crossing_df = sell_crossing_df.reset_index(drop=True)  # reset index for comparisons
        buy_crossing_df = buy_crossing_df.reset_index(drop=True)
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

                    if s_ma < l_ma and l_ma < len(self.df.index):
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




