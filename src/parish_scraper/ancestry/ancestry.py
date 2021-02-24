'''
Author: Henry Yeomans
Created: 2020-12

Class: AncestryScraper
A selenium-based webscraping bot which gathers parish records from Ancestry.co.uk.
'''

import os
import pandas as pd

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
    Once visible, collect the urls for image viewers for the given option names.
    Returns driver, url_key (tuple), urls_dict (dict: {<date range> : <url>,...}).
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

    return driver, url_key, urls_dict


def get_browse_labels(driver):
    '''
    Returns the labels (tuple) for each drop down browse element.
    '''
    browse_controls = driver.find_element_by_css_selector(r'#browseControls')
    labels = browse_controls.find_elements_by_css_selector('label')
    labels = tuple([label.text for label in labels])

    return labels


def drop_down(driver, xpaths_bl, option_names=[]):
    global urls
    if not xpaths_bl:
        xpath_level_name           = xpaths_bl[0] + r'/label'
        driver, url_key, urls_dict = collect_urls(driver, urls, option_names)
        labels = get_browse_labels(driver)
        url_key = tuple(zip(labels, url_key))
        # Update urls with date-ranges and hrefs
        urls[url_key] = urls_dict
    else:
        xpath_select               = xpaths_bl[0] + r'/div/select'
        xpath_options              = xpath_select + r'/option'
        no_success = True
        # Sometimes, webpage becomes stuck loading the next options drop-down box. If this happens, refresh and try again.
        while no_success:
            try:
                highest_level_options = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.XPATH, xpath_options)))[1:]
                no_success = False
            except:
                driver.refresh()
                continue
        highest_level_option_names = [option.text for option in highest_level_options]
        option_label = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath_options))).text
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


def get_useful_elements(driver):
    '''
    Returns a dictionary of useful image viewer page elements.
    '''
    # Button panel
    xpath_buttons       = r'//*[@class="paging-wrapper"]'
    buttons_panel       = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, xpath_buttons)))
    # Button to reveal table
    xpath_table_buttons = r'./button'
    table_button        = WebDriverWait(buttons_panel, 15).until(EC.presence_of_all_elements_located((By.XPATH, xpath_table_buttons)))[-1]
    # Next page button
    css_next_page       = r'button.page'
    next_page_button    = WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, css_next_page)))[-1]
    # Number of pages
    css_pages           = r'span.imageCountText.middle'
    num_pages           = WebDriverWait(buttons_panel, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_pages))).text
    # Index panel
    css_index_panel     = r'div.index-panel'
    index_panel         = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, css_index_panel)))
 
    elements = {'buttons_panel'   : buttons_panel,
               'table_button'     : table_button,
               'next_page_button' : next_page_button,
               'num_pages'        : num_pages,
               'index_panel'      : index_panel}

    return elements


def get_table_html(driver, **kwargs):
    '''
    For a given image viewer page, returns the inner html of the grid container.
    '''
    buttons_panel    = kwargs['buttons_panel']
    table_button     = kwargs['table_button']
    next_page_button = kwargs['next_page_button']
    num_pages        = kwargs['num_pages']
    index_panel      = kwargs['index_panel']
    
    if not table_button.is_enabled():
        grid_container_html = None
    else:
        css_grid_container   = r'div.grid-container'
        grid_container       = WebDriverWait(index_panel, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR,css_grid_container)))
        grid_container_html  = grid_container.get_attribute('innerHTML')

    return driver, grid_container_html


def make_grid_container_df(grid_container):
    '''
    Returns pandas.DataFrame containing the data within grid_container html.
    '''
    soup = BeautifulSoup(grid_container, 'html.parser')
    rows          = soup.find_all('div', {'class':'grid-row'})
    columns_html  = rows[0].findChildren('div')
    elements_html = [row.findChildren('div') for i, row in enumerate(rows) if i >= 1]
    columns       = [column.text for column in columns_html]
    elements      = []
    for i in range(len(elements_html)):
        element_row_html = elements_html[i]
        row_elements     = [element.text for element in element_row_html]
        elements.append(row_elements)
        df = pd.DataFrame(elements, columns=columns)
    
    return df


def scrape_record(driver, record_url):
    '''
    Scrape index panel data from parish collection at collection_url using driver.
    Driver must be authenticated (if not, call athuenticate() before calling this function).
    Progress is printed.
    Returns: Tuple (driver, complete DataFrame for that collection)
    '''
    # Go to webpage for the collection
    driver.get(record_url)

    elements         = get_useful_elements(driver)
    next_page_button = elements['next_page_button']
    not_last_page    = True
    counter          = 1

    grid_containers  = []
    df_list          = []
    prev_grid_container = None     
    # Scrape the grid containers
    while not_last_page:
        elements                    = get_useful_elements(driver)
        driver, grid_container_html = get_table_html(driver, **elements)
        if grid_container_html and grid_container_html != prev_grid_container:
            grid_containers.append(grid_container_html)
            prev_grid_container = grid_container_html
            not_last_page       = next_page_button.is_enabled()
            if not_last_page:
                next_page_button.click()
        else:
            continue

    # Now use BeautifulSoup to turn the html into a dataframe
    for grid_container in grid_containers:
        df = make_grid_container_df(grid_container)
        df_list.append(df)

    # Concatenate all dataframes into a final dataframe
    if df_list:
        df_concat = pd.concat(df_list, ignore_index=True).drop_duplicates().reset_index(drop=True)
    else:
        df_concat = pd.DataFrame([], columns = [])

    return driver, df_concat


def sort_dict(dictionary):
    '''
    Sorts dictionary by length of value.
    '''
    def my_key(element):
        return len(element[-1])

    list_dict = list(dictionary.items())
    list_dict.sort(key=my_key)
    sorted_dict = dict(list_dict)
    
    return sorted_dict


def partition_dict(dictionary, n_partitions):
    '''
    Partitions a dictionary into n_partitions of approximately equal length.
    '''
    list_of_dicts = [[] for i in range(n_partitions)]
    for i, item in enumerate(dictionary.items()):
        list_of_dicts[i % n_partitions].append(item)
    list_of_dicts = [dict(d) for d in list_of_dicts]
    
    return list_of_dicts


class AncestryScraper:
    '''
    A selenium-based bot which scrapes parish data from ancestry.co.uk.
    '''

    def __init__(self):
        self.authenticated_driver = None
        self.collection_urls = None

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
        else:
            driver.quit()
            raise AuthenticationError('Something went wrong.')
            
        return 

    def get_parish_urls(self, driver, collection_code):
        '''
        Collects the urls to the image viewer pages with transcribed records for collection with code 'collection_code'.
        Updates self.collection_urls to be a dictionary: {<record place and/or type> (tuple) : {<year range> : <url>} (dict)}
        Returns WebDriver.Chrome at welcome page.
        '''
        if not self.authenticated_driver:
            raise AuthenticationError('Please authenticate before attempting to collect urls.')
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
        self.collection_urls = urls
        driver.get(r'https://www.ancestry.co.uk')

        return driver

    def scrape_collection(self, n_jobs=1):
        '''
        Scrapes all records in a collection with urls contained in self.collection_urls.
        Returns Pandas.DataFrame.
        '''
        if not self.authenticated_driver:
            raise AuthenticationError('Please authenticate before attempting to collect urls.')
        else:
            driver = self.authenticated_driver
        collection_urls = self.collection_urls
        if not collection_urls:
            return None
        
        scraped_dfs = []

    def scrape_collection(self):
        '''
        Scrapes all records in a collection with urls contained in self.collection_urls.
        Returns Pandas.DataFrame.
        '''
        if not self.authenticated_driver:
            raise AuthenticationError('Please authenticate before attempting to collect urls.')
        else:
            driver = self.authenticated_driver
        collection_urls = self.collection_urls
        if not collection_urls:
            return None
        collection_dfs = []
        for labels, url_dict in collection_urls.items():
            record_dfs = []
            for date_range, url in url_dict.items():
                driver, df_record = scrape_record(driver, url)
                df_record.insert(0, 'Record Date Range', date_range) 
                record_dfs.append(df_record)
            df_label = pd.concat(record_dfs, axis=0, ignore_index=True)
            for label_name, label_value in labels[::-1]:
                df_label.insert(0, label_name, label_value)
            collection_dfs.append(df_label)
        df_collection = pd.concat(collection_dfs, axis=0, ignore_index=True)

        return df_collection  

    def shut_down(self):
        '''
        Close chromedriver.
        '''
        driver = self.authenticated_driver
        if driver:
            driver.close()
        
        return None
# %%
