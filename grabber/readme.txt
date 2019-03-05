### run celery
>> celery -A configs.celery:app worker -B -l info

### run task in shell to start parse
from main.tasks import retrieve_products_data
retrieve_products_data()