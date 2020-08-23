#!/usr/bin/python3
from binance.exceptions import BinanceAPIException, BinanceRequestException
from pyti.smoothed_moving_average import smoothed_moving_average as sma
from pyti.bollinger_bands import upper_bollinger_band as ubb # Examples of indicators/strategies
from pyti.bollinger_bands import lower_bollinger_band as lbb # Examples of indicators/strategies
from decimal import Decimal as D, ROUND_DOWN, ROUND_UP
from itertools import tee, islice, chain
from datetime import time, datetime
from binance.client import Client
from plotly.offline import plot
import plotly.graph_objs as go
from binance.enums import *
import pandas_ta as ta # Examples of indicators/strategies
from time import sleep
import pandas as pd
import numpy as np
import traceback
import datetime
import decimal
import hmac
import time
import bikeys

log = open("BinanceMT.txt", "w")
loline = '____________________________________________________________________'
sleepsec = 2.4
trend_count = 0
client = Client(api_key=bikeys.Pass, api_secret=bikeys.Sec)
global trend

pairs = ['BTCBUSD', 'BCHBUSD', 'LTCBUSD', 'ETHBUSD', 'ETCBUSD', 'XRPBUSD',
'EOSBUSD', 'LINKBUSD', 'XTZBUSD', 'BNBBUSD', 'ZILBUSD', 'EOSBUSD', 'ALGOBUSD', 
'ADABUSD', 'SXPBUSD']

def Trend(pair):
    global trend_count
    global pairsmas
    altc = pair[:-4]
    ticker = client.get_symbol_ticker(symbol=pair)
    price = ticker['price']
    print('\n')
    print(f'Start________Gathering Trend for {altc}______Price:{float(price)}______\n')
    candle_no = 480
    interval = Client.KLINE_INTERVAL_2HOUR
    candles = client.get_klines(symbol=pair, interval=interval, limit=candle_no)
    df = pd.DataFrame(data=candles)
    # New lists of data
    open = df.iloc[:,1].astype(float)
    high = df.iloc[:,2].astype(float)
    low = df.iloc[:,3].astype(float)
    close = df.iloc[:,4].astype(float)
    volume = df.iloc[:,5].astype(float)
    no_ofTrades = df.iloc[0:100,[8]]  #This returns as an integer from the API and the last value is incomplete per interval as is ongoing
    # Removes the columns to not use here:
    # df.pop(0)  # Open time
    df.pop(6)  # Close time
    df.pop(7)  # Quote asset volume
    df.pop(9)  # Taker buy base asset volume
    df.pop(10) # Taker buy quote asset volume
    df.pop(11) # Can be ignored
    df.columns = ['Time','Open','High','Low','Close','Volume', 'Trades'] #Titles the colms
    df['Time'] = pd.to_datetime(df['Time'] * 1000000, infer_datetime_format=True)

    # Calculates Smoothed moving avgs
    fastsma = sma(close,14)
    pairsmas = sma(close,30)
    slowsma = sma(close, 50)
    #
    fastsma = float(D("{0:.5f}".format(fastsma[-1])))
    pairsma = float(D("{0:.5f}".format(pairsmas[-1])))
    slowsma = float(D("{0:.5f}".format(slowsma[-1])))
    volma = sma(volume,11)
    # print(volma)
    vol = volma[-2]
    lvol = volma[-1]
    candle_no = candle_no-1
    avg_vol = (sum(volma) - lvol) / candle_no
    vol_perc = vol / avg_vol
    vol_perc_txt = D("{0:.3f}".format(vol_perc))
    print(f'The volume avg is: {vol_perc_txt} times the norm. Approx ~ {vol_perc_txt*100}%')
    # Gets details from other Columns Lows, Highs, No of trades:
    late_no_trades = df.Trades.iat[-1]
    trades = float(df.Trades.iat[-2])
    avg_trades = ((no_ofTrades.sum()) - late_no_trades) /candle_no
    avg_trades = float("{0:.4f}".format(avg_trades[8]))
    # print(f'Number of trades is in the prev. 5mins is {late_no_trades} and average is {avg_trades} in 90 mins')
    trend_lowest = min(low)
    # p_lowest = D("{0:.8f}".format(lowest))
    # print(f'The lowest candle for {altc} is {p_lowest}')
    trend_highest = max(high)
    # Calculates Volume Weighted Avg Price:
    vwap = float(sum(pairsmas))*float(vol)/sum(volma)
    vwap_dec = D("{0:.4f}".format(vwap))
    vwap_ratio = (vwap/float(price))*100
    vwap_ratio = D("{0:.2f}".format(vwap_ratio))
    if vwap_ratio > 100:
        oversold = True
    else:
        oversold = False
    trend = 'SIDEWYS'
    print(f' the VWAP is : {vwap_dec} and that is {vwap_ratio}% of the price')
    late_close = close[99] #The close (interval mins/hrs ago) != price
    if float(price) > fastsma and fastsma > pairsma and pairsma > slowsma:
        print(f'Classic TREND UP for {altc}')
        trend = 'UP'
    elif float(price) > fastsma and fastsma > pairsma:
        if oversold is False and float(price) > slowsma:
            trend = 'UP'
    # __________________________________________________________________
    if slowsma > pairsma and pairsma > fastsma and fastsma > float(price):
        print(f'Classic TREND DWN for {altc}')
        trend = 'DWN'
    elif pairsma > fastsma and fastsma > float(price):
        if float(price) < slowsma and oversold:
            trend = 'DWN'
    if trend == 'SIDEWYS':
        print(f'Trend is Sideways for {altc} on 2h, going for 4h chart')
        if trend_count < 1:
            interval = Client.KLINE_INTERVAL_4HOUR
            trend_count +=1
            Trend(pair)
        else:
            trend = 'SIDEWYS'
            print(f'Trend is Sidewys for {altc} on Daily charts')
    return trend

def Strategy(pair): # Gets precise Precise data and act from it.
    global df
    global altc
    global price
    global profit
    global pairsmas
    global long
    global short
    global up_bb
    global low_bb
    global tme_critical

    altc = pair[:-4]
    ticker = client.get_symbol_ticker(symbol=pair)
    price = ticker['price']
    
    # Pivots the daily candles in case your strategy requires daily a pivot:
    utc = datetime.datetime.utcnow()  # time now
    mid_utc = utc.replace(hour=0, minute=0, second=0, microsecond=0)
    mins_utc = int((mid_utc-utc).total_seconds() / 60.0)*-1 # time in minutes from UTC
    candls_utc = int(mins_utc/5)
    interval = Client.KLINE_INTERVAL_5MINUTE
    if candls_utc < 24:
        if mins_utc < 20:
            mins_utc = 20
        candls_utc = int(mins_utc/3)
        interval = Client.KLINE_INTERVAL_3MINUTE
    daily_factor = 0.40
    if candls_utc > 118:
        daily_factor = candls_utc/296

    candle_no = candls_utc
    m_one = int(candle_no-1)
    print('\n')
    print(f'Start________Gathering Strategy for {altc}__________Trend:{trend}______\n')
    print(f'From utc--- {candls_utc} :{interval} Candles')
    candles = client.get_klines(symbol=pair, interval=interval, limit=candle_no)
    df = pd.DataFrame(data=candles)
    # New lists of data
    open = df.iloc[:,1].astype(float)
    high = df.iloc[:,2].astype(float)
    low = df.iloc[:,3].astype(float)
    close = df.iloc[:,4].astype(float)
    volume = df.iloc[:,5].astype(float)
    no_ofTrades = df.iloc[0:100,[8]]  #This returns as an integer from the API and the last value is incomplete per interval as is ongoing
    # Removes the columns to not use here:
    # df.pop(0)  # Open time
    df.pop(6)  # Close time
    df.pop(7)  # Quote asset volume
    df.pop(9)  # Taker buy base asset volume
    df.pop(10) # Taker buy quote asset volume
    df.pop(11) # Can be ignored
    df.columns = ['time','open','high','low','close','volume','trades'] #Titles the colms
    df['time'] = pd.to_datetime(df['time'] * 1000000, infer_datetime_format=True)

    open = np.array(open)
    l_open = float(open[-1])

    if candls_utc < 7:
        fastsma = sma(close, int(candls_utc))
    else:
        fastsma = sma(close, 7)
    fastsma = float(fastsma[-1])
    fiftysma = sma(close, 50)
    fiftysma = float(fiftysma[-1])
    highest = max(high)
    avg_high = float(sum(high)+highest/int(len(high)+1))
    lowest = min(low)
    avg_low = float(sum(low)+lowest/int(len(low)+1))
    up_bb = ubb(close, 7, 3.0)
    lup_bb = up_bb[-1]

    low_bb = lbb(close, 7, 3.0)
    llow_bb = low_bb[-1]

    print(f'The current Upper BB value: {lup_bb}')
    print(f'The current Lower BB value: {llow_bb}')

    diff = (float(lup_bb) - float(llow_bb))
    profit = float(diff/float(price)) + 1
    print(f'\n The trading profit for {altc} is potentially {profit} or {profit*float(price)}')
    price = float(price)
    print(loline)

    long = False
    short = False
    tme_critical = False

    if profit > 1.007 and profit < 1.033:  #Lateral
        scale = profit*0.009
        profit = 1.0116 + scale
        if price <= float(llow_bb)*0.9984 and l_open < fastsma:
            tme_critical = True
            if price <= float(llow_bb)*1.0033 and float(llow_bb) < fastsma and fastsma*1.002 < lvwap:
                if trend == 'UP' or trend == 'SIDEWYS':
                    long = True
                    print(f'\n Very cheap state vs VWAP and smma,. looking to long {altc} for a {profit} prof')
            else:
                print('Almost there')
        if price >= float(lup_bb)*1.0016 and l_open > fastsma:
            tme_critical = True
            if price > float(lup_bb)*0.9967 and float(lup_bb) > fastsma and fastsma*0.998 > lvwap:
                if trend == 'DWN' or trend == 'SIDEWYS':
                    short = True
                    print(f'\n Price is a very high vs VWAP and smma,. looking to short {altc} for a {profit} prof')
            else:
                print('Almost there')

    elif profit >= 1.033: #Pumping
        if price >= fiftysma and l_open > fastsma:
            tme_critical = True
            if price >= avg_high:
                if trend == 'UP' or trend == 'SIDEWYS': # If trend is UP or SIDEWYS
                    long = True
                    print(f'\n Pumping but cheap state vs VWAP and smma,. looking to long {altc} for a {profit} prof')
            else:
                print('Almost there')
        if price <= fiftysma and l_open < fastsma:
            tme_critical = True
            if price <= avg_low:
                if trend == 'DWN' or trend == 'SIDEWYS': # If trend is DWN or SIDEWYS
                    short = True
                    print(f'\n Price is falling vs VWAP and smma,. looking to short {altc} for a {profit} prof')
            else:
                print('Almost there')
    else:
        print(f'\n Not there yet')

    return long
    return short
    return tme_critical

def OpenOrder(price):
    global noLongPosition
    global noShortPosition
    altc = pair[:-4]
    print(f'Checking open order on {altc}')
    open_order = client.get_open_margin_orders(symbol= pair)
    has_data = float(len(open_order))
    noShortPosition= True
    noLongPosition = True
    if has_data > 0:
        for i in range(len(open_order)):
            orig_quant = float(open_order[i]['origQty'])
            # exec_quant = float(open_order[i]['executedQty'])
            orderId = int(open_order[i]['orderId'])
            type = str((open_order[i]['type']))
            side = str((open_order[i]['side']))
            takeprofit = str((open_order[i]['price']))
            takeprof = float(takeprofit)
            time = pd.to_datetime(float(open_order[i]['price']), infer_datetime_format=True)
            print(f'!!!!!\n ___Order of {orig_quant} units of {altc} at price of {takeprof} time{time}!!\n ')
            if side == 'SELL':  # -----------------------This is a long position
                print(open_order)
                print('\n There s an open TP Sell order here,.. \n')
                noLongPosition = False
                if price >= lup_vwap_b and float(price/takeprof) >= 0.9916:  #Price is up + bad position
                    info = client.get_symbol_info(symbol=pair)
                    price_filter = float(info['filters'][0]['tickSize'])
                    ticker = client.get_symbol_ticker(symbol=pair)
                    price = float(ticker['price'])
                    price = D.from_float(price).quantize(D(str(price_filter)))
                    minimum = float(info['filters'][2]['minQty']) # 'minQty'
                    quant = D.from_float(orig_quant).quantize(D(str(minimum)))
                    result = client.cancel_margin_order(symbol= pair, orderId= orderId)
                    print('Price is up now + bad position!, Order cancelled')
                    try:
                        order = client.create_margin_order(symbol=pair,
                            side=SIDE_SELL,
                            type=ORDER_TYPE_MARKET,
                            quantity= quant)
                        print(f'Market sold {pair}')
                    except Exception as e:
                        traceback.print_exc(file=log)
                        print(e)
                        try:
                            sleep(2)
                            order = client.create_margin_order(
                                symbol=pair,
                                side=SIDE_SELL,
                                type=ORDER_TYPE_MARKET,
                                quantity=quant)
                            print(f'Market sold {pair}')
                        except Exception as e:
                            traceback.print_exc(file=log)
                            print(e)
                    RepayUSD()
                    noLongPosition = True
                    print(f'Sell order for {altc} cleared')
                elif trend == 'DWN' or float(price/takeprof) >= 0.9916:
                    info = client.get_symbol_info(symbol=pair)
                    price_filter = float(info['filters'][0]['tickSize'])
                    ticker = client.get_symbol_ticker(symbol=pair)
                    price = float(ticker['price'])
                    price = D.from_float(price).quantize(D(str(price_filter)))
                    minimum = float(info['filters'][2]['minQty']) # 'minQty'
                    quant = D.from_float(orig_quant).quantize(D(str(minimum)))
                    result = client.cancel_margin_order(symbol= pair, orderId= orderId)
                    print('Price is up now + bad position!, Order cancelled')
                    try:
                        order = client.create_margin_order(symbol=pair,
                            side=SIDE_SELL,
                            type=ORDER_TYPE_MARKET,
                            quantity= quant)
                        print(f'Market sold {pair}')
                    except Exception as e:
                        traceback.print_exc(file=log)
                        print(e)
                        try:
                            sleep(2)
                            order = client.create_margin_order(
                                symbol=pair,
                                side=SIDE_SELL,
                                type=ORDER_TYPE_MARKET,
                                quantity=quant)
                            print(f'Market sold {pair}')
                        except Exception as e:
                            traceback.print_exc(file=log)
                            print(e)
                    RepayUSD()
                    noLongPosition = True
                    print(f'Sell order for {altc} cleared')
                else:
                    print(f'Sell order for {altc} stays')
                return noLongPosition
            if side == 'BUY':  # -----------------------This is a Short position
                print(open_order)
                print('\n There is an open TP Buy lower order here already \n')
                noShortPosition = False
                if price <= llow_vwap_b and float(price/takeprof) <= 1.0084: #price dwn + bad position
                    info = client.get_symbol_info(symbol=pair)
                    price_filter = float(info['filters'][0]['tickSize'])
                    ticker = client.get_symbol_ticker(symbol=pair)
                    price = float(ticker['price'])
                    price = D.from_float(price).quantize(D(str(price_filter)))
                    minimum = float(info['filters'][2]['minQty']) # 'minQty'
                    quant = D.from_float(orig_quant).quantize(D(str(minimum)), rounding=ROUND_UP)
                    result = client.cancel_margin_order(symbol= pair, orderId= orderId)
                    print('This is a loosing position, StopLoss: Order cancelled')
                    try:
                        order = client.create_margin_order(symbol=pair,
                            side=SIDE_BUY,
                            type=ORDER_TYPE_MARKET,
                            quantity= quant)
                        print(f'Market bought {pair} to repay')
                    except Exception as e:
                        traceback.print_exc(file=log)
                        print(e)
                        try:
                            order = client.create_margin_order(
                                symbol=pair,
                                side=SIDE_BUY,
                                type=ORDER_TYPE_MARKET,
                                quantity=quant)
                            print(f'Market bought {pair} to repay')
                        except Exception as e:
                            traceback.print_exc(file=log)
                            print(e)
                    RepayAltc()
                    noShortPosition= True
                    print(f'Buy order for {altc} cleared')
                elif trend == 'UP' or float(price/takeprof) <= 1.0084:
                    info = client.get_symbol_info(symbol=pair)
                    price_filter = float(info['filters'][0]['tickSize'])
                    ticker = client.get_symbol_ticker(symbol=pair)
                    price = float(ticker['price'])
                    price = D.from_float(price).quantize(D(str(price_filter)))
                    minimum = float(info['filters'][2]['minQty']) # 'minQty'
                    quant = D.from_float(orig_quant).quantize(D(str(minimum)), rounding=ROUND_UP)
                    result = client.cancel_margin_order(symbol= pair, orderId= orderId)
                    print('This is a loosing position, StopLoss: Order cancelled')
                    try:
                        order = client.create_margin_order(symbol=pair,
                            side=SIDE_BUY,
                            type=ORDER_TYPE_MARKET,
                            quantity= quant)
                        print(f'Market bought {pair} to repay')
                    except Exception as e:
                        traceback.print_exc(file=log)
                        print(e)
                        try:
                            order = client.create_margin_order(
                                symbol=pair,
                                side=SIDE_BUY,
                                type=ORDER_TYPE_MARKET,
                                quantity=quant)
                            print(f'Market bought {pair} to repay')
                        except Exception as e:
                            traceback.print_exc(file=log)
                            print(e)
                    RepayAltc()
                    noShortPosition= True
                    print(f'Buy order for {altc} cleared')
                else:
                    print(f'Buy order for {altc} stays for now')
                return noShortPosition
    else:
        print(f'There are no open orders for {altc}')

def RepayUSD():
    print(f'^ Checking free balances on BUSD')
    info = client.get_symbol_info(symbol='ADABUSD')
    minimum = float(info['filters'][2]['minQty']) # 'minQty'
    dict_balanc = client.get_margin_account()
    balances = (dict_balanc['userAssets'])
    for i in balances:
        if str('BUSD') == i['asset'] and float(i['free']) > 0.00001 and float(i['borrowed']) > 10:
                loaned = float(i['borrowed'])
                quant = float(i['free'])
                print(f'There are {quant} USD free, waiting')
                quant1 = D.from_float(quant).quantize(D(str(minimum)), rounding=ROUND_DOWN)
                print(f'The balance of BUSD wallet is {quant1}')
                sleep(5)
                dict_balanc = client.get_margin_account()
                balances = (dict_balanc['userAssets'])
                for i in balances:
                    if str('BUSD') == i['asset'] and float(i['free']) > 0.00001:
                            quant2 = float(i['free'])
                            print(f'There are {quant2} USD free, comparing')
                            quant2 = D.from_float(quant2).quantize(D(str(minimum)), rounding=ROUND_DOWN)
                if float(quant) > 10 and quant1 == quant2 and loaned > 10:
                    print(f'Checking BUSD for a repay of the free amount')
                    try:
                        quant = D.from_float(quant).quantize(D(str(minimum)))
                        repay = client.repay_margin_loan(asset='BUSD', amount= quant)
                        print(f'Repayed the collateral for {pair} 1st try')
                    except Exception as e:
                        traceback.print_exc(file=log)
                        print(e)
                        try:
                            repay = client.repay_margin_loan(asset='BUSD', amount= quant)
                            print(f'Repayed the collateral for {pair} 2nd try')
                        except Exception as e:
                            traceback.print_exc(file=log)
                            print(e)
                if float(quant) > 10 and quant1 == quant2 and float(quant) > loaned:
                    print(f'Checking BUSD for a repay of the free amount')
                    try:
                        loaned = D.from_float(loaned).quantize(D(str(minimum)), rounding=ROUND_DOWN)
                        repay = client.repay_margin_loan(asset='BUSD', amount= loaned)
                        print(f'Repayed the collateral for BUSD 1st try')
                    except Exception as e:
                        traceback.print_exc(file=log)
                        print(e)
                if float(quant) > 10 and loaned > 10:
                    repay = client.repay_margin_loan(asset='BUSD', amount= quant)
                    print(f'Repayed the collateral for BUSD 1st try')
        elif str('BUSD') == i['asset'] and float(i['borrowed']) < 10:
            print('No borrowed amount')

def RepayAltc():
    print(f'^ Checking free balances on {altc}')
    info = client.get_symbol_info(symbol=pair)
    minimum = float(info['filters'][2]['minQty']) # 'minQty'
    dict_balanc = client.get_margin_account()
    balances = (dict_balanc['userAssets'])
    for i in balances:
        dollars = 0
        if str('BUSD') == i['asset'] and float(i['free']) > 10:
            dollars = float(i['free'])
        if str(altc) == i['asset'] and float(i['free']) >= minimum and float(i['borrowed']) >= minimum:
                loan = float(i['borrowed'])
                loaned = float("{0:.6f}".format(loan))
                quant = float(i['free'])
                print(f'There are {quant} {altc} free, waiting')
                quant1 = D.from_float(quant).quantize(D(str(minimum)), rounding=ROUND_DOWN)
                print(f'The balance of {altc} wallet is {quant1}')
                sleep(7)
                dict_balanc = client.get_margin_account()
                balances = (dict_balanc['userAssets'])
                if loaned > minimum:
                    if noShortPosition and noLongPosition:
                        try:
                            repay = client.repay_margin_loan(asset=altc, amount= quant)
                            print(f'Repayed the {altc} debt')
                        except Exception as e:
                            traceback.print_exc(file=log)
                            print(e)
                            try:
                                loaned = quant - loaned
                                loaned=D.from_float(loaned).quantize(D(str(minimum)))
                                order = client.create_margin_order(
                                    symbol= pair,
                                    side=SIDE_BUY,
                                    type=ORDER_TYPE_MARKET,
                                    quantity=loaned)
                                print(f'Market bought {altc} to repay borrowed debt')
                                sleep(20)
                                repay = client.repay_margin_loan(asset=altc, amount= quant)
                                print(f'Repayed the {altc} debt')
                            except Exception as e:
                                traceback.print_exc(file=log)
                                print(e)
                                try:
                                    order = client.create_margin_order(
                                        symbol= pair,
                                        side=SIDE_BUY,
                                        type=ORDER_TYPE_MARKET,
                                        quantity=loaned)
                                    print(f'Market bought {altc} to repay borrowed debt')
                                    sleep(16)
                                    repay = client.repay_margin_loan(asset=altc, amount= quant)
                                    print(f'Market bought {altc} to repay borrowed debt')
                                except Exception as e:
                                    traceback.print_exc(file=log)
                                    print(e)
                                    try:
                                        order = client.create_margin_order(
                                            symbol= pair,
                                            side=SIDE_BUY,
                                            type=ORDER_TYPE_MARKET,
                                            quantity=loaned)
                                        print(f'Market bought {altc} to repay borrowed debt')
                                        sleep(20)
                                        repay = client.repay_margin_loan(asset=altc, amount= dollars)
                                        print(f'Market bought {altc} to repay borrowed debt')
                                    except Exception as e:
                                        traceback.print_exc(file=log)
                                        print(e)
                    elif noShortPosition and noLongPosition:
                        try:
                            repay = client.repay_margin_loan(asset=altc, amount= quant)
                            print(f'Repayed the {altc} debt')
                        except Exception as e:
                            repay = client.repay_margin_loan(asset=altc, amount= loaned)
                            print(f'Repayed the {altc} debt on 2nd try')
                            traceback.print_exc(file=log)
                            print(e)
        elif str(altc) == i['asset'] and float(i['borrowed']) < 0.00001:
            print('No borrowed amount')

def Long(pair):
    try:
        print(loline)
        ticker = client.get_symbol_ticker(symbol=pair)
        price = ticker['price']
        price = float(price)
        price = float("{0:.5f}".format(price))
        max_loan = client.get_max_margin_loan(asset='BUSD') # Whats the max margin I get?
        max_loan = float(max_loan['amount'])
        loan = max_loan/6
        loan = float(loan)
        loan = float("{0:.5f}".format(loan))
        print(f' the loan amnt is {loan} out of the max of: {max_loan}')
        if max_loan >= 130 and profit > 1.00933:
            transaction = client.create_margin_loan(asset='BUSD', amount=loan)  # Borrows longing asset prepares to Buy> Sale Higher > Repay BUSD
            print(transaction)
            asset = 'BUSD'
            info = client.get_symbol_info(symbol=pair)
            minimum = float(info['filters'][2]['minQty']) # 'minQty'
            price_filter = float(info['filters'][0]['tickSize'])
            price = D.from_float(price).quantize(D(str(price_filter)))
            quant = loan/float(price)
            quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
            try:
                print(f'Borrowed BUSD and Market buying {altc}')
                order = client.create_margin_order(
                    symbol= pair,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_MARKET,
                    quantity=quant)
                sleep(21)
                print(f'Borrowed BUSD and Market bought {altc}')
            except Exception as e:
                traceback.print_exc(file=log)
                print(e)
                try:
                    price = float(client.get_orderbook_ticker(symbol=str(pair))['askPrice'])
                    price = D.from_float(price).quantize(D(str(price_filter)))
                    print('failed to market buy, going for limit on ask price')
                    order = client.create_margin_order(
                        symbol= pair,
                        side=SIDE_BUY,
                        type=ORDER_TYPE_LIMIT,
                        timeInForce=TIME_IN_FORCE_GTC,
                        quantity=quant,
                        price=price)
                    print(f'Borrowed BUSD and bought {altc}, waiting on order to go trw')
                    sleep(16)
                except Exception as e:
                    dict_balanc = client.get_margin_account()
                    balances = (dict_balanc['userAssets'])
                    for i in balances:
                        if str(altc) == i['asset'] and float(i['free']) > 0.00:
                                quant = float(i['free'])
                                print(quant)
                                quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
                                print(f'The fucking balance of {altc} wallet is {quant}')
                                order = client.create_margin_order(
                                    symbol= pair,
                                    side=SIDE_BUY,
                                    type=ORDER_TYPE_LIMIT,
                                    timeInForce=TIME_IN_FORCE_GTC,
                                    quantity=quant,
                                    price=price)
                                print(f'Borrowed BUSD and bought {altc}, waiting on order to go trw')
                    traceback.print_exc(file=log)
                    print(e)
            try:
                print(f'Attempting TP planned at {profit} parts of {price} for {altc} !****')
                price = float(price)
                dict_balanc = client.get_margin_account()
                balances = (dict_balanc['userAssets'])
                for i in balances:
                    if str(altc) == i['asset'] and float(i['free']) > 0.00000001:
                            quant = float(i['free'])
                            print(quant)
                            quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
                            print(f'The balance of {altc}s wallet is {quant}')
                profitL = float(profit-1)
                profitLong = profitL + 1
                price = price*profitLong
                price_filter = float(info['filters'][0]['tickSize'])
                price = D.from_float(price).quantize(D(str(price_filter)))
                order = client.create_margin_order(
                    symbol= pair,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_LIMIT,
                    timeInForce=TIME_IN_FORCE_GTC,
                    quantity=quant,
                    price=price)
                print(f' *******Limit SELL order made: {quant} of {altc} * @ * {price} *****')
                print(f'Borrowed BUSD and bought {altc}, set TP at {price} for {altc}')
                Plot(pair, profit)
            except Exception as e:
                traceback.print_exc(file=log)
                print(e)
                sleep(16)
                print(f'Error with TP trying again')
                try:
                    quant = (float(quant)/float(price))*0.9925    #Lesser amount left after fees
                    quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
                    order = client.create_margin_order(
                        symbol= pair,
                        side=SIDE_SELL,
                        type=ORDER_TYPE_LIMIT,
                        timeInForce=TIME_IN_FORCE_GTC,
                        quantity=quant,
                        price=price)
                    print(f' *******Limit SELL order made: {quant} of {altc} * @ * {price} *****')
                    print(f'Borrowed BUSD and bought {altc}, set TP at {price} for {altc}')
                    Plot(pair, profit)
                except Exception as e:
                    traceback.print_exc(file=log)
                    print(e)
                    print(f'Error with TP trying again:')
                    try:
                        quant = float(quant)*0.9925   #amount before fees
                        quant = D.from_float(quant).quantize(D(str(minimum)))
                        order = client.create_margin_order(
                            symbol= pair,
                            side=SIDE_SELL,
                            type=ORDER_TYPE_LIMIT,
                            timeInForce=TIME_IN_FORCE_GTC,
                            quantity=quant,
                            price=price)
                        print(f' *******Limit SELL order made: {quant} of {altc} * @ * {price} *****')
                        print(f'Borrowed BUSD and bought {altc}, set TP at {price} for {altc}')
                        Plot(pair, profit)
                    except Exception as e:
                        traceback.print_exc(file=log)
                        print(e)
                        try:
                            quant = float(quant)*0.9925   #amount before fees
                            quant = D.from_float(quant).quantize(D(str(minimum)))
                            order = client.create_margin_order(
                                symbol= pair,
                                side=SIDE_SELL,
                                type=ORDER_TYPE_LIMIT,
                                timeInForce=TIME_IN_FORCE_GTC,
                                quantity=quant,
                                price=price)
                            print(f' *******Limit SELL order made: {quant} of {altc} * @ * {price} *****')
                            print(f'Borrowed BUSD and bought {altc}, set TP at {price} for {altc}')
                            Plot(pair, profit)
                        except Exception as e:
                            traceback.print_exc(file=log)
                            print(e)
        else:
            print('******** Not enough margin left, or profit opportunity is low *****')
            sleep(sleepsec)
    except Exception as e:
        traceback.print_exc(file=log)
        print(e)
        sleep(1)

def Short(pair):
    try:
        print(loline)
        ticker = client.get_symbol_ticker(symbol=pair)
        price = ticker['price']
        price = float(price)
        price = float("{0:.5f}".format(price))
        max_loan = client.get_max_margin_loan(asset=altc) # Whats the max margin I get?
        max_loan = float(max_loan['amount'])
        loan = max_loan/6
        loan = float(loan)
        loan = float("{0:.5f}".format(loan))
        print(f' the loan amnt is {loan} out of the max of: {max_loan}')
        if max_loan >= 148/price and float(profit) > 1.00933:
            transaction = client.create_margin_loan(asset=altc, amount=loan)  # Borrows shorting asset prepares to SELL> Rebuy lower > Repay altc
            print(transaction)
            asset = altc
            info = client.get_symbol_info(symbol=pair)
            price_filter = float(info['filters'][0]['tickSize'])
            price = D.from_float(price).quantize(D(str(price_filter)))
            quant = loan
            minimum = float(info['filters'][2]['minQty']) # 'minQty'
            quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
            try:
                print(f'Borrowing {altc} and market selling to short')
                order = client.create_margin_order(
                    symbol= pair,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=quant)
                sleep(20)
                print(f'Borrowed {altc} and market sold FOR BUSD')
            except Exception as e:
                print(f'Error with Order trying again ***************')
                traceback.print_exc(file=log)
                print(e)
                try:
                    price_filter = float(info['filters'][0]['tickSize'])
                    price = float(client.get_orderbook_ticker(symbol=str(pair))['bidPrice'])
                    price = D.from_float(price).quantize(D(str(price_filter)))
                    order = client.create_margin_order(
                        symbol= pair,
                        side=SIDE_SELL,
                        type=ORDER_TYPE_LIMIT,
                        timeInForce=TIME_IN_FORCE_GTC,
                        quantity=quant,
                        price=price)
                    print(f'Borrowed {altc} and set a buy for bidPrice {price}, waiting on order to go trw')
                    sleep(21)
                except Exception as e:
                    try:
                        print(f'Error with {altc} sell, market selling to short')
                        order = client.create_margin_order(
                            symbol= pair,
                            side=SIDE_SELL,
                            type=ORDER_TYPE_MARKET,
                            quantity=quant)
                        sleep(16)
                        print(f'Sold {altc} at market FOR BUSD')
                    except Exception as e:
                        try:
                            info = client.get_symbol_info(symbol=pair)
                            price_filter = float(info['filters'][0]['tickSize'])
                            price = D.from_float(price).quantize(D(str(price_filter)))
                            minimum = float(info['filters'][2]['minQty']) # 'minQty'
                            quant = loan
                            dict_balanc = client.get_margin_account()
                            balances = (dict_balanc['userAssets'])
                            for i in balances:
                                if str(altc) == i['asset'] and float(i['free']) > 0.00:
                                        quant1 = float(i['free'])
                                        print(f'There are {quant1} {altc} free')
                                        sleep(2)
                                        print(f'The fucking balance of {altc} wallet is {quant}')
                            quant = D.from_float(quant1).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
                            order = client.create_margin_order(
                                symbol= pair,
                                side=SIDE_SELL,
                                type=ORDER_TYPE_MARKET,
                                quantity=quant)
                        except BinanceAPIException as e:
                            traceback.print_exc(file=log)
                            try:
                                info = client.get_symbol_info(symbol=pair)
                                price_filter = float(info['filters'][0]['tickSize'])
                                price = D.from_float(price).quantize(D(str(price_filter)))
                                minimum = float(info['filters'][2]['minQty']) # 'minQty'
                                dict_balanc = client.get_margin_account()
                                balances = (dict_balanc['userAssets'])
                                for i in balances:
                                    if str(altc) == i['asset'] and float(i['free']) > 0.00:
                                            quant = float(i['free'])
                                            print(quant)
                                            quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
                                            print(f'The fucking balance of {altc} wallet is {quant}')
                                order = client.create_margin_order(
                                    symbol= pair,
                                    side=SIDE_SELL,
                                    type=ORDER_TYPE_MARKET,
                                    quantity=quant)
                                print(f'Sold {altc} at market for ~{quant*price} BUSD')
                            except BinanceAPIException as e:
                                traceback.print_exc(file=log)
                                print(f'*****   Error with the order reverted and repyaing margin ************!!!!')
                                order = client.create_margin_order(
                                    symbol= pair,
                                    side=SIDE_BUY,
                                    type=ORDER_TYPE_MARKET,
                                    quantity=quant)
                                sleep(16)
                                print(f' Bought {altc} back, repyaing {altc},..')
                                quant = float(quant)*0.9995
                                quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
                                repay = client.repay_margin_loan(asset=altc, amount= quant)
                                print(f'Margin of {altc} of {quant} repayed')
                                print(e)
            profitS = float(profit-1)
            profitShort = profitS+1
            short_prof = 2-profitShort
            info = client.get_symbol_info(symbol=pair)
            price = float(price)*float(short_prof)
            price_filter = float(info['filters'][0]['tickSize'])
            price = D.from_float(price).quantize(D(str(price_filter)))
            minimum = float(info['filters'][2]['minQty']) # 'minQty'
            quant = loan #*0.9995?
            minimum = float(info['filters'][2]['minQty']) # 'minQty'
            quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
            dict_balanc = client.get_margin_account()
            balances = (dict_balanc['userAssets'])
            for i in balances:
                if str('BUSD') == i['asset'] and float(i['free']) > 0.00:
                        quant1 = float(i['free'])
                        print(quant)
                        quant1 = D.from_float(quant1).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
                        print(f'The fucking balance of BUSD wallet is {quant1}')
            print(f'TP planned at {2-profit} parts of {quant} at price of: {price} for {altc}')
            try:
                order = client.create_margin_order(
                    symbol= pair,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_LIMIT,
                    timeInForce=TIME_IN_FORCE_GTC,
                    quantity=quant,
                    price=price)
                print(f' *******Limit BUY order made: {quant} of {altc} * @ * {price} *****')
                print(f'Borrowed BUSD and bought {altc}, setting TP at {profit}at: {price} for {altc}')
                ShortPlot(pair, profit)
            except Exception as e:
                traceback.print_exc(file=log)
                try:
                    quant = float(quant)*0.9995
                    quant = D.from_float(quant).quantize(D(str(minimum)), rounding= decimal.ROUND_DOWN)
                    order = client.create_margin_order(
                        symbol= pair,
                        side=SIDE_BUY,
                        type=ORDER_TYPE_LIMIT,
                        timeInForce=TIME_IN_FORCE_GTC,
                        quantity=quant,
                        price=price)
                    print(f' *******Limit BUY order made: {quant} of {altc} * @ * {price} *****')
                    print(f'Borrowed BUSD and bought {altc}, setting TP at {profit}at: {price} for {altc}')
                    ShortPlot(pair, profit)
                except Exception as e:
                    traceback.print_exc(file=log)
                    print(e)
        else:
            print('******** Not enough margin left, or profit opportunity *****')
    except Exception as e:
        traceback.print_exc(file=log)
        print(e)

def ShortPlot(pair, profit):
    buy_signals = []
    try:
        for item, prce in zip (pairsmas, close):
            if item >= 1.0055*prce:
                buy_signals.append([df['time'][i], close[prce]])
            if item == item[-1]:
                buy_signals.append([df['time'][i], close[prce]])
    except Exception as e:
        print(e)
        pass
    # Amount target to be gained from Buy2sell:
    profit = profit-2  # BTC -s fees = 0.0015*quant traded
    profit = profit*-1
    # Stop loss target for Stop out sell limit orders
    stop_out = float(1.06) # 0.06 loss At Sell TP
    # plot candlestick chart
    def Ploting(df, pairsmas, up_bb, low_bb, sell_signals):
        candle = go.Candlestick(
            x = df['time'],
            open = df['open'],
            close = df['close'],
            high = df['high'],
            low = df['low'],
            name = str(altc))
        # plot MAs
        ssma = go.Scatter(
            x = df['time'],
            y = pairsmas,
            name = "SMA",
            line = dict(color = ('rgba(102, 207, 255, 50)'), width = 1))

        upbb = go.Scatter(
            x = df['time'],
            y = up_bb,
            name = "Upper BB",
            line = dict(color = ('rgba(202, 107, 255)'),dash = 'solid',
            shape = 'spline',
            smoothing = 1,
            width = 2))
        lwbb = go.Scatter(
            x = df['time'],
            y = low_bb,
            name = "Lower BB",
            line = dict(color = ('rgba(202, 107, 255)'),dash = 'solid',
            shape = 'spline',
            smoothing = 1,
            width = 2))

        shorts = go.Scatter(
            x = [item[0] for item in sell_signals],
            y = [item[1] for item in sell_signals],
            name = "Short Signals",
            mode = "markers",
            )
        buyTPs = go.Scatter(
            x = [item[0] for item in sell_signals],
            y = [item[1]*profit for item in sell_signals],
            name = "TP Point",
            mode = "markers",
            )
        stops = go.Scatter(
            x = [item[0] for item in sell_signals],
            y = [item[1]*stop_out for item in sell_signals],
            name = "Stops",
            mode = "markers",
            )
        data = go.Data([candle, ssma, upbb, lwbb, shorts ,buyTPs, stops])
        # style and display
        layout = go.Layout(title = f'{pair}_{price}_Shorts 5m')
        fig = go.Figure(data = data, layout = layout)
        plot(fig, filename = str(f'{pair}_5m' + '.html'))

    # Ploting(df,pairsmas, up_bb, low_bb, sell_signals)
    print('Sleeping 25secs')
    sleep(1)
    return Ploting(df,pairsmas, up_bb, low_bb, sell_signals)

def Plot(pair, profit):
    buy_signals = []
    try:
        for item, prce in zip (pairsmas, close):
            if item <= 0.9945*prce:
                buy_signals.append([df['time'][i], close[prce]])
            if item == item[-1]:
                buy_signals.append([df['time'][i], close[prce]])
    except Exception as e:
        print(e)
        pass
    # Amount target to be gained from Buy2sell:
    profit = profit  # BTC -s fees = 0.0015*quant traded
    # Stop loss target for Stop out sell limit orders
    stop_out = float(0.94) # 0.05 loss At Sell TP
    # plot candlestick chart
    def Ploting(df, pairsmas, up_bb, low_bb, buy_signals):
        candle = go.Candlestick(
            x = df['time'],
            open = df['open'],
            close = df['close'],
            high = df['high'],
            low = df['low'],
            name = str(altc))

        # plot MAs
        ssma = go.Scatter(
            x = df['time'],
            y = df['VWAP'],
            name = "VWAP",
            line = dict(color = ('rgba(102, 207, 255, 50)'), width = 1))

        upbb = go.Scatter(
            x = df['time'],
            y = up_bb,
            name = "Upper BB",
            line = dict(color = ('rgba(202, 107, 255)'),dash = 'solid',
            shape = 'spline',
            smoothing = 1,
            width = 2))
        lwbb = go.Scatter(
            x = df['time'],
            y = low_bb,
            name = "Lower BB",
            line = dict(color = ('rgba(202, 107, 255)'),dash = 'solid',
            shape = 'spline',
            smoothing = 1,
            width = 2))

        buys = go.Scatter(
            x = [item[0] for item in buy_signals],
            y = [item[1] for item in buy_signals],
            name = "Buy Signals",
            mode = "markers",
            )

        sells = go.Scatter(
            x = [item[0] for item in buy_signals],
            y = [item[1]*profit for item in buy_signals],
            name = "Sell Signals",
            mode = "markers",
            )
        stops = go.Scatter(
            x = [item[0] for item in buy_signals],
            y = [item[1]*stop_out for item in buy_signals],
            name = "Stop Signals",
            mode = "markers",
            )
        data = go.Data([candle, ssma, upbb, lwbb, buys ,sells, stops])
        # style and display
        layout = go.Layout(title = f'{pair}_{price}_ 5m')
        fig = go.Figure(data = data, layout = layout)
        plot(fig, filename = str(f'{pair}_5m' + '.html'))

try:
    while True:
        try:
            for pair in pairs:
                trend = Trend(pair)
                Strategy(pair)
                OpenOrder(price)
                if long:
                    if noLongPosition:
                        Long(pair)
                elif short:
                    if noShortPosition:
                        Short(pair)
                elif not tme_critical:
                    print(f'Taking our time')
                    RepayAltc()
                    RepayUSD()
                    sleep(sleepsec)
        except Exception as e:
            print(traceback.format_exc())
            traceback.print_exc(file=log)
            print(e)
            pass
except KeyboardInterrupt:
    pass
