import csv
import sys
from sys import exit
from collections import defaultdict

def get_raw_data(filename):
    data = []
    with open(filename, 'rb') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=",", quotechar='|')
        for row in csvreader:
            data.append(row)   
    data.pop(0)
    return data
    
p_hash = {}
def prices_hash():
    stock_prices = get_raw_data("prices.csv")
    for asset in stock_prices:
        p_hash[asset[0]] = float(asset[2])
    return p_hash

prices_hash()

def convert_data(d):
    data_hash = defaultdict(dict)
    for transaction in d:
        transaction[3] = float(transaction[3])
        details = transaction[1:]
        details.pop(1)
        data_hash[transaction[0]][transaction[2]]= details
    return data_hash

def calc_margin(endofday):
    clients = {}
    
    for account, holdings in endofday.items():
        balances = []
        balances.append(0)
        balances.append(0)
        for stock, info in holdings.items():
            form = info[0]
            amt = info[1]
            time = info[2]
            if form == 'CASH':
                balances[0] += amt
            if form == 'STK' and time == 'Short':
                balances[1] += amt * p_hash[stock]
        clients[account] = balances

    margin_call = {}  
    for key, value in clients.items():
        vals = []
        vals =  [format(value[0],'.2f'), format(value[1]/2,'.2f'), value[0] < value[1]/2]
        margin_call[key] = vals
    return margin_call 


def form_eod(prev_day, today_trades):
    yesterday = convert_data(get_raw_data(prev_day))
    trades = get_raw_data(today_trades)
    # I assume at the end of the day that all the orders will be finished.
    for transaction in trades:
        acct = transaction[0]
        company = transaction[1]
        order = transaction[2]
        t_price = float(transaction[5]) # transaction[5] is today's average price
        amt = float(transaction[3])
        if order == 'Buy':
            if 'n/a' not in yesterday[acct]:
                yesterday[acct]['n/a'] = ['CASH', 0, 'Long']
            cash = yesterday[acct]['n/a'][1]
            if company not in yesterday[acct]:
                yesterday[acct][company] = ['STK', amt, 'Long']
                yesterday[acct]['n/a'][1] -= amt * t_price
            else:
                time = yesterday[acct][company][2]
                funds = yesterday[acct][company][1]
                if time == 'Long':
                    funds += amt
                    yesterday[acct]['n/a'][1] -= amt * t_price
                
                elif time == 'Short':
                    buy = amt* t_price
                    short = funds * t_price
                    funds -= amt
                    yesterday[acct]['n/a'][1] -= buy
                    if buy > short:
                        time = 'Long'
                # if you buy more than you shorted, you speculate the price to rise 
        elif order == 'Short':
            if company not in yesterday[acct]:
                yesterday[acct][company] = ['STK', amt, 'Short']
            else:
                time = yesterday[acct][company][2]
                funds = yesterday[acct][company][1]
                if time == 'Long':
                    time = 'Short'
                    funds += amt
                elif time == 'Short':
                    funds += amt
        else: #the sell case 
            if yesterday[acct][company][2] == 'Long':
                yesterday[acct][company][1] -= amt
                if 'n/a' not in yesterday[acct]:
                    yesterday[acct]['n/a'] = ['CASH', 0, 'Long']
                yesterday[acct]['n/a'][1] += amt*t_price 
    return yesterday


def total_margin(region):
    if region == 'NA':
        NA = convert_data(get_raw_data("na_t.csv"))
        return calc_margin(NA)
    elif region == 'EU':
        EU = form_eod("emea_t-1.csv","emea_trades.csv")
        return calc_margin(EU)
    elif region == 'APAC':
        APAC = form_eod("apac_t-1.csv","apac_trades.csv")
        return calc_margin(APAC)

def make_csv(margins, filename):
    target_file = open(filename, 'w')
    target_file.write("Account ID, Cash balance, Margin balance, Margin call\n")
    for account, balances in margins.items():
        target_file.write(account)
        target_file.write(", ")
        target_file.write(str(balances[0]))
        target_file.write(", ")
        target_file.write(str(balances[1]))
        target_file.write(", ")
        target_file.write(str(balances[2]))
        target_file.write("\n")
    target_file.close()
    
def quit_fun(word):
    if word == 'quit':
        exit()
    return 0

def execute():
    print "Hello, please designate your region. If the region is not listed, the margin data for all regions will be printed.\n"
    while(1):
        print "Type 'quit' at anytime to quit.\n"
        region = raw_input("Region (NA,EU,APAC): ")
        quit_fun(region)
        print "Please designate what file to write to. The csv extension is automatically added.\n"
        o_file = raw_input("Output filename: ")
        quit_fun(o_file)
    
        if region != 'NA' and region != 'EU' and region != 'APAC':
            make_csv(total_margin('NA'), o_file + 'NA.csv')
            make_csv(total_margin('EU'), o_file + 'EU.csv')
            make_csv(total_margin('APAC'), o_file + 'APAC.csv')
        else:
            print "To view an account number, type it here. If it is not found or the entry invalid, all accounts will be written to %s" %o_file
            acc_num = raw_input("Account #: ")
            quit_fun(acc_num)
        reg_data = total_margin(region)
        if acc_num in reg_data.keys():
            sys.stdout.write("Account #: " + acc_num + '\n')
            sys.stdout.write("Cash balance: " + reg_data[acc_num][0] + '\n')
            sys.stdout.write("Margin balance: " + reg_data[acc_num][1] + '\n')
            sys.stdout.write("Margin call? " + str(reg_data[acc_num][2]) + '\n')
        else:
            print "Account does not exist. Writing all accounts to %s" %o_file
            make_csv(reg_data, o_file + '.csv')
        
execute()
    