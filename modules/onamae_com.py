import os
import re
import random
import datetime
from time import sleep
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as fs
from selenium.common.exceptions import NoSuchElementException 
from fake_useragent import UserAgent
from modules.by_pass_captcha import by_pass_captcha
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
def check_exists_by_name(driver, name):
    try:
        driver.find_element(By.NAME, name)
    except NoSuchElementException:
        return False
    return True

def check_exists_by_class_name(driver, class_name):
    try:
        driver.find_element(By.CLASS_NAME, class_name)
    except NoSuchElementException:
        return False
    return True

def parse_expiration_date(text):
    match = re.search(r'残り[\d]+日', text)
    if match:
        day_left = int(re.search(r'[\d]+', match.group()).group())
        now = datetime.datetime.now()
        expiration_date = now + datetime.timedelta(days=day_left)
        return expiration_date.strftime('%Y/%m/%d')
    else:
        return '-'

def parse_contents(tblFixed, tblwrap):
    tblFixedSize = len(tblFixed)
    tblwrapSize = len(tblwrap)
    logger.debug(f'tblFixed: {tblFixedSize}, tblwrap: {tblwrapSize}')
    if tblFixedSize != tblwrapSize:
        logger.debug(f'pop: {tblFixed.pop(0)}')
    for i in range(len(tblFixed)):
        attr = tblwrap[i].find_all("td")
        text = attr[1].get_text()
        match = re.search(r'\d{4}/\d{2}/\d{2}', text)
        if match:
            expiration_date = match.group()
        else:
            expiration_date = parse_expiration_date(text)
        edate = datetime.datetime.strptime(expiration_date, "%Y/%m/%d")
        if datetime.date(edate.year, edate.month, edate.day) < datetime.date.today():
            continue
        text = attr[2].get_text()
        match = re.search(r'設定', text)
        if match:
            autorenew = 0
        else:
            autorenew = 1
        domain_name = tblFixed[i].get_text()
        autorenew_target = "-"
        if autorenew == 1:
            autorenew_target = f'=IF(COUNTIF(\'ドメイン自動更新管理\'!B:B, "{domain_name}"), "対象", "対象外")'
        yield [domain_name, "お名前", expiration_date, autorenew, autorenew_target]

def get_domain_info():
    url = "https://navi.onamae.com/domain"
    login = os.environ["ONAMAE_ID"]
    password = os.environ["ONAMAE_PASS"]

    ua = UserAgent()
    logger.debug(f'onamae_com: UserAgent: {ua.chrome}')

    options = Options()
    options.add_argument("--disable-notifications")
    options.add_argument("--mute-audio")
    options.add_argument(f'user-agent={ua.chrome}')
#   options.add_argument('--headless')
    
    try:
        chrome_service = fs.Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=chrome_service, options=options)
        
        driver.get(url)
        driver.set_window_size(1200, 1053)

        driver.find_element(By.NAME, "loginId").send_keys(login)
        driver.find_element(By.NAME, "loginPassword").send_keys(password)
        driver.find_element(By.TAG_NAME, "button").click()
        sleep(random.randint(7, 11))

        logger.info("onamae_com: check if g-recaptcha exists")
        if check_exists_by_class_name(driver, "g-recaptcha"):
            ret = by_pass_captcha(driver)
            if ret == False:
                raise Exception
            sleep(10)

        logger.info('onamae_com: login')
        sleep(5)

        if not check_exists_by_name(driver, "select1"):
            driver.find_element(By.LINK_TEXT, "TOP").click()
            sleep(5)
            driver.find_element(By.XPATH, '//button[@data-gtmvalue="usagesituation_domain"]').click()
            sleep(10)

        dropdown = driver.find_element(By.NAME, "select1")
        select = Select(dropdown)
        select.select_by_value('100')
        
        logger.info('onamae_com: select 100')
        sleep(30)

        try:
            nav = driver.find_element(By.XPATH, '//ul[@class="nav-Pagination"]')
            paging = nav.find_elements(By.TAG_NAME, "a")
            logger.info(f'paging: {len(paging) - 2}')
        
            contents = BeautifulSoup(driver.page_source, "html.parser")
            domain_info = list(parse_contents(contents.find_all("tr", target="tblFixed"), contents.find_all("tr", target="tblwrap")))
            logger.debug(f'page: 1: {len(domain_info)}')

            for i in range(len(paging)):
                if i == 0 or i == 1 or i == len(paging) - 1:
                    continue
                paging[i].click()
                sleep(20)
                contents = BeautifulSoup(driver.page_source, "html.parser")
                domain_chunk = list(parse_contents(contents.find_all("tr", target="tblFixed"), contents.find_all("tr", target="tblwrap")))
                logger.debug(f'page: {i}: {len(domain_chunk)}')
                domain_info.extend(domain_chunk)
        except:
            contents = BeautifulSoup(driver.page_source, "html.parser")
            domain_info = list(parse_contents(contents.find_all("tr", target="tblFixed"), contents.find_all("tr", target="tblwrap")))
            logger.debug(f'page: 1: {len(domain_info)}')

        logger.debug(f'onamae_com: total_list_number: {len(domain_info)}')

        driver.close()
        driver.quit()

        return domain_info
    except Exception as err:
        logger.error(f'Error: onamae_com: get_domain_info: {err}')
        return None
