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


def get_graph_callbacks(app, TradingDf, StratTradingDf):

    @app.callback(
        [Output("graph", "figure"),
         Output("ma_profit_output", "children"),
         Output("graphOverlay", "value"),
         Output('graph_ma_inputs_div', 'style'),
         Output('graph_wy_inputs_div', 'style'),
         # Output('data_table_div','style')],
         Output('raw_trading_df', 'data'),
         Output('raw_trading_df', 'columns'),
         Output('transaction_trading_df', 'data'),
         Output('transaction_trading_df', 'columns')],
        [#Input(component_id="timeframe-slider", component_property="value"),
         Input("visframe-slider", "value"),
         Input("ma_short", "value"),
         Input("ma_long", "value"),
         Input("ma_signal", "value"),
         Input("trade_pct_fee", "value"),
         Input('checklist', 'value'),
         Input('graphOverlay', 'value'),
         Input('Graph_MA_method', 'value'),
         Input('graph_trade_method', 'value'),
         Input('wy_vol_ma', 'value'), Input('wy_vol_variation_ma', 'value'), Input('wy_vol_max_var_grad_period', 'value'),
         Input('wy_price_ma', 'value'), Input('wy_price_slope_offset', 'value'), Input('wy_price_slope_ave', 'value'),
         Input('wy_price_slope_peak_delta', 'value'), Input('wy_price_slope_peak_delta_window', 'value'),
         Input('wy_accum_time', 'value'),
        ]
    )
    def display_candlestick(visframVal, ma_short, ma_long, ma_signal, trade_pct_fee,
                            checklist, graphOverlay, graphMAmethod, graphTradeMethod,
                            wy_vol_ma, wy_vol_variation_ma, wy_vol_max_var_grad_period,
                            wy_price_ma, wy_price_slop_offset, wy_price_slope_ave,
                            wy_price_slope_peak_delta, wy_price_slope_peak_delta_window, wy_accum_time):

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

        # set up main set of graphs
        fig = go.Figure()
        # fig.update_traces(selector={'name': 'Accum_Price_Slope_Check'}, overwrite=True).data = []
        fig = plotly.subplots.make_subplots(rows=num_extra_graphs+1, cols=1, shared_xaxes=True, vertical_spacing=0.02,
                                            row_heights=row_heights,
                                            specs=specs)
        fig.update_traces(overwrite=True)

        # plot main candlestick graph
        fig.add_trace(go.Candlestick(
            x=TradingDf.df['Open time'],
            open=TradingDf.df['Open'], high=TradingDf.df['High'],
            low=TradingDf.df['Low'], close=TradingDf.df['Close'],
            name='Price Data'
        ), secondary_y=False, row=1, col=1)
        fig.update_yaxes(title_text="Price", row=1, col=1)

        # Add Moving Average Trace
        final_pct_profit = 0  # set default value to avoid errors
        MA_div_display = {'display': 'none'}
        Wyckoff_div_display = {'display': 'none'}

        if graphTradeMethod == 'MA':
            MA_div_display = {'display': 'inline', 'padding': '20px'}
            if (ma_short < ma_long) and (ma_long < TradingDf.df_length):
                TradingDf.update_df_ma(ma_method=graphMAmethod, short_ma=ma_short, long_ma=ma_long,
                                       trade_cost_pct=trade_pct_fee, signal_ma=ma_signal, trade_strat_dict={})
                if TradingDf.transaction_df.Pct_profit_cum.iloc[-1]:
                    final_pct_profit = round(TradingDf.transaction_df.Pct_profit_cum.iloc[-1], 5)
                    num_trades = len(TradingDf.transaction_df.Pct_profit_cum)
                else:
                    final_pct_profit = 0
                    num_trades = 0
                final_pct_profit = f'Final % profit: {final_pct_profit}  ¦  Number of trades: {num_trades}'
                print(final_pct_profit)

                if graphMAmethod == 'MACD':
                    graphOverlay = 'None'
                    fig.add_trace(
                        go.Scatter(x=TradingDf.df['Open time'], y=macd.macd(), line=dict(color='black', width=2),
                                   name='MACD'), secondary_y=True)
                    fig.add_trace(
                        go.Scatter(x=TradingDf.df['Open time'], y=macd.macd_signal(), line=dict(color='blue', width=1),
                                   name='MACD signal'), secondary_y=True)
                else:
                    # graphOverlay = graphOverlay
                    # Add Moving Average Traces
                    fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['MA_Short'],
                                             opacity=0.7,
                                             line=dict(color='blue', width=2),
                                             name='MA_Short'), secondary_y=False, row=1, col=1)

                    fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['MA_Long'],
                                             opacity=0.7,
                                             line=dict(color='orange', width=2),
                                             name='MA_Long'), secondary_y=False, row=1, col=1)

                # Add vertical by/sell lines
                for index, row in TradingDf.transaction_df.iterrows():
                    fig.add_vline(x=TradingDf.transaction_df['Buy_Open time'][index], line_width=3, line_dash="dash",
                                  line_color="green", row=1,
                                  col=1)
                    fig.add_vline(x=TradingDf.transaction_df['Sell_Open time'][index], line_width=3, line_dash="dash",
                                  line_color="red", row=1,
                                  col=1)

        elif graphTradeMethod == 'Wyckoff':

            Wyckoff_div_display = {'display': 'inline', 'padding': '20px'}
            TradingDf.check_wyckoff(wy_vol_ma, wy_vol_variation_ma, wy_vol_max_var_grad_period,
                                    wy_price_ma, wy_price_slop_offset, wy_price_slope_ave, wy_price_slope_peak_delta, wy_price_slope_peak_delta_window,
                                    wy_accum_time)
            graphOverlay = 'Wyckoff'



            # plot volume graphs
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Volume ma'],
                                     opacity=0.7,
                                     line=dict(color='blue', width=2),
                                     name='Volume ma', yaxis='y2'))

            # colour based off based off number of sell makers (more sell makers bad)
            colors = ['rgba(0,250,0, 0.2)' if row['Taker buy base asset volume'] >= (row['Volume']/2) else 'rgba(250,0,0, 0.2)' for index, row
                      in TradingDf.df.iterrows()]

            fig.add_trace(go.Bar(x=TradingDf.df['Open time'], y=TradingDf.df['Volume'], marker_color=colors,
                                 name='Volume', yaxis='y2'))
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Volume Pct Variation'],
                                     name='Volume Pct Variation', line=dict(color='green', width=2, dash='dot'),
                                     yaxis='y4'))
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Volume Pct Variation abs'],
                                     name='Volume Pct Variation abs', line=dict(color='blue', width=2, dash='dot'),
                                     yaxis='y4'))
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Volume Pct Variation abs ma'],
                                     name='Volume Pct Variation abs ma', line=dict(color='blue', width=2, dash='longdash'),
                                     yaxis='y4'))
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Volume Pct Variation abs gradient 1'],
                                     name='Volume Pct Variation abs gradient 1',
                                     line=dict(color='blue', width=2, dash='solid'),
                                     yaxis='y4'))



            # plot Wyckoff price variations
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Price ma'],
                                     opacity=0.7,
                                     line=dict(color='black', width=2),
                                     name='Price ma', yaxis='y1'), secondary_y=False, row=1, col=1)
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Price gradient 1'],
                                     name='Price gradient 1', line=dict(color='black', width=2, dash='dot'),
                                     yaxis='y3'))
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Price gradient 1 ma'],
                                     name='Price gradient 1 ma', line=dict(color='black', width=2, dash='longdash'),
                                     yaxis='y3'))
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Price gradient 1 max delta'],
                                     name='Price gradient 1 max delta', line=dict(color='red', width=2, dash='solid'),
                                     yaxis='y3'))
            fig.add_trace(go.Scatter(x=TradingDf.df['Open time'], y=TradingDf.df['Accum_Price_Slope_Check'],
                                     name='Accum_Price_Slope_Check', yaxis='y3',
                                     mode='markers', marker=dict(symbol='star', size=10, color='blue', line=dict(width=2))))




            # print('fig data:')
            # print(fig.data)

            # Graphing
            fig.update_layout(
                xaxis=dict(
                    domain=[0, 0.9]
                ),
                yaxis2=dict(
                    title="Volume",
                    titlefont=dict(
                        color="#000000"
                    ),
                    tickfont=dict(
                        color="#000000"
                    ),
                    anchor="x",  # specifying x - axis has to be the fixed
                    overlaying="y",  # specifyinfg y - axis has to be separated
                    side="right"  # specifying the side the axis should be present
                ),
                yaxis3=dict(
                    title="Price Pct Variations",
                    titlefont=dict(
                        color="#8f00ff"
                    ),
                    tickfont=dict(
                        color="#8f00ff"
                    ),
                    anchor="free",  # specifying x - axis has to be the fixed
                    overlaying="y",  # specifyinfg y - axis has to be separated
                    side="right",  # specifying the side the axis should be present
                    position=0.95  # specifying the position of the axis
                ),
                yaxis4=dict(
                    title="Vol Pct Variations",
                    titlefont=dict(
                        color="#8f00ff"
                    ),
                    tickfont=dict(
                        color="#8f00ff"
                    ),
                    anchor="free",  # specifying x - axis has to be the fixed
                    overlaying="y",  # specifyinfg y - axis has to be separated
                    side="right",  # specifying the side the axis should be present
                    position=1  # specifying the position of the axis
                ),
                legend={
                         "x": 0.8,
                         "y": 1,
                         # "xref": "container",
                         # "yref": "container",
                         # "bgcolor": "Gold",
                },
            )


            pass



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
        elif graphOverlay == 'None':
            pass

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

        raw_trading_df = TradingDf.df.to_dict('records')
        raw_trading_df_columns = [{'id': c, 'name': c} for c in TradingDf.df.columns]
        transaction_trading_df = TradingDf.transaction_df.to_dict('records')
        transaction_trading_df_columns = [{'id': c, 'name': c} for c in TradingDf.transaction_df.columns]

        return fig, final_pct_profit, graphOverlay, MA_div_display, Wyckoff_div_display, \
               raw_trading_df, raw_trading_df_columns, transaction_trading_df, transaction_trading_df_columns