import pandas as pd
import matplotlib.pyplot as plt
from dash import Dash, dcc, html, Input, Output, State
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


def hour_rounder(t):
    # Rounds to nearest hour by adding a timedelta hour if minute >= 30
    return (t.replace(second=0, microsecond=0, minute=0, hour=t.hour)
               +datetime.timedelta(hours=t.minute//30))

def get_callbacks(app, TradingDf, StratTradingDf):

    @app.callback([Output('strat_status', 'children'),
                  Output('strat_data_store', 'data'),
                  Output('stoploss_div', 'style')],
                  [Input('MA_method', 'value'),
                   Input('strat_checklist', 'value'),
                   Input('strat-date-range', 'start_date'), Input('strat-date-range', 'end_date'),
                   Input('ma_short_start', 'value'), Input('ma_short_end', 'value'), Input('ma_short_interval', 'value'),
                   Input('ma_long_start', 'value'), Input('ma_long_end', 'value'), Input('ma_long_interval', 'value'),
                   Input('macd_signal', 'value'),
                   Input(component_id='trade_cost_pct', component_property='value'),
                   Input('stoploss_radio', 'value'), Input('stoploss_start', 'value'), Input('stoploss_int', 'value'), Input('stoploss_end', 'value'),
                   ],
                  )
    def update_trade_stat_status_info(ma_method, strat_checklist, start_date, end_date, short_start, short_end,
                                      short_int, long_start, long_end, long_int, macd_signal, trade_cost_pct, stoploss_type,
                                      stoploss_start, stoploss_int, stoploss_end):
        '''Takes all the strat info, updates the calc status text, passes the info to the check_trade_stat function'''

        trade_strat_dict = {}

        #set visibility of strat inputs from checklists
        if 'StopLoss' in strat_checklist:
            stoploss_div = {'display': 'grid', 'width': '100%', 'margin-bottom': '5px'}
            trade_strat_dict['stoploss_type'] = stoploss_type
            trade_strat_dict['stoploss_start'] = stoploss_start
            trade_strat_dict['stoploss_int'] = stoploss_int
            trade_strat_dict['stoploss_end'] = stoploss_end
        else:
            stoploss_div = {'display': 'none'}
        if 'Stoch' in strat_checklist:
            stoch_div = {'display': 'grid', 'width': '100%', 'margin-bottom': '5px'}
        else:
            stoch_div = {'display': 'none'}
        if 'TradeVol' in strat_checklist:
            tradevol_div = {'display': 'grid', 'width': '100%', 'margin-bottom': '5px'}
        else:
            tradevol_div = {'display': 'none'}

        strat_inp_list = [ma_method, strat_checklist, start_date, end_date, short_start, short_end,
                           short_int, long_start, long_end, long_int, macd_signal, trade_cost_pct, trade_strat_dict]

        store = {
            'data': strat_inp_list
        }

        return 'Status: LOADING', store, stoploss_div


    @app.callback([Output('MA_method', 'value'),
                   Output('ma_rng_profit_output', 'children'),
                   Output('ma_rng_timeframe_output', 'children'),
                   Output('ma_rng_matype_output', 'children'),
                   Output('ma_rng_sma_output', 'children'),
                   Output('ma_rng_lma_output', 'children'),
                   Output('ma_rng_timelen_output', 'children'),
                   Output('ma_rng_numtrades_output', 'children'),
                   Output('strat_status', 'children', allow_duplicate=True)],
                   Input('strat_data_store', 'data'),
                   prevent_initial_call=True)
    def check_trade_strat(strat_inp_list):
        ''' performs iterative strategies to find best, taking inputs from grid inputs'''
        strat_inp_list = strat_inp_list['data']

        ma_method, strat_checklist, start_date, end_date, short_start, short_end, short_int, long_start, long_end, \
        long_int, macd_signal, trade_cost_pct, trade_strat_dict = strat_inp_list
        print(f'trade_strat_dict {trade_strat_dict}')

        if len(ma_method) == 0:  # set default calc method to simple moving average if no others selected
            ma_method = ['Simple']

        # strat_checklist

        if 'T' in start_date:
            start_date = start_date.split('T')[0]
        if 'T' in end_date:
            end_date = end_date.split('T')[0]
        # start_date_str = start_date
        # end_date_str = end_date
        # print(f'start: {start_date_str}    end: {end_date_str}')
        short_ma_range = [short_start, short_end, short_int]
        long_ma_range = [long_start, long_end, long_int]

        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        StratTradingDf.df = StratTradingDf.raw_df[StratTradingDf.raw_df['Open time'].between(start_date, end_date, inclusive='both')]

        StratTradingDf.check_ma_range(ma_method, short_ma_range, long_ma_range, trade_cost_pct,
                                      macd_signal=macd_signal, trade_strat_dict=trade_strat_dict)
        StratTradingDf.ma_profit_df.sort_values(by=['Pct_Profit'], ascending=False, inplace=True)

        print(f"timeframes: {StratTradingDf.ma_profit_df['timeframe'].iloc[0]}")
        final_pct_profit = f"Final % profit: {round(StratTradingDf.ma_profit_df['Pct_Profit'].iloc[0],5)} for MA ranges: [{short_start}:{short_int}:{short_end}] ¦ [{long_start}:{long_int}:{long_end}]"
        # best_timeframe = f"Best num hour timeframe: {StratTradingDf.ma_profit_df['timeframe'].iloc[0][0]} to {StratTradingDf.ma_profit_df['timeframe'].iloc[0][1]}"
        best_timeframe = f"Best num hour timeframe: {StratTradingDf.ma_profit_df['timeframe'].iloc[0]}"
        if StratTradingDf.ma_profit_df['MA_type'].iloc[0] == 'MACD':
            best_ma_type = f"Best MA type: {StratTradingDf.ma_profit_df['MA_type'].iloc[0]} ¦ signal: {StratTradingDf.ma_profit_df['MACD signal'].iloc[0]}"
        else:
            best_ma_type = f"Best MA type: {StratTradingDf.ma_profit_df['MA_type'].iloc[0]}"
        best_s_ma = f"Best Short MA length: {StratTradingDf.ma_profit_df['s_ma'].iloc[0]}"
        best_l_ma = f"Best long MA length: {StratTradingDf.ma_profit_df['l_ma'].iloc[0]}"
        timeframe_len = f"Timeframe length [hrs]: {StratTradingDf.ma_profit_df['timeframe_len'].iloc[0]}"
        num_trades = f"Num trades: {StratTradingDf.ma_profit_df['Num_Trades'].iloc[0]}"
        print(final_pct_profit)
        strat_status = 'Status: Calculation complete'
        return ma_method, final_pct_profit, best_timeframe, best_ma_type, best_s_ma, best_l_ma, timeframe_len, num_trades, strat_status

    @app.callback([Output(component_id='timeframe-slider', component_property='min'),
                   Output(component_id='timeframe-slider', component_property='max'),
                   Output(component_id='timeframe-slider', component_property='value'),
                   Output(component_id='timeframe-slider', component_property='marks'),
                   Output(component_id='visframe-slider', component_property='value')],
                  [Input(component_id='df_num_hours', component_property='value')])
    def set_time_slider_range(df_num_hours):

        TradingDf.slice_df(df_num_hours)

        time_min = TradingDf.df.index[0]
        time_max = TradingDf.df.index[-1]
        time_value = [time_min, time_max]
        vis_value = time_value
        time_marks = TradingDf.date_dict

        return time_min, time_max, time_value, time_marks, vis_value



    @app.callback([Output(component_id='visframe-slider', component_property='min'),
                   Output(component_id='visframe-slider', component_property='max'),
                   Output(component_id='visframe-slider', component_property='value', allow_duplicate=True),
                   Output(component_id='visframe-slider', component_property='marks')],
                  [Input(component_id='timeframe-slider', component_property='value'),
                   Input("graph", "relayoutData")],
                  prevent_initial_call=True)
    def set_visual_slider_range(timeframeVal, relOut):
        '''update visual slide from timeframe values selected'''

        vis_min = timeframeVal[0]
        vis_max = timeframeVal[1]
        vis_value = [vis_min, vis_max]

        # set view axis if moved
        if relOut is not None:
            # print(f' relout1: {relOut}')
            if "xaxis.range[0]" in relOut:
                format_data = "%y-%m-%d %H:%M:%S.%f"
                datetime_ob_0 = datetime.datetime.strptime(relOut["xaxis.range[0]"], "%Y-%m-%d %H:%M:%S.%f")
                datetime_ob_0 = hour_rounder(datetime_ob_0)
                datetime_ob_0 = datetime_ob_0.strftime(format_data)
                datetime_ob_1 = datetime.datetime.strptime(relOut["xaxis.range[1]"], "%Y-%m-%d %H:%M:%S.%f")
                datetime_ob_1 = hour_rounder(datetime_ob_1)
                datetime_ob_1 = datetime_ob_1.strftime(format_data)
                # print(f'date obs: {datetime_ob_0} ; {datetime_ob_1}')
                try:
                    new_vis_min = TradingDf.df[TradingDf.df['Open time'].dt.strftime(format_data) == datetime_ob_0].index[0]
                    if new_vis_min < timeframeVal[0]:
                        vis_val1 = vis_min
                    else:
                        vis_val1 = new_vis_min
                except:
                    vis_val1 = vis_min
                try:
                    new_vis_max = TradingDf.df[TradingDf.df['Open time'].dt.strftime(format_data) == datetime_ob_1].index[0]
                    if new_vis_max > timeframeVal[1]:
                        vis_val2 = vis_max
                    else:
                        vis_val2 = new_vis_max
                except:
                    vis_val2 = vis_max

                vis_value = [vis_val1, vis_val2]

        # update marks
        vis_marks = {}
        for i in range(len(TradingDf.datelist)):
            if TradingDf.date_idxs[i] < vis_max and TradingDf.date_idxs[i] > vis_min:
                vis_marks[str(TradingDf.date_idxs[i])] = TradingDf.datelist[i]

        return vis_min, vis_max, vis_value, vis_marks


    @app.callback(
        [Output("graph", "figure"),
         Output("ma_profit_output", "children"),
         Output("graphOverlay", "value"),
         Output('graph_ma_inputs_div', 'style'),
         Output('graph_wy_inputs_div', 'style')],
        [Input(component_id="timeframe-slider", component_property="value"),
         Input("visframe-slider", "value"),
         Input("ma_short", "value"),
         Input("ma_long", "value"),
         Input("ma_signal", "value"),
         Input("trade_pct_fee", "value"),
         Input("df_num_hours", "value"),
         Input('checklist', 'value'),
         Input('graphOverlay', 'value'),
         Input('Graph_MA_method', 'value'),
         Input('graph_trade_method', 'value')]
    )
    def display_candlestick(timeframeVal, visframVal, ma_short, ma_long, ma_signal, trade_pct_fee, df_num_hours, checklist, graphOverlay, graphMAmethod, graphTradeMethod):

        TradingDf.df = TradingDf.raw_df.loc[timeframeVal[0]:timeframeVal[1]]

        # MACD
        if graphMAmethod == 'MACD' or graphOverlay == 'MACD' or 'MACD' in checklist:  # only calc if needed
            macd = MACD(close=TradingDf.df['Close'],
                        window_slow=ma_long,
                        window_fast=ma_short,
                        window_sign=ma_signal)

        # Stochastic
        if graphMAmethod == 'Stoch' or graphOverlay == 'Stoch' or 'Stoch' in checklist:  # only calc if needed
            stoch = StochasticOscillator(high=TradingDf.df['High'],
                                         close=TradingDf.df['Close'],
                                         low=TradingDf.df['Low'],
                                         window=14,
                                         smooth_window=3)

        # setup lists to allow activation of diff graphs
        num_extra_graphs = len(checklist)
        specs = [[{"secondary_y": True}]]  # set main graph with secondary y axis
        row_heights = [0.5]  # set main graph as always 0.5
        if num_extra_graphs == 0:
            row_heights = [0.7]  # set graph height of div
            num_extra_graphs = 1
            space_value = 0.3  # set blank space after graph
        else:
            space_value = 0.5 / num_extra_graphs
        row_heights.extend(repeat(space_value, num_extra_graphs))   # add x number of fractional values to fill the extra space
        specs.extend(repeat([{"secondary_y": False}], num_extra_graphs))

        fig = go.Figure()
        fig = plotly.subplots.make_subplots(rows=num_extra_graphs+1, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                                            row_heights=row_heights,
                                            specs=specs)

        fig.add_trace(go.Candlestick(
            x=TradingDf.df['Open time'],
            open=TradingDf.df['Open'], high=TradingDf.df['High'],
            low=TradingDf.df['Low'], close=TradingDf.df['Close'],
            name='Price Data'
        ), secondary_y=False, row=1, col=1)


        # Add Moving Average Trace
        final_pct_profit = 0  # set default value to avoid errors
        MA_div_display = {'display': 'none'}
        Wyckoff_div_display = {'display': 'none'}

        if graphMAmethod == 'MACD':
            graphOverlay = 'MACD'
            fig.add_trace(
                go.Scatter(x=TradingDf.df['Open time'], y=macd.macd(), line=dict(color='black', width=2),
                           name='MACD'), secondary_y=True)
            fig.add_trace(
                go.Scatter(x=TradingDf.df['Open time'], y=macd.macd_signal(), line=dict(color='blue', width=1),
                           name='MACD signal'), secondary_y=True)

        elif graphTradeMethod == 'MA':
            MA_div_display = {'display': 'inline', 'padding': '20px'}

            graphOverlay = graphOverlay

            TradingDf.update_df_ma(ma_method=graphMAmethod, short_ma=ma_short, long_ma=ma_long,
                                   trade_cost_pct=trade_pct_fee, signal_ma=ma_signal, trade_strat_dict={})
            final_pct_profit = round(TradingDf.transaction_df.Pct_profit_cum.iloc[-1], 5)
            final_pct_profit = f'Final % profit: {final_pct_profit}  ¦  Number of trades: {len(TradingDf.transaction_df.Pct_profit_cum)}'

            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['MA_Short'],
                                     opacity=0.7,
                                     line=dict(color='blue', width=2),
                                     name='MA_Short'), secondary_y=False, row=1, col=1)
            # # Add long Moving Average Trace
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['MA_Long'],
                                     opacity=0.7,
                                     line=dict(color='orange', width=2),
                                     name='MA_Long'), secondary_y=False, row=1, col=1)
            for index, row in TradingDf.transaction_df.iterrows():
                fig.add_vline(x=TradingDf.transaction_df['Buy_Open time'][index], line_width=3, line_dash="dash",
                              line_color="green", row=1,
                              col=1)
                fig.add_vline(x=TradingDf.transaction_df['Sell_Open time'][index], line_width=3, line_dash="dash",
                              line_color="red", row=1,
                              col=1)

        elif graphTradeMethod == 'Wyckoff':
            Wyckoff_div_display = {'display': 'inline', 'padding': '20px'}
            pass


        fig.update_yaxes(title_text="Price", row=1, col=1)

        # set overlay graph for main graph
        if graphOverlay == 'Vol':
            fig.add_trace(go.Bar(x=TradingDf.df['Open time'], y=TradingDf.df['Volume'], name='Trade Volume'), secondary_y=True)
            fig.update_traces(marker_color='rgba(0,0,250, 0.2)', marker_line_width=0, selector=dict(type="bar"))
            fig.update_layout(yaxis2=dict(title_text='Volume', showgrid=False))
        elif graphOverlay == 'VolPct':
            colors = ['rgba(0,250,0, 0.2)' if row['Open'] - row['Close'] >= 0 else 'rgba(250,0,0, 0.2)' for index, row in TradingDf.df.iterrows()]
            fig.add_trace(go.Bar(x=TradingDf.df['Open time'], y=TradingDf.df['Taker buy base asset volume pct'], marker_color=colors,
                                 name='Taker buy base asset volume pct'), secondary_y=True)
            fig.update_layout(yaxis2=dict(title_text='Maker sell / volume pct', showgrid=False))
        elif graphOverlay == 'MACD':
            colors = ['rgba(0,250,0, 0.2)' if val >= 0 else 'rgba(250,0,0, 0.2)' for val in macd.macd_diff()]
            fig.add_trace(go.Bar(x=TradingDf.df['Open time'], y=macd.macd_diff(), marker_color=colors, name='MACD difference'), secondary_y=True)
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=macd.macd(), line=dict(color='black', width=2), name='MACD'), secondary_y=True)
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=macd.macd_signal(), line=dict(color='blue', width=1), name='MACD signal'), secondary_y=True)
            fig.update_yaxes(title_text="MACD", showgrid=False)
        elif graphOverlay == 'Stoch':
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=stoch.stoch(), line=dict(color='black', width=1), name='Stochastic'), secondary_y=True)
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=stoch.stoch_signal(), line=dict(color='blue', width=1), name='Stochastic Signal'), secondary_y=True)
            fig.update_yaxes(title_text="Stochastic Signal", showgrid=False)

        # fig.update_layout(
        #     yaxis3=dict(
        #         title="yaxis3 title",
        #         titlefont=dict(
        #             color="#d62728"
        #         ),
        #         tickfont=dict(
        #             color="#d62728"
        #         ),
        #         anchor="x",
        #         overlaying="y",
        #         side="right"
        #     ),
        #     yaxis4=dict(
        #         title="yaxis4 title",
        #         # titlefont=dict(
        #         #     color="#9467bd"
        #         # ),
        #         # tickfont=dict(
        #         #     color="#9467bd"
        #         # ),
        #         # anchor="free",
        #         overlaying="y",
        #         side="right",
        #         # position=0.85
        #     )
        # )

        fig.update_layout(
            xaxis=dict(
                rangeslider_visible=False,
                rangeselector=dict(
                    buttons=list([
                        # dict(count=1, label="HTD", step="hour", stepmode="backward"),
                        # dict(count=3, label="3h", step="hour", stepmode="backward"),
                        dict(count=24, label="day", step="hour", stepmode="backward"),
                        dict(count=168, label="week", step="hour", stepmode="backward"),
                        dict(count=744, label="month", step="hour", stepmode="backward"),
                        dict(count=2232, label="3 months", step="hour", stepmode="backward"),
                        dict(step="all")
                    ])
                )))

        # Plot volume trace on 2nd row in our figure
        if 'VolPct' in checklist:
            vol_idx = checklist.index('VolPct') + 2
            colors = ['green' if row['Open'] - row['Close'] >= 0 else 'red' for index, row in TradingDf.df.iterrows()]
            fig.add_trace(go.Bar(x=TradingDf.df['Open time'], y=TradingDf.df['Taker buy base asset volume pct'], marker_color=colors, name='Taker buy base asset volume pct'), row=vol_idx, col=1)
            fig.update_yaxes(title_text="maker sell / volume pct", row=vol_idx, col=1)

        # Plot MACD trace on 3rd row
        if 'MACD' in checklist:
            MACD_idx = checklist.index('MACD') + 2
            colors = ['green' if val >= 0 else 'red' for val in macd.macd_diff()]
            fig.add_trace(go.Bar(x=TradingDf.df['Open time'], y=macd.macd_diff(), marker_color=colors, name='MACD difference'), row=MACD_idx, col=1)
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=macd.macd(), line=dict(color='black', width=2), name='MACD'), row=MACD_idx, col=1)
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=macd.macd_signal(), line=dict(color='blue', width=1), name='MACD signal'), row=MACD_idx, col=1)
            fig.update_yaxes(title_text="MACD", showgrid=False, row=MACD_idx, col=1)

        # Plot stochastics trace on 4th row
        if 'Stoch' in checklist:
            stoch_idx = checklist.index('Stoch') + 2
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=stoch.stoch(), line=dict(color='black', width=1), name='Stochastic'), row=stoch_idx, col=1)
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=stoch.stoch_signal(), line=dict(color='blue', width=1), name='Stochastic Signal'), row=stoch_idx, col=1)
            fig.update_yaxes(title_text="Stoch", row=stoch_idx, col=1)

        fig.update_layout(
            xaxis_rangeslider_visible=False,
            showlegend=True,
            height=1200
        )

        # update axis after modifying view range
        disp_date_start = TradingDf.df.loc[visframVal[0]]['Open time']
        disp_date_end = TradingDf.df.loc[visframVal[1]]['Open time']
        disp_candle_ymax = TradingDf.df.loc[visframVal[0]:visframVal[1]].High.max()
        disp_candle_ymin = TradingDf.df.loc[visframVal[0]:visframVal[1]].Low.min()
        fig.update_layout(
            xaxis=dict(range=[disp_date_start, disp_date_end]),
            yaxis=dict(range=[disp_candle_ymin, disp_candle_ymax]),
            # yaxis2=dict(range=[disp_candle2_ymin, disp_candle2_ymax*1.1]),
            yaxis2=dict(autorange=True)  # auto range required to allow swapping of overlay graph
        )

        return fig, final_pct_profit, graphOverlay, MA_div_display, Wyckoff_div_display