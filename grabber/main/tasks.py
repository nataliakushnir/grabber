import re
import time
from urllib.error import HTTPError

from celery import shared_task

from main.models import Product
from main.parser import Parser
from main.utils import md5Checksum


@shared_task(bind=True)
def retrieve_products_data(self):
    parse_categories.delay()


@shared_task(bind=True, default_retry_delay=10, max_retries=5)
def parse_categories(self):
    p = Parser(base_url="https://www.vseinstrumenti.ru/map.html")
    soup = p.get_html(url=p.base_url, parent_task=self)
    categories = soup.find(id="rubrikator")
    for c in categories.find_all('li', {'class': 'level3'}):
        if hasattr(c.find('a'), 'href'):
            link = c.find('a')['href']
            if 'https://' in link:
                c_link = link
            else:
                c_link = '/'.join([p.domain_url.rstrip('/'), link.lstrip('/')])
            parse_products_from_category_link.delay(url=c_link)
        time.sleep(600)


@shared_task(bind=True, default_retry_delay=10, max_retries=5)
def parse_products_from_category_link(self, url):
    p = Parser(base_url=url)
    soup = p.get_html(url=p.base_url, parent_task=self)

    products_blocks = soup.find('div', {'id': 'goodsListingBox'}).find_all('div', {'class': 'tile-block'})
    if not products_blocks:
        products_blocks = soup.find('div', {'id': 'goodsListingBox'}).find_all('div', {'class': 'list-box product'})
    for block in products_blocks:
        products = block.find_all('div', {'class': 'tile-box product'})
        for product in products:
            link = product.find('a', {'class': 'picture'})['href']
            if 'https://' in link:
                p_link = product.find('a', {'class': 'picture'})['href']
            else:
                p_link = '/'.join([p.domain_url.rstrip('/'), link.lstrip('/')])
            parse_product_from_own_page.delay(p_link)
            time.sleep(60)
    if soup.find('div', {'class': 'paging dspl_ib commonPagination'}):
        start_page = 2
        new_url = '/'.join([url.strip('/'), f'page{start_page}/#goods'.lstrip('/')])
        parse_products_from_paginator_page.delay(url=new_url, page=start_page, prev_url=url)
        time.sleep(60)


@shared_task(bind=True, default_retry_delay=10, max_retries=5)
def parse_products_from_paginator_page(self, url, page, prev_url):
    p = Parser(base_url=url)
    soup = p.get_html(url=p.base_url, parent_task=self)

    products_blocks = soup.find('div', {'id': 'goodsListingBox'}).find_all('div', {'class': 'tile-block'})
    for block in products_blocks:
        products = block.find_all('div', {'class': 'tile-box product'})
        for product in products:
            link = product.find('a', {'class': 'picture'})['href']
            if 'https://' in link:
                p_link = product.find('a', {'class': 'picture'})['href']
            else:
                p_link = '/'.join([p.domain_url.lstrip('/'), link.lstrip('/')])
            parse_product_from_own_page.delay(url=p_link)
    if not products_blocks:
        products_blocks = soup.find('div', {'id': 'goodsListingBox'}).find_all('div', {'class': 'list-box product'})
        for block in products_blocks:
            product = block.find('div', {'class': 'product-name'})
            if hasattr(product.find('a'), 'href'):
                link = product.find('a')['href']
                if 'https://' in link:
                    p_link = link
                else:
                    p_link = '/'.join([p.domain_url.lstrip('/'), link.lstrip('/')])
                parse_product_from_own_page.delay(url=p_link)

    if soup.find('a', {'class': 'dspl_ib sprArrow arrowScrollRightRed'}):
        new_page = page + 1
        new_url = '/'.join([prev_url.strip('/'), f'page{new_page}/#goods'.lstrip('/')])

        return parse_products_from_paginator_page(url=new_url, page=new_page, prev_url=prev_url)


@shared_task(bind=True, default_retry_delay=10, max_retries=5)
def parse_product_from_own_page(self, url):
    p = Parser(base_url=url)
    soup = p.get_html(url=p.base_url, parent_task=self)

    product_old_price = None
    product_price = None
    is_available = True
    product_name = soup.find('h1', {'id': 'card-h1-reload-new'}).text.lstrip()
    product_code = soup.find('span', {'class': 'wtis-id-value codeToOrder'}).text.lstrip()

    basket = soup.find('div', {'class': 'card-basket-block-new'})
    if not basket.find('span', {'class': 'price-value'}):
        is_available = False
    else:
        product_old_price = soup.find('span', {'class': 'saled-price-value'}).text.replace(' ', '') if soup.find('span', {'class': 'saled-price-value'}) else None
        product_price = soup.find('span', {'class': 'price-value'}).text.replace(' ', '') if soup.find('span', {'class': 'price-value'}) else None

    description_block = soup.find('div', {'class': 'fs-13 c-gray3 copy-checker'})
    description = ''
    for feature in description_block.find_all('p'):
        description += feature.text

    # simple-history tracks all changes in product
    defaults = {
        'name': product_name,
        'available_price': product_price,
        'old_price': product_old_price,
        'is_available': is_available,
        'description': description,
    }
    # create or update if\n daily task
    p, _ = Product.objects.update_or_create(defaults=defaults, code=product_code)

    if _:
        print(f"{p} created")

    main_img_div = soup.find('div', {'class': 'zoomWindowContainer'}).findChildren('div')[0]['style']
    main_image_url = re.findall('url\((.*?)\)', main_img_div)[0]
    download_image_from_request.delay(image_url=main_image_url, product_id=p.pk, is_main=True)

    images_block = soup.find('div', {'id': 'slider_content'})

    for image in images_block:
        if image.find('img') and hasattr(image.find('img'), 'src'):
            image_url = image.find('img')['src']
            download_image_from_request.delay(image_url=image_url, product_id=p.pk)


@shared_task(bind=True, default_retry_delay=10, max_retries=5)
def download_image_from_request(self, image_url, product_id, is_main=False):

    from main.models import Product
    import requests
    from django.core.files import File
    from django.core.files.temp import NamedTemporaryFile

    product = Product.objects.get(id=product_id)

    try:
        r = requests.get(image_url)
        r.raise_for_status()
    except HTTPError as exc:
        if exc.response.status_code >= 500:
            raise self.retry(exc=exc)
        raise exc
    except Exception as exc:
        raise exc
    else:
        img_name = image_url.split('/')[-1]

        try:
            temp_file = NamedTemporaryFile(delete=True)
            temp_file.write(r.content)
            temp_file.flush()
        except Exception as e:
            raise
        image_hash = md5Checksum(url=image_url)
        # create if not exists
        if not product.images.filter(hash=image_hash).exists():
            image = product.images.create()
            image.hash = image_hash
            image.is_main = is_main
            image.image.save(img_name, File(temp_file), save=True)
