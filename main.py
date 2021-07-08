import os
import modules
import datetime
import gspread # to manipulate spreadsheet
from oauth2client.service_account import ServiceAccountCredentials # to access Google API

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
def write_domain_list(domain_info):
    SPREADSHEET_ID = os.environ['UNDER_CONTRACT_DOMAIN_SSID']
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('spreadsheet.json', scope)
    gc = gspread.authorize(credentials)
    sheet = gc.open_by_key(SPREADSHEET_ID).worksheet('契約中ドメイン一覧')

    sheet.clear()
    cell_list = sheet.range(1, 1, len(domain_info) + 1, 6)
    i = 0
    for cell in cell_list:
        if (i == 0):
            cell.value = 'No'
        elif (i == 1):
            cell.value = 'ドメイン名'
        elif (i == 2):
            cell.value = '取得先'
        elif (i == 3):
            cell.value = '有効期限'
        elif (i == 4):
            cell.value = '自動更新\nフラグ'
        elif (i == 5):
            cell.value = '自動更新\n対象'
        elif (i % 6 == 0):
            cell.value = int(i / 6)
        elif (i % 6 == 1):
            cell.value = domain_info[int(i / 6) - 1][0]
        elif (i % 6 == 2):
            cell.value = domain_info[int(i / 6) - 1][1]
        elif (i % 6 == 3):
            cell.value = domain_info[int(i / 6) - 1][2]
        elif (i % 6 == 4):
            cell.value = domain_info[int(i / 6) - 1][3]
        elif (i % 6 == 5):
            cell.value = domain_info[int(i / 6) - 1][4]
        i += 1
    sheet.update_cells(cell_list, value_input_option='USER_ENTERED')
    
    cell_list = sheet.range('G1:L1')
    cell_list[0].value = 'Size'
    cell_list[1].value = len(domain_info)
    cell_list[2].value = datetime.datetime.now().strftime('%Y-%m-%d')
    cell_list[3].value = '=HYPERLINK("https://www.value-domain.com/login.php", "Go to バリュー")'
    cell_list[4].value = '=HYPERLINK("https://muumuu-domain.com/?mode=conpane", "Go to ムームー")'
    cell_list[5].value = '=HYPERLINK("https://navi.onamae.com/domain", "Go to お名前")'
    sheet.update_cells(cell_list, value_input_option='USER_ENTERED')

### main_script ###
if __name__ == '__main__':

    try:
        domain_info = modules.value_domain.get_domain_info()
        logger.debug(f'main: add value_domain: {len(domain_info)}')
        if not domain_info:
            logger.error("Error: value_domain: get_domain_info")
            exit(1)
        domain_chunk = modules.muu_muu_domain.get_domain_info()
        if not domain_chunk:
            logger.error("Error: muu_muu_domain: get_domain_info")
            exit(1)
        domain_info.extend(domain_chunk)
        logger.debug(f'main: add muu_muu_domain: {len(domain_info)}')
        domain_chunk = modules.onamae_com.get_domain_info()
        if not domain_chunk:
            logger.error("Error: onamae_com: get_domain_info")
            exit(1)
        domain_info.extend(domain_chunk)
        logger.debug(f'main: add onamae_com: {len(domain_info)}')
        write_domain_list(domain_info)
        logger.info('Finish')
        exit(0)
    except Exception as err:
        logger.error(f'main: {err}')
        exit(1)
