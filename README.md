# BinanceMarginTrader
Binance Marging Trading defined in easy functions
## Table of contents
* [Technologies](#technologies)
* [Setup](#setup)

## General info

# BinanceMarginTrader

If you find this functions useful please donate here: 

BTC 16VVnTof3c4mGGAMmFQwRzTe3tmuwUF3wt 

ETH 0x914a22f07a8cda8b4ac149beadb38743b1edc106

LINK ERC20 0x914a22f07a8cda8b4ac149beadb38743b1edc106

Margin Trading here is made simpler! =) You can easily open an account, I get 20% of the fees: https://www.binance.com/en/register?ref=26095868
We both get 10% of the fees: https://www.binance.com/en/register?ref=XGD25UFF

Strategy= Define your own. To use at your own risk/peril.

## Functions available:

Safely logs in with your API keys in another file.

Keeps exception logs of any errors with the Rest API/functions/program in a txt file.

Identifies the overal bigger picture, 1-2 Hr candls to return trend: 'UP', 'DWN' or 'SIDEWYS'

You can build (and easily write) your own strategy, could be Moving averages, MACD, VWAP or etc. based 
# (email me: carlo.fernandezben@gmail.com to write one.)

Goes Long or Short depending on the strategy, and corrects the position in case there is any fault or exception in the process.

Continuosly checks the open long or short orders and cancels them if trend is oposite to the position or any other desired price condition.

Use of any DB is not necessary/optional.
	
## Technologies
Project is created with:
* python: 3.7

	
## Setup
To run this project, install python and run in a virtual env the needed libraries:

```
$ pandas
$ numpy
$ pyti
$ python-binance or pythonic binance
$ binance
See others for indicators as pandas-ta
```
