#!/usr/bin/env python3

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
import pandas as pd

# get path for api file
def resource_path(relative_path) :
    try :
        base_path = sys._MEIPASS
    except Exception :
        base_path = os.path.abspath('.')
    
    return os.path.join(base_path, relative_path)

# debug param 1 for single product
prod_number = 12 # change to 12 for exe

# store-api file path
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

# helper function to run request
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
'''
    data {
        data {
            productVariants {
                edges {
                    [
                        node {
                            displayName
                            inventoryQuantity
                            sku
                            product {
                                vendor
                                featuredImage {
                                    url
                                }
                                threshold: metafield (key,namespace) {
                                    value
                                }
                                req_qty: metafield (key,namespace) {
                                    value
                                }
                            }

                        }
                        .
                        .
                        .


                    ]
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }
'''
page_info = GqlQuery().fields(['endCursor','hasNextPage'], name='pageInfo').generate()
featured_image = GqlQuery().fields(['url'], name='featuredImage').generate()
vendor_code = GqlQuery().fields(['value']).query(name='metafield', alias='vendor_code', input={'namespace':'"my_fields"','key':'"breadcrumb_category"'}).generate()
threshold = GqlQuery().fields(['value']).query(name='metafield', alias='threshold', input={'namespace':'"stock"','key':'"threshold"'}).generate()
req_qty = GqlQuery().fields(['value']).query(name='metafield', alias='req_qty', input={'namespace':'"my_fields"','key':'"req_quantity"'}).generate()
product = GqlQuery().fields(['vendor',featured_image,vendor_code,threshold,req_qty], name='product').generate()
var_node = GqlQuery().fields(['sku','inventoryQuantity','displayName',product], name='node').generate()
var_edges = GqlQuery().fields([var_node], name='edges').generate()

# prepare output file
ofile = datetime.now().strftime('%d-%m-%Y_%H-%M') + '.csv'
with open(ofile, 'a', encoding="utf-8") as f :
            f.write('Image,Name,SKU,Quantity,Vendor,Vendor_Code,Req_Qty\n')

# extracting info from data
'''
    Data breakdown
    data -> data -> productVariants
    productVariants -> edges and pageInfo
    edges -> list of nodes -> node -> displayName, id, inventoryQuantity, sku, product -> vendor, featureImage, vendor_code,threshold,req_qty -> value
    pageInfo -> endCursor, startCursor, hasNextPage
'''
def info_extract(data, loop_count=1) :
    try:
        for idx,node in enumerate(data['data']['productVariants']['edges']) :
            db = node['node']
            try :
                threshold = int(db['product']['threshold']['value'])
            except Exception :
                threshold = 0
            try :
                req_qty = db['product']['req_qty']['value']
            except Exception :
                req_qty = 0
            #print(threshold)
            if(int(db['inventoryQuantity'])<=threshold) :
                try :
                    img_url = '=IMG("'+db['product']['featuredImage']['url']+'")'
                except TypeError :
                    img_url = ''
                try :
                    v_code = db['product']['metafield']['value']
                except KeyError :
                    v_code = ''
                write_data = '{0},{1},{2},{3},{4},{5},{6}\n'.format(
                    img_url,
                    db['displayName'].replace(',',''),
                    db['sku'],
                    db['inventoryQuantity'],
                    db['product']['vendor'],
                    v_code,
                    req_qty
                )
                with open(ofile, 'a', encoding="utf-8") as f :
                    f.write(write_data)
            print('Product count : ', loop_count)
            loop_count += 1
    except KeyError:
        pprint('Error in fetching data', data)
        input('press enter to close')
    next_page = data['data']['productVariants']['pageInfo']['hasNextPage']
    return next_page, loop_count

# flow control
next_page = True
first_run = True
loop_count = 1
# request variable
variables = {'first':prod_number,'after':'null','query':'"(product_status:active)"'}

# main loop
while(next_page) :
    if(first_run):
        # run request for 1st time with cursor as null
        variants = GqlQuery().fields([var_edges, page_info]).query('productVariants', input=variables).operation().generate()
    else : 
        # consecutive runs with cursor = endcursor       
        variants = GqlQuery().fields([var_edges, page_info]).query('productVariants', input=variables).operation().generate()        
    #pprint(variants)    
    data = run_query(variants) # get request data
    #pprint(data)
    #quit()
    # check if next page is present
    next_page, loop_count = info_extract(data, loop_count) # extract info from respones    
    variables['after'] = '"'+data['data']['productVariants']['pageInfo']['endCursor']+'"' # update the cursor    
    first_run = False # toggle first run

    # check for throttle condition
    time.sleep(1) # restores 50 points
    # get current limits
    hit_rate = data['extensions']['cost']['requestedQueryCost']
    current_available = data['extensions']['cost']['throttleStatus']['currentlyAvailable']
    #print(hit_rate, current_available)
    if((2*int(hit_rate)) > (current_available)) :
        time.sleep(10) # sleep to restore 500 points

# split csv based on vendors
stock_data = pd.read_csv(ofile)

# creating an output directory
out_dir = './'+ofile.replace('.csv','')
Path(out_dir).mkdir(parents=True,exist_ok=True)
# storing vendor csv files
for k,v in stock_data.groupby('Vendor') :
    v.to_csv(f'{out_dir}/{k}.csv')