# Python-MT5
This repo includes my strategies I coded in python for MT5

MetaTrader 5 Heiken Ashi Trading Bot
This Python script connects to MetaTrader 5 (MT5) and implements a trading strategy based on Heiken Ashi candlestick patterns. It fetches live market data, calculates Heiken Ashi candles, and places trades automatically based on predefined conditions.

Features
Heiken Ashi Calculation: Computes Heiken Ashi candles using live OHLC data.
Automated Trading: Places buy/sell orders based on Heiken Ashi patterns.
Position Management: Closes positions when market conditions reverse or become indecisive.
Slippage Handling: Retries orders with increasing slippage values to ensure execution.

Prerequisites
Before running the script, ensure you have the following:
MetaTrader 5 installed on your system.
A demo or live account with MetaTrader 5.
Python 3.x installed.
The MetaTrader5 and pandas Python libraries installed.

Installation
Install Python Libraries:
pip install MetaTrader5 pandas

Update Script Credentials:
Replace the following placeholders in the script with your MT5 account details:
path = "C:\\Program Files\\MetaTrader 5\\terminal64.exe"  # Path to your MT5 terminal
server = "MetaQuotes-Demo"  # Your MT5 server
login = 11111111  # Your MT5 account login
password = "********"  # Your MT5 account password

Usage
The script runs in an infinite loop, checking for new candlestick data every 5 seconds. It performs the following steps:
Fetches the latest OHLC data for the specified symbol (e.g., XAUUSD).
Calculates Heiken Ashi candles.
Evaluates trading conditions based on Heiken Ashi patterns.
Places buy/sell orders or closes existing positions as needed.

Customization
Symbol: Change the symbol variable to trade a different instrument.
Timeframe: Adjust the timeframe variable to use a different candlestick interval.
Wick Threshold: Modify the wick_threshold variable to adjust sensitivity to wick sizes.
Slippage: Update the slippage variable to control acceptable slippage levels.

Example Output
Copy
Initialization successful
New candle formed at 2023-10-01 12:00:00
Completed candle OHLC: Open: 1800.50, Close: 1801.00, High: 1802.00, Low: 1800.00
Completed HA candle OHLC: Open: 1800.75, Close: 1801.25, High: 1802.00, Low: 1800.50
Placing a BUY trade
BUY order placed successfully, order ticket: 123456


Contributions are welcome! If you'd like to improve this project, please:
Fork the repository.
Create a new branch for your feature or bugfix.
Submit a pull request with a detailed description of your changes.

