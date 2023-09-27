# import callback functions from each subfolder to call in main app
from StratFunctions import get_strat_callbacks
from VisualisationFunctions import get_vis_callbacks
from GraphingFunctions import get_graph_callbacks


def get_callbacks(app, TradingDf, StratTradingDf):

    get_strat_callbacks(app, TradingDf, StratTradingDf)

    get_vis_callbacks(app, TradingDf, StratTradingDf)

    get_graph_callbacks(app, TradingDf, StratTradingDf)


