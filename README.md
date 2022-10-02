# Out-of-stock

- Simple shopify app to get out of stock products
- out_of_stock.py -> all products with quantity 0(zero) or below
- below_threshold.py -> all products with quantity below respective threshold levels set in metafield
---
## How to get started

- Clone the repo
- Open the repo in your fav editor
    - create a python3 virtual enviroment
    - install requirements.txt using pip
- Generate a store.secret file using secret_generator.py
- run out_of_stock.py or below_threshold.py

### Going Further

- To create an standalone exe run
    - pyinstaller.exe --onefile --add-data="store.secret;." below_threshold.py
    - pyinstaller.exe --onefile --add-data="store.secret;." out_of_stock.py