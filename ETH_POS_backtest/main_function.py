import pandas as pd
from function import *
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

pd.set_option('expand_frame_repr', False)  # 当列太多时不换行
pd.set_option('display.max_rows', 5000)  # 最多显示数据的行数


def smart_back_test(df, week , step):
    can_sell = False  # 是否允许卖出
    days = 200  # 均线日期D
    region = 0.1  # 单位范围X
    step = step  # 单位定投率Y
    initial_capital = 1000000
    defi_yearly_apr = 0 #  假定 套利的XX%的年化收益率
    weekly_apr = (defi_yearly_apr+1) ** (1/52)-1
    invest_cash = 10000  # 每次的基准定投金额
    week = week  # 每周几定投。0代表周一，1代表周二，以此类推
    trade_rate = 0.2/100

    # 计算均线
    df['ma'] = df['close'].rolling(days, min_periods=1).mean()
    #设置定投起始时间 和结束 时间
    starttime = '20190625'
    endtime = '20201223'
    timeperiod = (pd.to_datetime(endtime) - pd.to_datetime(starttime)).days
    auto_invest_endtime = pd.to_datetime(starttime) +timedelta(7*initial_capital/invest_cash)

    df = df[df['candle_time'] >= pd.to_datetime(starttime)]
    df = df[df['candle_time'] <= pd.to_datetime(endtime)]
    df['week'] = df['candle_time'].dt.dayofweek # 计算星期几
    df['bias'] = (df['close'] - df['ma']) / df['ma']

    # 计算greed阶段的定投率
    df.loc[(df['greed_fear'] >= 50) & (df['greed_fear'] <60) , 'invest_rate'] = 1 - step
    df.loc[(df['greed_fear'] >= 60) & (df['greed_fear'] <70 ), 'invest_rate'] = 1 - 2 * step
    df.loc[(df['greed_fear'] >= 70) & (df['greed_fear'] <80 ), 'invest_rate'] = 1 - 3 * step
    df.loc[(df['greed_fear'] >= 80) & (df['greed_fear'] <90 ), 'invest_rate'] = 1 - 4 * step
    df.loc[(df['greed_fear'] >= 90) , 'invest_rate'] = 1 - 5 * step
    if not can_sell:
        df.loc[(df['invest_rate'] < 0), 'invest_rate'] = 0

    # 计算fear阶段的定投率
    df.loc[(df['greed_fear'] >= 40) & (df['greed_fear'] <50) , 'invest_rate'] = 1 + step
    df.loc[(df['greed_fear'] >= 30) & (df['greed_fear'] <40) , 'invest_rate'] = 1 + 2 * step
    df.loc[(df['greed_fear'] >= 20) & (df['greed_fear'] <30 ), 'invest_rate'] = 1 + 3 * step
    df.loc[(df['greed_fear'] >= 10) & (df['greed_fear'] <20 ), 'invest_rate'] = 1 + 4 * step
    df.loc[(df['greed_fear'] <10) , 'invest_rate'] = 1 + 5 * step


    # 比较均线定投和普通定投的区别
    # df = auto_invest(df, week=week, invest_cash=invest_cash, trade_rate=0.25 / 100, can_sell=can_sell)[0]

    df.reset_index(drop=True, inplace=True)
    df.loc[(df['week'] == week) & (df['candle_time'] < auto_invest_endtime),'action']= True
    df.loc[(df['action'] == True), 'smart_invest'] = df['invest_rate'] * invest_cash
    df['smart_invest'].fillna(value = 0, inplace=True)


    # 计算买入份额
    df['si_share'] = df['smart_invest'] / (df['close'] * (1 + trade_rate))
    df['si_share'].fillna(value=0, inplace=True)
    #df['ni_share'] = df['normal_invest'] / (df['close'] * (1 + trade_rate))
    df['smart_share_sum'] = df['si_share'].cumsum()
    # 处理一下没有份额卖出的情况
    if can_sell:
        for i in range(0, df.shape[0]):
            if i == 0:
                df['smart_share_sum'][i] = 0 + df['si_share'][i]
            if i != 0:
                df['smart_share_sum'][i] = df['si_share'][i] + df['smart_share_sum'][i - 1]
            if df['smart_share_sum'][i] < 0:
                df['smart_share_sum'][i] = 0
                if i != 0:
                    df['smart_invest'][i] = -df['smart_share_sum'][i - 1] * df['close'][i] / (1 + trade_rate)

    df.loc[(df['smart_share_sum'] == 0) & (df['smart_share_sum'].shift(1) == 0), 'smart_invest'] = 0.0
    df['smart_share_sum'].fillna(method='ffill', inplace=True	)
    df['smart_capital'] = df['smart_share_sum'] * df['close']
    df['smart_invest_all'] = df['smart_invest'].cumsum()
    df['smart_rate'] = df['smart_capital'] / df['smart_invest_all']
    si_invest_all = round(df['smart_invest'].sum(), 2)

    ## 计算defi 本金 和收益
    df['defi_position'] = initial_capital - df['smart_invest_all']
    df.loc[(df['action'] == True) ,'defi_profit'] =  df['defi_position'] * weekly_apr
    df['defi_profit'].fillna(value=0, inplace=True)
    df['defi_profit_all'] = df['defi_profit'].cumsum()
    df['defi_capital'] = df['defi_position'] + df['defi_profit_all']
    df['total_capital'] = df['defi_capital']+ df['smart_capital']

    result_capital = round(df['total_capital'].iloc[-1], 2)
    result_defiprofit  =  round(df['defi_profit_all'].iloc[-1], 2)
    result_smartinvestprofit  =  round((df['smart_capital']-df['smart_invest_all']).iloc[-1], 2)
    final_apy = (result_capital / initial_capital-1) * 100 *365/timeperiod
    ##同期BTC 涨幅
    btc_starttime = df['close'][0]
    btc_endtime =df['close'].iloc[-1]
    btc_change =( btc_endtime -btc_starttime)/btc_starttime


    # print('【DeFi + 定投,重度greed&fear组合】\n【熊市周期】\n '
    #       '周期：%s -- %s , %s 天\n '
    #       '总投入：%s  到期资产：%s  \n'
    #       '资产/投入：%.4f  总收益率： %.2f%%  \n '
    #      'Defi套利收益：%s  定投收益：%s \n'
    #       '年化收益率： %.2f%%'
    #
    #       % (starttime,endtime,timeperiod,
    #          initial_capital, result_capital,
    #          result_capital / initial_capital, (result_capital / initial_capital-1) * 100,
    #       result_defiprofit, result_smartinvestprofit,
    #          final_apy))
    #
    #
    # print ('\n【同期比特币价格】\n'
    #           '起始日  %s :  BTC = %s\n'
    #           '结束日  %s :  BTC = %s\n'
    #           '同期涨幅  ： %.2f%%'
    #         % (starttime, btc_starttime, endtime ,btc_endtime, btc_change*100))
    #
    # df.to_csv('defi + 定投 + greed_fear（D：%s,X:%s,Y:%s）.csv' % (days, week, step), encoding='gbk', index=False)
    print ("week =  %s ,  step = %s, apy = %s" %(week, step, final_apy))
    return (df)



def draw_1st_pic(df, initial_capital):
    plt.rcParams["font.family"] = 'Arial Unicode MS'
    #df[invest].fillna(method='ffill', inplace=True)
    #df[capital].fillna(method='ffill', inplace=True)
    plt.figure(figsize=(10, 7))
    plt.plot(df['candle_time'], df['smart_capital']-df['smart_invest_all'], label='定投收益')
    plt.plot(df['candle_time'], df['defi_profit_all'], label='Defi 收益')
    plt.plot(df['candle_time'], df['total_capital']-initial_capital, label='综合收益')
    plt.axis()
    plt.legend(loc='best')
    plt.grid(True)
    plt.title('Defi +智能定投表现 参数 Defi 收益率： 20%')
    plt.show()
    plt.savefig('image1.png')


def draw_2st_pic(df, initial_capital , starttime , endtime):
    scatterx = df.loc[df['smart_invest']>1]['candle_time']
    scattery = (df.loc[df['smart_invest']>1]['close'])/df['close'][0]-1
    scattersize = 20
    #scattersize = 40*(50-40* df.loc[df['smart_invest']>1]['invest_rate'])
    #print (scattersize)
    plt.figure(figsize=(10, 7))
    plt.plot(df['candle_time'],df['close']/df['close'][0]-1,'r',alpha = 0.4,label = 'BTC 表现')
    plt.plot(df['candle_time'],df['total_capital']/initial_capital-1,label ='基金净值')
    #plt.plot(df['candle_time'],df['close'])
    plt.legend(loc='best')
    plt.grid(True)

    plt.title('净值对比特币表现 %s --%s' %(starttime,endtime))
    plt.scatter(scatterx,scattery,s= scattersize,marker="d",alpha = 0.8)
    plt.show()
    plt.savefig('image2.png')
