from dash import Dash, dcc, html, Input, Output, State, ctx
import datetime


def hour_rounder(t):
    # Rounds to nearest hour by adding a timedelta hour if minute >= 30
    return (t.replace(second=0, microsecond=0, minute=0, hour=t.hour)
               +datetime.timedelta(hours=t.minute//30))


def get_vis_callbacks(app, TradingDf, StratTradingDf):

    def set_time_from_inpbox():
        pass

    def set_time_from_rngselect():
        pass


    @app.callback([Output(component_id='timeframe-slider', component_property='min'),
                   Output(component_id='timeframe-slider', component_property='max'),
                   Output(component_id='timeframe-slider', component_property='value'),
                   Output(component_id='timeframe-slider', component_property='marks'),
                   Output(component_id='visframe-slider', component_property='value'),
                   Output(component_id='df_num_hours', component_property='value')],
                  [Input(component_id='df_num_hours', component_property='value'),
                   Input('data_timeunit', 'value'),
                   Input('time-reset-btn', 'n_clicks'),
                   Input('graph-date-range', 'start_date'), Input('graph-date-range', 'end_date')])
    def set_time_slider_range(df_num_hours, data_timeunit, btn, start_date, end_date):

        # handle if reset button has been pressed:
        if "time-reset-btn" == ctx.triggered_id:
            print("Reset button clicked")

        # handle date input field
        if 'T' in start_date:
            start_date = start_date.split('T')[0]
        if 'T' in end_date:
            end_date = end_date.split('T')[0]
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")

        # handle date slicing
        TradingDf.slice_df(df_num_hours, data_timeunit, start_date=start_date, end_date=end_date)
        print('length of trading df:', len(TradingDf.df))


        time_min = TradingDf.df.index[0]
        time_max = TradingDf.df.index[-1]
        time_value = [time_min, time_max]
        vis_value = time_value
        time_marks = TradingDf.date_dict

        return time_min, time_max, time_value, time_marks, vis_value, len(TradingDf.df)

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