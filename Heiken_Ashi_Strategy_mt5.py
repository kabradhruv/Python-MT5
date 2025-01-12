import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import time

# Initialize MT5 connection and change the credentials
path = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
server = "MetaQuotes-Demo"
login = 11111111 
password = "********"
timeout = 10000
portable = False

if mt5.initialize(path=path, login=login, password=password, server=server, timeout=timeout, portable=portable):
    print("Initialization successful")
else:
    print("Initialization failed, error code =", mt5.last_error())

symbol = "XAUUSD"
timeframe = mt5.TIMEFRAME_M5  # 5-minute timeframe
num_bars = 2  # Fetch the last two bars (1 completed, 1 forming)
wick_threshold = 0.001
slippage = 10

# Fetch live OHLC data for last two candles
def get_ohlc(symbol, num_bars):
    ohlc = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    if ohlc is None or len(ohlc) == 0 or len(ohlc) < num_bars:
        print(f"Failed to fetch OHLC data for {symbol}, error:", mt5.last_error())
        return None
    return pd.DataFrame(ohlc)

# Calculating the last 100 bars HA OHLC
# Function to calculate Heiken Ashi candles
def calculate_previous_heiken_ashi():

    # retrieve the 100 bars OHLC 
    ohlc = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
    if ohlc is None or len(ohlc) == 0 or len(ohlc) < 2:
        print(f"Failed to fetch old (100 previous bars) OHLC data for {symbol}, error:", mt5.last_error())
        return None
    
    ha_df = pd.DataFrame(ohlc)

    # Initialize the first Heiken Ashi values using standard OHLC data
    ha_df['ha_close'] = (ha_df['open'] + ha_df['high'] + ha_df['low'] + ha_df['close']) / 4

    # Initialize ha_open for the first candle
    ha_df.loc[ha_df.index[0], 'ha_open'] = (ha_df['open'].iloc[0] + ha_df['close'].iloc[0]) / 2

    # Iterate over the dataframe to calculate HA Open based on the previous HA values
    for i in range(1, len(ha_df)):
        ha_df.loc[ha_df.index[i], 'ha_open'] = (ha_df.loc[ha_df.index[i - 1], 'ha_open'] + ha_df.loc[ha_df.index[i - 1], 'ha_close']) / 2

    ha_df['ha_high'] = ha_df[['ha_open', 'ha_close', 'high']].max(axis=1)
    ha_df['ha_low'] = ha_df[['ha_open', 'ha_close', 'low']].min(axis=1)

    return ha_df

# Function to calculate Heiken Ashi for the latest completed candle
def calculate_live_heiken_ashi(df_ohlc, ha_df):
    # Get the OHLC for the last completed candle (not the forming one)
    open_price = df_ohlc['open'].iloc[-2]
    high_price = df_ohlc['high'].iloc[-2]
    low_price = df_ohlc['low'].iloc[-2]
    close_price = df_ohlc['close'].iloc[-2]

    # First, calculate ha_open using the last row from the previous 100 bars HA data
    ha_open = (ha_df['ha_open'].iloc[-1] + ha_df['ha_close'].iloc[-1]) / 2

    # Now, calculate Heiken Ashi close, high, and low using the latest completed candle and the new ha_open
    ha_close = (open_price + high_price + low_price + close_price) / 4
    ha_high = max(high_price, ha_close, ha_open)  # Now using the new ha_open
    ha_low = min(low_price, ha_close, ha_open)

    # Store the calculated Heiken Ashi values in a dictionary
    live_ha_values = {
        'time': df_ohlc['time'].iloc[-2],  # Time of the last completed candle
        'open': open_price,
        'high': high_price,
        'low': low_price,
        'close': close_price,
        'ha_open': ha_open,
        'ha_close': ha_close,
        'ha_high': ha_high,
        'ha_low': ha_low
    }

    return live_ha_values

# Function to append the live HA data to the 100 previous HA data
def append_live_ha_to_df(df_ohlc, ha_df):
    # Calculate Heiken Ashi values for the last completed candle
    live_ha_values = calculate_live_heiken_ashi(df_ohlc, ha_df)

    # Convert the dictionary to a DataFrame row
    live_ha_df = pd.DataFrame([live_ha_values])

    # Append the new row to the existing dataframe containing the previous 100 bars
    ha_df = pd.concat([ha_df, live_ha_df], ignore_index=True)

    return ha_df

# Check Heiken Ashi candle pattern, and place trade if no position is open
def check_heiken_ashi_and_trade(ha_df, df_ohlc):
    # Use the last row for the most recently completed HA candle
    ha_open =  ha_df['ha_open'].iloc[-1]  # Last completed HA candle
    ha_close =  ha_df['ha_close'].iloc[-1]
    ha_high =  ha_df['ha_high'].iloc[-1]
    ha_low =  ha_df['ha_low'].iloc[-1]

    print(f"Completed candle OHLC: Open: {df_ohlc['open'].iloc[-2]}, Close: {df_ohlc['close'].iloc[-2]}, High: {df_ohlc['high'].iloc[-2]}, Low: {df_ohlc['low'].iloc[-2]}")
    print(f"Completed HA candle OHLC: Open: {ha_open}, Close: {ha_close}, High: {ha_high}, Low: {ha_low}")

    # Conditions
    bullish_indecisive_condition = ha_close > ha_open and (ha_high - ha_close > wick_threshold and ha_open - ha_low > wick_threshold)
    bearish_indecisive_condition = ha_close < ha_open and (ha_high - ha_open > wick_threshold and ha_close - ha_low > wick_threshold)
    buy_condition = ha_close > ha_open and wick_threshold > ha_open - ha_low
    sell_condition = ha_close < ha_open and ha_high - ha_open < wick_threshold

    # Handle market uncertainty (wick on both sides of the candle)
    if bullish_indecisive_condition or bearish_indecisive_condition:
        candle_type = "Bullish" if bullish_indecisive_condition else "Bearish"
        print(f" {candle_type} Indecisive candle detected, closing all positions.")
        close_all_positions()
        return

    # Get open positions for the symbol
    positions = mt5.positions_get(symbol=symbol)
    
    # If positions exist, handle them based on the current conditions
    if positions:
        for position in positions:
            if position.type == mt5.ORDER_TYPE_BUY and sell_condition:
                print("Market reversal detected: Sell signal while Buy position is open. Closing Buy position.")
                close_position(position)
                return  # Exit after closing the position
            elif position.type == mt5.ORDER_TYPE_SELL and buy_condition:
                print("Market reversal detected: Buy signal while Sell position is open. Closing Sell position.")
                close_position(position)
                return  # Exit after closing the position
        print("Position already open, skipping new trade.")
        return  # Skip placing a new trade if positions are open

    # Check for Buy or Sell conditions
    if buy_condition:
        print("Placing a BUY trade")
        place_trade("BUY")
    elif sell_condition:
        print("Placing a SELL trade")
        place_trade("SELL")

# Function to place a trade
def place_trade(trade_type):
    if trade_type == "BUY":
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(symbol).ask,
            "comment": "Heiken Ashi Buy Order",
            "deviation": slippage,  # Acceptable slippage
            "type_time": mt5.ORDER_TIME_GTC,
        }
    elif trade_type == "SELL":
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_SELL,
            "price": mt5.symbol_info_tick(symbol).bid,
            "comment": "Heiken Ashi Sell Order",
            "deviation": slippage,  # Acceptable slippage
            "type_time": mt5.ORDER_TIME_GTC,
        }

    order_result = mt5.order_send(request)
    if order_result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Error placing order:", order_result.comment)
        if order_result.retcode == mt5.TRADE_RETCODE_REQUOTE:
            print("Requote error, retrying...")
            retry_order_send(request)
    else:
        print(f"{trade_type} order placed successfully, order ticket:", order_result.order)

def retry_order_send(request):
    time.sleep(1)  # Wait 1 second before retrying
    order_result = mt5.order_send(request)
    if order_result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Error placing order on retry:", order_result.comment)
    else :
        print(f"Respective order placed successfully, order ticket:", order_result.order)


# Function to close positions
def close_all_positions():
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        for position in positions:
            close_position(position)

def close_position(position):
    slippage_list = [10, 15, 20]  # Slippage values to try
    for slippage in slippage_list:
        if position.type == mt5.ORDER_TYPE_BUY:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_SELL,
                "position": position.ticket,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": slippage,  # Current slippage value
            }
        elif position.type == mt5.ORDER_TYPE_SELL:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_BUY,
                "position": position.ticket,
                "price": mt5.symbol_info_tick(symbol).ask,
                "deviation": slippage,  # Current slippage value
            }

        result = mt5.order_send(request)

        if result is None:
            print("Error: order_send() returned None. Check if your request is valid:", mt5.last_error())
            continue  # Move to the next slippage value in the list

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"Position {position.ticket} closed successfully with slippage {slippage}")
            return  # Exit the loop as the order was successful
        elif result.retcode == mt5.TRADE_RETCODE_REQUOTE:
            print(f"Requote error with slippage {slippage}, trying with higher slippage...")

    # If still getting requote after trying all slippages, attempt to close at market price
    print("Requote error persisted, trying to close at market price...")
    if position.type == mt5.ORDER_TYPE_BUY:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL,
            "position": position.ticket,
            "price": mt5.symbol_info_tick(symbol).bid,  # Market price
            "deviation": 0,  # No slippage for market order
        }
    elif position.type == mt5.ORDER_TYPE_SELL:
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_BUY,
            "position": position.ticket,
            "price": mt5.symbol_info_tick(symbol).ask,  # Market price
            "deviation": 0,  # No slippage for market order
        }

    result = mt5.order_send(request)
    if result is None:
        print("Error: order_send() returned None when trying market price. Check your request:", mt5.last_error())
    elif result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Error closing position at market price:", result.comment)
    else:
        print(f"Position {position.ticket} closed successfully at market price")

# Variable to store the last checked candle time
last_checked_time = None
# Get the data of last 100 bars and calculate
ha_df = calculate_previous_heiken_ashi()  # Initialize ha_df with 100 previous bars

# Main trading loop
while True:
    df_ohlc = get_ohlc(symbol, num_bars)  # Fetch the latest OHLC data
    if df_ohlc is None:
        continue

    # Check if the candle has completed (new time)
    last_candle_time = df_ohlc['time'].iloc[-2]  # Time of the last completed candle

    if last_checked_time is None or last_candle_time > last_checked_time:
        ha_df = append_live_ha_to_df(df_ohlc, ha_df)  # Append the latest HA data
        print(f"New candle formed at {datetime.fromtimestamp(last_candle_time)}")
        
        # Pass ha_df and df_ohlc to the trade function
        check_heiken_ashi_and_trade(ha_df, df_ohlc)
        
        last_checked_time = last_candle_time  # Update the last checked time

    time.sleep(5)  # Wait 5 seconds before checking again

