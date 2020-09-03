# BinanceMarginTrader
Binance Marging Trading defined in easy functions. You can go long or short assets weather they increase in price or not.
## Skip to
* [Setup](#setup)

## General info

# BinanceMarginTrader

If you find this functions useful please donate here: 

BTC 16VVnTof3c4mGGAMmFQwRzTe3tmuwUF3wt 

ETH 0x914a22f07a8cda8b4ac149beadb38743b1edc106

LINK ERC20 0x914a22f07a8cda8b4ac149beadb38743b1edc106

Margin Trading here is made simpler! =) You can easily open an account, I get 20% of the fees: https://www.binance.com/en/register?ref=26095868

We both get 10% of the fees: https://www.binance.com/en/register?ref=XGD25UFF

Strategy= Define your own. To use at your own risk/peril. Trades in Margin with BUSD pairs as they have lower fees, but the pairs can be changed to any MT pair you like.

## Functions available: What it does

Logs in with your API keys from another file (bikeys.py). Consider a .ini for added security.

Keeps exception logs of any errors with the Rest API/functions/program written in a file with traceback.

Gets historical data from the API and organizes it in a dataframe with OCHLV + VWAP and others values to then analize it.

Identifies the overal bigger picture trend, 1 Hr candls or 2hr candls if sideways to return trend: 'UP', 'DWN' or 'SIDEWYS'

You can build (and easily write) your own strategy, could be based on Moving averages, MACD, VWAP, combined or etc. 
# NOT TESTED: The strategy present here just runs, most likely it is not profitable (email me: carlo.fernandezben@gmail.com to write one)

Goes Long or Short depending on the trend and the strategy chosen, and starts looking for similar pairs faster to trade when volatility increases.

Revises and corrects the position in case there is any fault or exception in the process.

Plots and graphs a snapshot of the chart when going long or short indicating the Take profit point and Stop loss prices.

Continuosly checks the open long TP or short orders and cancels them if trend is oposite to the position or any other desired price or indicator condition.

Use of any DB is not necessary/optional. All in one fast/lite program to trade and leave running when profitable.

## Technologies
Project is a Rest API program created with:
* python: 3.7

	
## Setup
To run this project, install python and run in a virtual env the needed libraries can be added with pip install:

```
$ pandas
$ numpy
$ pyti
$ python-binance or pythonic binance 
$ binance
$ plotly

See others for indicators as pandas-ta
```
python-binance (https://python-binance.readthedocs.io/en/latest/binance.html)
