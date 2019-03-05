from urllib.error import HTTPError

from bs4 import BeautifulSoup
from pyvirtualdisplay import Display
from selenium import webdriver


class Parser(object):
    domain_url = "https://www.vseinstrumenti.ru"

    def __init__(self, base_url):
        self.base_url = base_url

    def get_html(self, url, parent_task):
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        # be sure that chrmium browser is installed !!!
        driver = webdriver.Chrome("/usr/lib/chromium-browser/chromedriver")
        try:
            driver.get(url)
        except HTTPError as exc:
            if exc.response.status_code >= 500:
                msg = 'Will be tried 5 times: {}'.format(exc)
                raise parent_task.retry(exc=exc)
        html = driver.page_source
        soup = BeautifulSoup(html, 'lxml')
        driver.close()
        return soup
