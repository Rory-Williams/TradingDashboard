#### import external classes
import pandas as pd
import matplotlib.pyplot as plt
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly
import plotly.graph_objects as go
import plotly.subplots
# import pandas as pd
from ta.trend import MACD
from ta.momentum import StochasticOscillator
import plotly.express as px
import datetime
from itertools import repeat
import time


#### import local classes
from DataframeClass import TradingData

import sys
sys.path.insert(1, 'dashboardFunctions')
from dashboardFunctions import CollatedDashboardCallbacks


#### setup dataframe class
csv_path = 'C:/Users/rory1/PycharmProjects/CryptoBots/BTC_Price_History_Binance/BTCUSDT-1h-PriceHistoryCollatedFull.csv'
initial_slice = 500
TradingDf = TradingData(csv_path, initial_slice)
StratTradingDf = TradingData(csv_path, 0)


##################### DASH APP VIEW ####################################
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    html.H1('BTC vs USDT', style={'padding': '20px'}),

    html.Div(className="row radio-group", children=[
        html.Div(className="col-sm-12", children=[
            html.H4('Select timeframe for analysis:' ),
            dbc.RadioItems(
                id="data_timeunit",
                className="btn-group",
                inputClassName="btn-check",
                labelClassName="btn btn-outline-primary",
                labelCheckedClassName="active",
                options=[
                    {"label": "Hours", "value": "H"},
                    {"label": "Days", "value": "D"},
                    {"label": "Weeks", "value": "W"},
                    {"label": "Months", "value": "M"},
                ],
                value="H"
            )],
         )],
     style={'padding': '5px', 'display': 'inline'}),

    #  DATA RANGE    DATA RANGE    DATA RANGE    DATA RANGE    DATA RANGE    DATA RANGE    DATA RANGE    DATA RANGE
    html.Div(className='row', children=[
        html.Div(className='col-sm-4', children=[
            html.H4('Select number of hours of data to show (0 for all data):' ),
            dcc.Input(
                    id="df_num_hours", type="number",
                    debounce=True, placeholder="Num hours of data",
                    value=initial_slice, style={'margin': '20px'},
                ),
        ], style={'padding': '5px', 'display': 'inline'}),

        html.Div(className='col-sm-8', children=[
            html.H4('Edit data range:'),
            dcc.RangeSlider(
                min=TradingDf.df.index[0],
                max=TradingDf.df.index[-1],
                value=[TradingDf.df.index[0], TradingDf.df.index[-1]],
                marks=TradingDf.date_dict,
                pushable=True,
                id='timeframe-slider',
            ),
        ], style={}),
    ], style={'width': '100%', 'margin-bottom': '25px', 'padding': '10px'}),

    #  VIS RANGES    VIS RANGES    VIS RANGES    VIS RANGES    VIS RANGES    VIS RANGES    VIS RANGES    VIS RANGES    VIS RANGES
    html.Div(className='row', children=[
        html.Div(className='col-sm-4', children=[
            html.H4('Or select date range to check strategy:'),
            dcc.DatePickerRange(
                id='graph-date-range',
                display_format='Y-M-D',
                min_date_allowed=TradingDf.raw_df['Open time'].iloc[0],
                max_date_allowed=TradingDf.raw_df['Open time'].iloc[-1],
                start_date=TradingDf.raw_df['Open time'].iloc[-13559],
                end_date=TradingDf.raw_df['Open time'].iloc[-1],
                style={'padding': '5px'},
            ),
        ], style={'padding': '5px', 'display': 'inline'}),

        html.Div(className='col-sm-8', children=[
            html.H4('Edit visual data range:'),
            dcc.RangeSlider(
                min=TradingDf.df.index[0],
                max=TradingDf.df.index[-1],
                value=[TradingDf.df.index[0], TradingDf.df.index[-1]],
                marks=TradingDf.date_dict,
                pushable=True,
                id='visframe-slider'
            ),
        ], style={}),
    ], style={'width': '100%', 'margin-bottom': '25px', 'padding': '10px'}),

    #  SELECT TRADE TYPE    SELECT TRADE TYPE    SELECT TRADE TYPE    SELECT TRADE TYPE    SELECT TRADE TYPE    SELECT TRADE TYPE
    html.Div(className='col-sm-6', children=[
            html.H4('Select trade method:'),
            dcc.RadioItems(
                    id="graph_trade_method",
                    options=[
                        {"label": "MA", "value": "MA"},
                        {"label": "Wyckoff", "value": "Wyckoff"},
                    ],
                    inline=True,
                    labelStyle={'padding': '10px'},
                    value='MA',
                ),
        ], style={'padding': '5px', 'display': 'inline'}),
    #  MA GRAPH RANGE    MA GRAPH RANGE    MA GRAPH RANGE    MA GRAPH RANGE    MA GRAPH RANGE    MA GRAPH RANGE    MA GRAPH RANGE

    html.Div(children=[
        html.H4('Edit MA range (hrs):'),
        html.P('Moving average method:', style={'padding': '5px', 'display': 'inline'}),
        dcc.RadioItems(
                id="Graph_MA_method",
                options={
                    'Simple': 'Simple MA',
                    'EMA': 'EMA',
                    'MACD': 'MACD',
                },
                inline=True,
                labelStyle={'padding': '10px', 'display': 'inline'},
                value='Simple',
            ),
        html.P(children='Short MA:', style={'display': 'inline'}),
        dcc.Input(
                id="ma_short", type="number",
                debounce=True, placeholder="MA short in hrs",
                value=5, style={'margin': '20px'},
            ),
        html.P(children='Long MA:', style={'display': 'inline'}),
        dcc.Input(
                id="ma_long", type="number",
                debounce=True, placeholder="MA long in hrs",
                value=20, style={'margin': '20px'},
            ),
        html.P(children='Signal (MACD):', style={'display': 'inline'}),
        dcc.Input(
                id="ma_signal", type="number",
                debounce=True, placeholder="MA signal for MACD in hrs",
                value=9, style={'margin': '20px'},
            ),
        html.P(children='', style={'display': 'inline', 'padding': '20px'}),
        html.P(children='Input trade % fee:', style={'display': 'inline'}),
        dcc.Input(
                id="trade_pct_fee", type="number",
                debounce=True, placeholder="Trade pct fee",
                value=0.001, style={'margin': '20px'},
        ),
        html.Div(id="ma_profit_output", style={'display': 'inline'}),
    ], style={'display': 'inline', 'padding': '20px'}, id="graph_ma_inputs_div"),


#  WYCKOFF GRAPH INP    WYCKOFF GRAPH INP    WYCKOFF GRAPH INP    WYCKOFF GRAPH INP    WYCKOFF GRAPH INP    WYCKOFF GRAPH INP    WYCKOFF GRAPH INP

    html.Div(children=[
        html.H4('Wyckoff div'),
    ], style={'display': 'none', 'padding': '20px'}, id="graph_wy_inputs_div"),

    #  GRAPHING    GRAPHING    GRAPHING    GRAPHING    GRAPHING    GRAPHING    GRAPHING    GRAPHING    GRAPHING    GRAPHING    GRAPHING

    html.Div(className='row', children=[
        html.Div(className='col-sm-6', children=[
            html.H4('Extra graphs to show:'),
            dcc.Checklist(
                    id="checklist",
                    options=[
                        {"label": "Volume %", "value": "VolPct"},
                        {"label": "MACD", "value": "MACD"},
                        {"label": "Stochastic", "value": "Stoch"},
                    ],
                    inline=True,
                    labelStyle={'padding': '10px'},
                    value=[],
                ),
        ], style={'padding': '5px', 'display': 'inline'}),
        html.Div(className='col-sm-6', children=[
            html.H4('Graphs to overlay candle plot:'),
            dcc.RadioItems(
               id="graphOverlay",
               options={
                    'Vol': 'Volume',
                    'VolPct': 'Volume %',
                    'MACD': 'MACD',
                    'Stoch': 'Stochastic'
               },
               inline=True,
               labelStyle={'padding': '10px'},
               value='Vol',
            ),
        ], style={'padding': '5px', 'display': 'inline'}),
    ], style={'width': '100%', 'margin-bottom': '25px', 'padding': '10px'}),
    dcc.Graph(id="graph", config={"scrollZoom": True}),
    html.Div(id='hidden-div', style={'display': 'none'}),

    #  DATA TABLE    DATA TABLE    DATA TABLE    DATA TABLE    DATA TABLE    DATA TABLE    DATA TABLE    DATA TABLE    DATA TABLE
    html.Div(className='row', id='data_table_div', children=[
        dash_table.DataTable(
            id='raw_trading_df',
            # data=TradingDf.df.to_dict('records'),
            # columns=[{'id': c, 'name': c} for c in TradingDf.df.columns],
            page_action='none',
            style_table={'height': '300px', 'overflowY': 'auto'}
        ),
    ], style={'width': '100%', 'margin-bottom': '25px', 'padding': '10px'}),
    html.Br(),
    html.Div(className='row', id='data_table_div2', children=[
        dash_table.DataTable(
            id='transaction_trading_df',
            # data=TradingDf.transaction_df.to_dict('records'),
            # columns=[{'id': c, 'name': c} for c in TradingDf.transaction_df.columns],
            page_action='none',
            style_table={'height': '300px', 'overflowY': 'auto'}
        ),
    ], style={'width': '100%', 'margin-bottom': '25px', 'padding': '10px'}),

    #  STRAT TESTING     STRAT TESTING     STRAT TESTING     STRAT TESTING     STRAT TESTING     STRAT TESTING     STRAT TESTING
    html.H2('Setup Strategy'),
    html.Div(children=[
        #  Date range picker    Date range picker    Date range picker
        html.Div(children=[
            html.H4('Date range to check strategy:', style={'padding': '5px', 'grid-column': '1', 'grid-row': '0'}),
            dcc.DatePickerRange(
                id='strat-date-range',
                display_format='Y-M-D',
                # min_date_allowed=time.mktime(df['Open time'].iloc[0].timetuple()),
                # max_date_allowed=time.mktime(df['Open time'].iloc[-1].timetuple()),
                # start_date=time.mktime(df['Open time'].iloc[0].timetuple()),
                # end_date=time.mktime(df['Open time'].iloc[-1].timetuple())
                min_date_allowed=StratTradingDf.raw_df['Open time'].iloc[0],
                max_date_allowed=StratTradingDf.raw_df['Open time'].iloc[-1],
                start_date=StratTradingDf.raw_df['Open time'].iloc[-13559],
                end_date=StratTradingDf.raw_df['Open time'].iloc[-1],
                style={'padding': '5px', 'grid-column': '2', 'grid-row': '1'},
            ),
            html.P(style={'padding': '5px', 'grid-column-start': '4', 'grid-column-end': '12', 'grid-row': '0'}),
        ], style={'display': 'grid', 'width': '100%', 'margin-bottom': '5px'}),

        #  Strat input picker    Strat input picker    Strat input picker    Strat input picker    Strat input picker    Strat input picker
        html.Div(children=[
            html.P('Strategy methods to include:', style={'padding': '5px', 'grid-column': '1', 'grid-row': '1'}),
            html.P('MA methods to try:', style={'padding': '5px', 'grid-column': '2', 'grid-row': '1'}),
            dcc.Checklist(
               id="MA_method",
               options=[
                    {"label": "Simple MA", "value": "Simple"},
                    {"label": "EMA", "value": "EMA"},
                    {"label": "MACD", "value": "MACD"},
               ],
               inline=True,
               labelStyle={'padding': '10px', 'grid-column': '3', 'grid-row': '1'},
               value=['Simple'],
            ),
            html.P('Other additional methods:', style={'padding': '5px', 'grid-column': '4', 'grid-row': '1'}),
            dcc.Checklist(
                id="strat_checklist",
                options=[
                    {"label": "Stochastic", "value": "Stoch"},
                    {"label": "Stop Loss", "value": "StopLoss"},
                    {"label": "Trading Volume", "value": "TradeVol"},
                ],
                inline=True,
                labelStyle={'padding': '10px', 'grid-column': '5', 'grid-row': '1'},
                value=[],
            ),
            html.P(style={'padding': '5px', 'grid-column-start': '6', 'grid-column-end': '7', 'grid-row': '1'}),
        ], style={'display': 'grid', 'width': '100%', 'margin-bottom': '5px'}),

        #  % trade fee    % trade fee    % trade fee    % trade fee    % trade fee    % trade fee    % trade fee    % trade fee
        html.Div(children=[
            html.P('Trade cost (%):', style={'padding': '5px', 'grid-column': '1', 'grid-row': '1'}),
            dcc.Input(
                id="trade_cost_pct", type="number",
                debounce=True, placeholder="Trade Cost %",
                value=0.001, style={'margin': '10px', 'grid-column': '2', 'grid-row': '1'},
            ),
            html.P(style={'padding': '5px', 'grid-column-start': '3', 'grid-column-end': '12', 'grid-row': '1'}),
        ], style={'display': 'grid', 'gap': '10px', 'width': '100%', 'margin-bottom': '25px'}),


        #  MA range picker    MA range picker    MA range picker    MA range picker    MA range picker    MA range picker
        html.Div(id='ma_div', children=[
            html.H4('MA Inputs:', style={'padding': '5px', 'grid-column': '1', 'grid-row': '1'}),
            html.P('Range Start', style={'padding': '5px', 'grid-column': '2', 'grid-row': '1'}),
            html.P('Range End', style={'padding': '5px', 'grid-column': '3', 'grid-row': '1'}),
            html.P('Range Interval', style={'padding': '5px', 'grid-column': '4', 'grid-row': '1'}),
            html.P('MACD Signal', style={'padding': '5px', 'grid-column': '5', 'grid-row': '1'}),
            html.P('Short MA range to check:', style={'padding': '5px', 'grid-column': '1', 'grid-row': '2'}),
            dcc.Input(
                    id="ma_short_start", type="number",
                    debounce=True, placeholder="MA short range start",
                    value=5, style={'margin': '10px', 'grid-column': '2', 'grid-row': '2'},
                ),
            dcc.Input(
                    id="ma_short_end", type="number",
                    debounce=True, placeholder="MA short range end",
                    value=10, style={'margin': '10px', 'grid-column': '3', 'grid-row': '2'},
                ),
            dcc.Input(
                    id="ma_short_interval", type="number",
                    debounce=True, placeholder="MA short range interval",
                    value=5, style={'margin': '10px', 'grid-column': '4', 'grid-row': '2'},
                ),
            dcc.Input(
                    id="macd_signal", type="number",
                    debounce=True, placeholder="MA short range interval",
                    value=9, style={'margin': '10px', 'grid-column': '5', 'grid-row': '2'},
                ),
            html.Br(),
            html.P('Long MA range to check:', style={'padding': '5px', 'grid-column': '1', 'grid-row': '3'}),
            dcc.Input(
                id="ma_long_start", type="number",
                debounce=True, placeholder="MA long range start",
                value=100, style={'margin': '10px', 'grid-column': '2', 'grid-row': '3'},
            ),
            dcc.Input(
                id="ma_long_end", type="number",
                debounce=True, placeholder="MA long range end",
                value=200, style={'margin': '10px', 'grid-column': '3', 'grid-row': '3'},
            ),
            dcc.Input(
                id="ma_long_interval", type="number",
                debounce=True, placeholder="MA long range interval",
                value=20, style={'margin': '10px', 'grid-column': '4', 'grid-row': '3'},
            ),
            html.P(style={'padding': '5px', 'grid-column-start': '3', 'grid-column-end': '12', 'grid-row': '1'}),
        ], style={'display': 'grid', 'gap': '10px', 'width': '100%', 'margin-bottom': '25px'}),


        #  Stop loss picker    Stop loss picker    Stop loss picker    Stop loss picker    Stop loss picker    Stop loss picker
        html.Div(id='stoploss_div', children=[
            html.H4('Stop loss Inputs:', style={'padding': '5px', 'grid-column': '1', 'grid-row': '1'}),
            dcc.RadioItems(
               id="stoploss_radio",
               options={
                    'BuyPrice': 'From Buy Price',
                    'TrailingPrice': 'Trailing Price',
               },
               inline=True,
               labelStyle={'padding': '10px', 'grid-column': '1', 'grid-row': '2'},
               value='BuyPrice',
            ),
            html.P('Stop loss % range start', style={'padding': '5px', 'grid-column': '1', 'grid-row': '3'}),
            html.P('Stop loss % range int', style={'padding': '5px', 'grid-column': '1', 'grid-row': '4'}),
            html.P('Stop loss % range end', style={'padding': '5px', 'grid-column': '1', 'grid-row': '5'}),
            dcc.Input(
                    id="stoploss_start", type="number",
                    debounce=True, placeholder="Stop loss % range start",
                    value=0.05, style={'margin': '10px', 'grid-column': '2', 'grid-row': '3'},
                ),
            dcc.Input(
                    id="stoploss_int", type="number",
                    debounce=True, placeholder="Stop loss % range start",
                    value=0.01, style={'margin': '10px', 'grid-column': '2', 'grid-row': '4'},
                ),
            dcc.Input(
                    id="stoploss_end", type="number",
                    debounce=True, placeholder="Stop loss % range end",
                    value=0.1, style={'margin': '10px', 'grid-column': '2', 'grid-row': '5'},
                ),
            html.P(style={'padding': '5px', 'grid-column-start': '3', 'grid-column-end': '12', 'grid-row': '5'}),
        ], style={'display': 'grid', 'gap': '10px', 'width': '100%', 'margin-bottom': '25px'}),


        #  Strat results output    Strat results output    Strat results output    Strat results output    Strat results output    Strat results output
        html.Div(children=[
            html.H4('Results:', style={'padding': '5px', 'grid-column': '1', 'grid-row': '1'}),
            html.H4(children="Status: LOADING", id="strat_status", style={'margin': '10px', 'grid-column': '2', 'grid-row': '1'}),
            html.P(children="Pct profit:", id="ma_rng_profit_output", style={'margin': '10px', 'grid-column': '1', 'grid-row': '2'}),
            html.P(children="Best timeframe:", id="ma_rng_timeframe_output", style={'margin': '10px', 'grid-column': '1', 'grid-row': '3'}),
            html.P(children="Best MA type:", id="ma_rng_matype_output", style={'margin': '10px', 'grid-column': '1', 'grid-row': '4'}),
            html.P(children="Best S_MA:", id="ma_rng_sma_output", style={'margin': '10px', 'grid-column': '1', 'grid-row': '5'}),
            html.P(children="Best L_MA:", id="ma_rng_lma_output", style={'margin': '10px', 'grid-column': '1', 'grid-row': '6'}),
            html.P(children="Timeframe length [hrs]:", id="ma_rng_timelen_output", style={'margin': '10px', 'grid-column': '1', 'grid-row': '7'}),
            html.P(children="Num trades:", id="ma_rng_numtrades_output", style={'margin': '10px', 'grid-column': '1', 'grid-row': '8'}),

            html.P(style={'padding': '5px', 'grid-column-start': '3', 'grid-column-end': '12', 'grid-row': '1'}),
        ], style={'display': 'grid', 'gap': '10px', 'width': '100%', 'margin-bottom': '25px'}),

    ], style={'width': '100%'}),
    html.P(id="dead_p_tag1", children="", style={'height': '200px', 'width': '100%', 'display': 'none'}),
    dcc.Store(
            id='strat_data_store',
            storage_type='local',
            data={},
    ),
], style={'justify-content': 'center', 'align-items': 'center', 'text-align': 'center'})

CollatedDashboardCallbacks.get_callbacks(app, TradingDf, StratTradingDf)

app.run_server(debug=True)












