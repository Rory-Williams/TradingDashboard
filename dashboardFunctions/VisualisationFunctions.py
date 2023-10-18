from dash import Dash, dcc, html, Input, Output, State, ctx
import datetime


def hour_rounder(t):
    # Rounds to nearest hour by adding a timedelta hour if minute >= 30
    return (t.replace(second=0, microsecond=0, minute=0, hour=t.hour)
               +datetime.timedelta(hours=t.minute//30))


def get_vis_callbacks(app, TradingDf, StratTradingDf):


    @app.callback([Output(component_id='timeframe-slider', component_property='min'),
                   Output(component_id='timeframe-slider', component_property='max'),
                   Output(component_id='timeframe-slider', component_property='value'),
                   Output(component_id='timeframe-slider', component_property='marks'),
                   Output(component_id='visframe-slider', component_property='value'),
                   Output(component_id='df_num_hours', component_property='value'),
                   Output('graph-date-range', 'start_date'), Output('graph-date-range', 'end_date')],
                  [Input(component_id='df_num_hours', component_property='value'),
                   Input('data_timeunit', 'value'),
                   Input('time-reset-btn', 'n_clicks'),
                   Input('graph-date-range', 'start_date'), Input('graph-date-range', 'end_date'),
                   Input(component_id="timeframe-slider", component_property="value")])
    def set_time_slider_range(df_num_interval, data_timeunit, btn, start_date_inp, end_date_inp, timeframeVal):
        '''retrieves date data from various sources, sends date to dataframe class function to trim dataframe
        Then sets the time slider values + key'''

        prev_start_date = TradingDf.df['Open time'].iloc[0]
        prev_end_date = TradingDf.df['Open time'].iloc[-1]
        start_date = prev_start_date
        end_date = prev_end_date


        if TradingDf.df.index[0] != timeframeVal[0] or TradingDf.df.index[-1] != timeframeVal[1]:
            TradingDf.df = TradingDf.df_temp.loc[timeframeVal[0]:timeframeVal[1]]

        else:
            if "time-reset-btn" == ctx.triggered_id:  # reset button pressed, set to recent date
                end_date = TradingDf.raw_df_conv['Open time'].iloc[-1]

            elif len(TradingDf.df.index) != df_num_interval:  # date from num hours
                if df_num_interval > TradingDf.df_length:
                    start_date = TradingDf.raw_df_conv['Open time'].iloc[0]
                else:  # find start date from current end date, datetime unit, and value
                    if data_timeunit == 'H':
                        start_date = prev_end_date - datetime.timedelta(hours=df_num_interval - 1)
                    elif data_timeunit == 'D':
                        start_date = prev_end_date - datetime.timedelta(days=df_num_interval - 1)
                    elif data_timeunit == 'W':
                        start_date = prev_end_date - datetime.timedelta(weeks=df_num_interval - 1)
                    else:
                        start_date = prev_start_date

            else:  # date from date picker
                print('input dates:', start_date_inp, end_date_inp)
                start_date = start_date_inp
                end_date = end_date_inp
                if 'T' in start_date:
                    start_date = start_date.split('T')[0]
                    start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                if 'T' in end_date:
                    end_date = end_date.split('T')[0]
                    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
                print('input new dates:', start_date, end_date)

            TradingDf.slice_df(data_timeunit, start_date=start_date, end_date=end_date)


        time_inp_start = str(TradingDf.df['Open time'].iloc[0]).replace(' ', 'T')
        time_inp_end = str(TradingDf.df['Open time'].iloc[-1]).replace(' ', 'T')
        time_min = TradingDf.df_temp.index[0]
        time_max = TradingDf.df_temp.index[-1]
        time_value = [TradingDf.df.index[0], TradingDf.df.index[-1]]
        vis_value = time_value
        time_marks = TradingDf.date_dict

        print('input outputs:', time_inp_start, time_inp_end)
        print('LENGTH DF:', len(TradingDf.df.index))

        return time_min, time_max, time_value, time_marks, vis_value, len(TradingDf.df.index), \
            time_inp_start, time_inp_end

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
                    new_vis_min = \
                    TradingDf.df[TradingDf.df['Open time'].dt.strftime(format_data) == datetime_ob_0].index[0]
                    if new_vis_min < timeframeVal[0]:
                        vis_val1 = vis_min
                    else:
                        vis_val1 = new_vis_min
                except:
                    vis_val1 = vis_min
                try:
                    new_vis_max = \
                    TradingDf.df[TradingDf.df['Open time'].dt.strftime(format_data) == datetime_ob_1].index[0]
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