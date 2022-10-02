#!/usr/bin/env python3

# importing libraries
import pickle

# store api secrets
db = {
    'api_key':'<.........>',
    'api_secret':'<.........>',
    'admin_access_token':'<.........>',
    'store_url':'<.........>',
    'location_id':'<.........>'
}

# secret file
dbfile = open('./store.secret','wb')
pickle.dump(db, dbfile)
dbfile.close()

# check file content
dbfile = open('./store.secret','rb')
print(pickle.load(dbfile))
dbfile.close()