import pandas as pd
stock_data = pd.read_csv('./03-11-2022_09-22.csv')

print(stock_data)

for k,v in stock_data.groupby('Vendor') :
    print(v)