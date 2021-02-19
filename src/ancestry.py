'''
Author: Henry Yeomans
Created: 2020-12

Class: AncestryScraper
A selenium-based webscraping bot which gathers parish records from Ancestry.co.uk.
'''

#%%
import os

from bs4 import BeautifulSoup
from selenium import webdriver    # conda install selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException



def boot_up_driver():
    '''
    Boots up chromedriver with minimal detectability.
    Returns webdriver.Chrome object.
    '''
    # Change settings to minimize detectability
    option = webdriver.ChromeOptions()
    # For older ChromeDriver under version 79.0.3945.16
    option.add_experimental_option("excludeSwitches", ["enable-automation"])
    option.add_experimental_option('useAutomationExtension', False)
    #For ChromeDriver version 79.0.3945.16 or over
    option.add_argument('--disable-blink-features=AutomationControlled')
    # Change resolution and user-agent
    option.add_argument("window-size=1280,800")
    option.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36")
    #Open Browser
    driver = webdriver.Chrome(executable_path='chromedriver.exe',options=option)
    driver.maximize_window()

    return driver


def accept_cookies(driver):
    '''
    Accepts cookies.
    '''
    xpath_accept = r'//*[@id="Banner_cookie_0"]/div[2]/div/div[2]/div/button[1]'
    accept_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath_accept)))
    accept_button.click()

    return driver


def sign_in(driver, username, password):
    '''
    Signs into ancestry.
    '''
    # Switch to sign in iframe
    iframe_xpath = r'/html/body/main/div/div/section/div/div/div[2]/div[1]/iframe'
    frames = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH,iframe_xpath)))
    if frames[0].is_displayed(): 
        driver.switch_to.frame(frames[0])
        #Enter username
        xpath_un = r'//*[@id="username"]'
        un_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,xpath_un)))
        un_box.send_keys(username)
        # Enter password
        xpath_pw = r'//*[@id="password"]'
        pw_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,xpath_pw)))
        pw_box.send_keys(password)
        # Click sign in 
        xpath_sign_in = r'/html/body/main/form/div/div[3]/button'
        sign_in_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,xpath_sign_in)))
        sign_in_button.click()
    else:
        raise AuthenticationError('Could not find sign-in box.')

    return driver


def when_dom_static(driver, xpath, timeout=15, to_send='click'):
    '''
    Attempts to interact with an element on a page until the page has stopped changing.
    '''
    no_success = True
    while no_success:
        try:
            element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
            if to_send == 'click':
                element.click()
            else:
                try:
                    element.send_keys(to_send)
                except:
                    raise ValueError('Invalid Keys object.')
            no_success = False
        except:
            continue

    return driver


def collect_urls(driver, urls, option_names):
    '''
    '''
    url_key = tuple(option_names)
    ignored_exceptions=(NoSuchElementException,StaleElementReferenceException,)
    num_browse_levels = len(option_names)
    year_range_xpath = r'//*[@id="divBL_{}"]/div/ul/li'.format(num_browse_levels)
    try:
        urls_li_list     = WebDriverWait(driver, 20, ignored_exceptions=ignored_exceptions)\
                        .until(EC.presence_of_all_elements_located((By.XPATH, year_range_xpath)))
        urls_list        = [WebDriverWait(element, 15, ignored_exceptions=ignored_exceptions)\
                        .until(EC.presence_of_element_located((By.XPATH, 'a'))) for element in urls_li_list]
        urls_dict        = {element.text : element.get_attribute('href') for element in urls_list}
    # If no urls are displayed:
    except:
        urls_dict = {}

    return driver, urls_dict


def drop_down(driver, xpaths_bl, option_names=[]):
    global urls
    if not xpaths_bl:
        driver, urls_dict = collect_urls(driver, urls, option_names)
        # Update urls with date-ranges and hrefs
        urls[url_key] = urls_dict
    else:
        xpath_level_name           = xpaths_bl[0] + r'/label'
        xpath_select               = xpaths_bl[0] + r'/div/select'
        xpath_options              = xpath_select + r'/option'
        x = True
        # Sometimes, webpage becomes stuck loading the next options drop-down box. If this happens, refresh and try again.
        while x:
            try:
                highest_level_options = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, xpath_options)))[1:]
                x = False
            except:
                driver.refresh()
                continue
        highest_level_option_names = [option.text for option in highest_level_options]
        for option, option_name in zip(highest_level_options, highest_level_option_names):
            driver = when_dom_static(driver, xpath_select, timeout=15, to_send='click')
            driver = when_dom_static(driver, xpath_select, timeout=15, to_send=Keys.DOWN)
            driver = when_dom_static(driver, xpath_select, timeout=15, to_send=Keys.ENTER)
            option_names_copy = option_names.copy()
            option_names_copy.append(option_name)
            if xpaths_bl[:-1]:
                drop_down(driver, xpaths_bl[1:], option_names_copy)
            else:
                drop_down(driver, xpaths_bl[:-1], option_names_copy)
    
    return driver, urls


class AncestryScraper:
    '''
    A selenium-based bot which scrapes parish data from ancestry.co.uk.
    '''

    def __init__(self):
        self.authenticated_driver = None
        self.county_urls = None


    def authenticate(self):
        '''
        Boots up a chrome webdriver with minimal detectability, signs into ancestry, accepting cookies.
        Returns WebDriver.Chrome at welcome page.
        '''
        # Sign in details
        USERNAME = os.getenv('ANC_USERNAME', None)
        PASSWORD = os.getenv('ANC_PASSWORD', None)
        if not (USERNAME and PASSWORD):
            raise AuthenticationError('No username and/or password found in environment variables. \
                Ensure these are set before attempting to authenticate.')
        driver = boot_up_driver()
        # Go to sign in page, accept cookies, sign in.
        driver.get('https://www.ancestry.co.uk/secure/login')
        driver = accept_cookies(driver)
        driver = sign_in(driver, USERNAME, PASSWORD)
        # Check welcome screen is displayed
        welcome_xpath = r'//h1[@class="pageTitle"]'
        welcome = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,welcome_xpath)))
        if 'Welcome,' in welcome.text:
            print('Successfully logged in.')
            self.authenticated_driver = driver
            return driver
        else:
            raise AuthenticationError('Something went wrong.')
            driver.quit()
            return False


    def get_parish_urls(self, driver, collection_code):
        '''
        Collects the urls to the image viewer pages with transcribed records for collection with code 'collection_code'.
        Updates self.county_urls to be a dictionary: {<record place and/or type> (tuple) : {<year range> : <url>} (dict)}
        Returns WebDriver.Chrome at welcome page.
        '''
        # Go to collection url
        url_collection = r'https://www.ancestry.co.uk/search/collections/{}/'.format(collection_code)
        driver.get(url_collection)
        # Check the "Browse this collection" box is displayed.
        xpath_browse_box = r'//*[@id="divBrowse"]'
        try:
            browse_box = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath_browse_box)))
        except:
            raise NotFoundError('Either {} is not a valid ID or the collection cannot be browsed in the image viewer.')
        xpaths_bl = [r'//*[@id="browseControls"]/div[{}]'.format(i) for i in range(1, len(browse_levels) + 1)]
        urls = {}
        driver, urls = drop_down(driver, xpaths_bl)
        self.county_urls = urls
        driver.get(r'https://www.ancestry.co.uk')

        return driver


    def shut_down(self):
        '''
        Close chromedriver.
        '''
        driver = self.authenticated_driver
        if driver:
            driver.close()
        
        return None


