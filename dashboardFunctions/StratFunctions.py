from dash import Dash, dcc, html, Input, Output, State, ctx
import datetime


def get_strat_callbacks(app, TradingDf, StratTradingDf):

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

        # clean date data and update dataframe
        if 'T' in start_date:
            start_date = start_date.split('T')[0]
        if 'T' in end_date:
            end_date = end_date.split('T')[0]
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        StratTradingDf.df = StratTradingDf.raw_df[
            StratTradingDf.raw_df['Open time'].between(start_date, end_date, inclusive='both')]

        short_ma_range = [short_start, short_end, short_int]
        long_ma_range = [long_start, long_end, long_int]
        StratTradingDf.check_ma_range(ma_method, short_ma_range, long_ma_range, trade_cost_pct,
                                      macd_signal=macd_signal, trade_strat_dict=trade_strat_dict)
        StratTradingDf.ma_profit_df.sort_values(by=['Pct_Profit'], ascending=False, inplace=True)

        print(f"timeframes: {StratTradingDf.ma_profit_df['timeframe'].iloc[0]}")
        final_pct_profit = f"Final % profit: {round(StratTradingDf.ma_profit_df['Pct_Profit'].iloc[0], 5)} for MA ranges: [{short_start}:{short_int}:{short_end}] ¦ [{long_start}:{long_int}:{long_end}]"
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
