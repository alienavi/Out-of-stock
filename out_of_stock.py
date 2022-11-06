# importing libraries
import requests
import pickle
from gql_query_builder import GqlQuery
from datetime import datetime
from pprint import pprint
from pathlib import Path
import time
import os
import sys

# get path for api file
def resource_path(relative_path) :
    try :
        base_path = sys._MEIPASS
    except Exception :
        base_path = os.path.abspath('.')
    
    return os.path.join(base_path, relative_path)

# debug param 1 for single product
prod_number = 12 # change to 12 for exe

# store api file path
file_path = resource_path('store.secret')
#print(file_path)

# reading shopify api and secrets
with open(file_path, 'rb') as f :
    store_secrets = pickle.load(f)

# defining store parameters
store_url = store_secrets['store_url'] + 'graphql.json'
location_id = store_secrets['location_id']

# defining request header
headers = {
    'X-Shopify-Access-Token': store_secrets['admin_access_token'],
    'Content-Type': 'application/json'
}

# function to run request
def run_query(query, uri=store_url, headers=headers) :
    request = requests.post(
        url=uri,
        json={'query': query},
        headers=headers
    )
    if(request.status_code == 200) :
        return request.json()
    else :
        print(request.status_code, request)

# creating query
page_info = GqlQuery().fields(['endCursor','hasNextPage'], name='pageInfo').generate()
featured_image = GqlQuery().fields(['url'], name='featuredImage').generate()
metafield = GqlQuery().fields(['value']).query(name='metafield', input={'namespace':'"my_fields"','key':'"breadcrumb_category"'}).generate()
product = GqlQuery().fields(['vendor',featured_image,metafield], name='product').generate()
var_node = GqlQuery().fields(['sku','inventoryQuantity','displayName',product], name='node').generate()
var_edges = GqlQuery().fields([var_node], name='edges').generate()
variables = {'first':prod_number,'after':'null','query':'"(inventory_quantity:<=0)AND(product_status:active)"'}

'''
    Data breakdown
    data -> data -> productVariants
    productVariants -> edges and pageInfo
    edges -> list of nodes -> node -> displayName, id, inventoryQuantity, sku, product -> vendor, featureImage, metafield -> value
    pageInfo -> endCursor, startCursor, hasNextPage
'''
# prepare output file
ofile = datetime.now().strftime('%d-%m-%Y_%H-%M') + '.csv'
with open(ofile, 'a', encoding="utf-8") as f :
            f.write('Image,Name,SKU,Quantity,Vendor,Vendor_Code\n')

# extracting info from data
def info_extract(data, loop_count=1) :
    try:
        for idx,node in enumerate(data['data']['productVariants']['edges']) :
            db = node['node']
            if(int(db['inventoryQuantity'])<=0) :
                try :
                    img_url = '=IMG("'+db['product']['featuredImage']['url']+'")'
                except TypeError :
                    img_url = ''
                try :
                    v_code = db['product']['metafield']['value']
                except TypeError :
                    v_code = ''
                write_data = '{0},{1},{2},{3},{4},{5}\n'.format(
                    img_url,
                    db['displayName'].replace(',',''),
                    db['sku'],
                    db['inventoryQuantity'],
                    db['product']['vendor'],
                    v_code
                )
                with open(ofile, 'a', encoding="utf-8") as f :
                    f.write(write_data)
            print('Product count : ', loop_count)
            loop_count += 1
    except KeyError:
        print(data)
    next_page = data['data']['productVariants']['pageInfo']['hasNextPage']
    return next_page, loop_count

next_page = True
first_run = True
loop_count = 1
while(next_page) :
    variants = GqlQuery().fields([var_edges, page_info]).query('productVariants', input=variables).operation().generate()        
    #pprint(variants)    
    data = run_query(variants)
    #pprint(data)
    #quit()
    # check if next page is present
    next_page, loop_count = info_extract(data, loop_count)
    # update the cursor
    variables['after'] = '"'+data['data']['productVariants']['pageInfo']['endCursor']+'"'
    # toggle first run
    first_run = False
    # check for throttle condition
    hit_rate = data['extensions']['cost']['requestedQueryCost']
    current_available = data['extensions']['cost']['throttleStatus']['currentlyAvailable']
    #print(hit_rate, current_available)
    if((2*int(hit_rate)) > (current_available)) :
        time.sleep(4)

# split csv based on vendors
import pandas as pd
stock_data = pd.read_csv(ofile)

out_dir = './'+ofile.replace('.csv','')
Path(out_dir).mkdir(parents=True,exist_ok=True)
i = 1
for k,v in stock_data.groupby('Vendor') :
    v.to_csv(f'{out_dir}/{k}_{i}.csv')
    i = i+1