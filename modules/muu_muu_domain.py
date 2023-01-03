import os
import re
import datetime
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
from fake_useragent import UserAgent
from webdriver_manager.chrome import ChromeDriverManager

# Logger setting
from logging import getLogger, FileHandler, DEBUG
logger = getLogger(__name__)
today = datetime.datetime.now()
handler = FileHandler(f'log/{today.strftime("%Y-%m-%d")}_result.log', mode='a')
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

### functions ###
def parse_expiration_date(text):
    match = re.search(r'あと [-\d]+ 日', text)
    if match:
        day_left = int(re.search(r'[-\d]+', match.group()).group())
        now = datetime.datetime.now()
        expiration_date = now + datetime.timedelta(days=day_left)
        return expiration_date.strftime('%Y/%m/%d')
    else:
        return '-'

def parse_contents(conpane_cards):
    for element in conpane_cards:
        text = element.get_text()
        match = re.search(r'期限切れ間近|期限切れ|自動更新中', text)
        if match:
            if match.group() == "期限切れ":
                continue
            elif match.group() == "自動更新中":
                autorenew = 1
            else:
                autorenew = 0
        else:
            autorenew = 0
        match = re.search(r'\d{4}/\d{2}/\d{2}', text)
        if match:
            expiration_date = match.group()
        else:
            expiration_date = parse_expiration_date(text)
        start = re.search(r'契約期間', text).start()
        domain_name = text[:start].replace(' ', '').replace('\n', '')
        autorenew_target = "-"
        if autorenew == 1:
            autorenew_target = f'=IF(COUNTIF(\'ドメイン自動更新管理\'!B:B, "{domain_name}"), "対象", "対象外")'
        yield [domain_name, "ムームー", expiration_date, autorenew, autorenew_target]

def get_domain_info():
    url = "https://muumuu-domain.com/checkout/login"
    login = os.environ["MUU_MUU_ID"]
    password = os.environ["MUU_MUU_PASS"]
    
    ua = UserAgent()
    logger.debug(f'muu_muu_domain: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument('--headless')
    options.add_argument(f'user-agent={ua.chrome}')

    try:
        chrome_service = fs.Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=chrome_service, options=options)
        
        driver.get(url)
        driver.set_window_size(1200, 1053)
        
        driver.find_element(By.ID, "session_muu_id").send_keys(login)
        driver.find_element(By.ID, "session_password").send_keys(password)
        driver.find_element(By.NAME, "button").send_keys(Keys.ENTER)
        
        logger.info('muu_muu_domain: login')
        sleep(5)
        
        driver.find_element(By.LINK_TEXT, "ドメイン一覧(すべて)へ").send_keys(Keys.ENTER)
        
        logger.info('muu_muu_domain: go to all-domain-list')
        sleep(5)
        
        dropdown = driver.find_element(By.NAME, "limit")
        select = Select(dropdown)
        select.select_by_value('1000')
        
        logger.info('muu_muu_domain: select 1000')
        sleep(15)
        
        contents = BeautifulSoup(driver.page_source, "lxml")
        domain_info = list(parse_contents(contents.find_all(class_="conpane-card")))
        logger.debug(f'muu_muu_domain: total_list_number: {len(domain_info)}')

        driver.close()
        driver.quit()

        return domain_info
    except Exception as err:
        logger.error(f'Error: muu_muu_domain: get_domain_info: {err}')
        return None
