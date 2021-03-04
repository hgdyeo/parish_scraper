'''
Author: Henry Yeomans
Created: 2021-01-20

Class: FamilySearchScraper.
A selenium-based webscraping bot which gathers burial data from FamilySearch.org.
'''
#%%
import numpy as np
import pandas as pd
import requests
import re
import os
import pickle
import urllib
import urllib.parse as urlparse
import math
import time

from urllib.parse import urlencode
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from pyshadow.main import Shadow


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
    option.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36")
    #Open Browser
    driver = webdriver.Chrome(executable_path='chromedriver.exe',options=option)
    driver.maximize_window()

    return driver


def accept_cookies(driver):
    iframe_xpath = r'/html/body/div[3]/div/iframe'
    frame = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,iframe_xpath)))
    if frame.is_displayed():
        driver.switch_to.frame(frame)
    xpath_agree = r'/html/body/div[8]/div[1]/div/div[3]/a[1]'
    agree_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath_agree)))
    agree_button.click()

    return driver


def sign_in(driver, username, password):
    xpath_username = r'//*[@id="userName"]'
    xpath_password = r'//*[@id="password"]'
    xpath_signin  = r'//*[@id="login"]'
    user_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,xpath_username)))
    pass_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,xpath_password)))
    signin_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,xpath_signin)))
    user_input.send_keys(username)
    pass_input.send_keys(password)
    signin_button.click()
    time.sleep(5)

    if driver.current_url != r'https://www.familysearch.org/':
        raise AuthenticationError('Sign-in failed. Please ensure username and password are correct.')

    return driver


def scrape_table(shadow_driver, table):
    '''
    Returns Name and Date data contained within the web element table.
    '''
    rows = table.find_elements_by_tag_name(r'div')
    # table_data = []
    names = []
    dates = []
    places = []
    for row in rows[1:]:
        cell_name = row.find_element_by_css_selector(r'span > sr-cell-name') 
        cell_name_text = cell_name.get_attribute('name')
        cell_event = row.find_element_by_css_selector(r'span > sr-cell-events')

        cell_event_types = shadow_driver.find_elements(cell_event, r'span.event-type')
        cell_event_texts = [event_type.text for event_type in cell_event_types]
        
        cell_dates = shadow_driver.find_elements(cell_event, r'span.event-date')
        cell_date_texts = [cell_date.text for cell_date in cell_dates]

        cell_places = shadow_driver.find_elements(cell_event, r'span.event-place')
        cell_place_texts = [cell_place.text for cell_place in cell_places]

        cell_info = list(zip(cell_event_texts, cell_date_texts, cell_place_texts))
        # Take only burial info
        pattern = re.compile(r'(B|b)urial')
        burial_info = [info for info in cell_info if pattern.match(info[0])]
        if burial_info:
            burial_date = burial_info[0][1]
            burial_place = burial_info[0][2]
            dates.append(burial_date)
            places.append(burial_place)
            names.append(cell_name_text)

    table_data = {'Name' : names, 'Date' : dates, 'Place' : places}

    return table_data

        
def get_max_offset(shadow):
    '''
    Returns the maximum value for the offset query string given the number of results found.
    '''
    num_results_element = shadow.find_element(r'p.search-criteria')
    pattern = re.compile(r'of [0-9]+ Results')
    num_results_text = num_results_element.text.replace(',', '')
    num_results = int(pattern.findall(num_results_text)[0][3:-8])
    max_offset = 100 * math.floor(num_results/100)
    
    return max_offset


class QuietShadow(Shadow):
    '''
    Modified Shadow object without irritating print('QA--QAQA True') in is_present method.
    '''
    def __init__(self, driver):
        super().__init__(driver)
        
    def is_present(self, element):
        present = self.executor_get_object("return isVisible(arguments[0]);", element)
        return present


class FamilySearchScraper:
    '''
    A selenium-based bot that scrapes burial records from FamilySearch.org.
    '''

    def __init__(self):
        self.authenticated_driver = None

    def authenticate(self):
        # Sign in details
        USERNAME = os.getenv('FS_USERNAME', None)
        PASSWORD = os.getenv('FS_PASSWORD', None)

        if not (USERNAME and PASSWORD):
            raise AuthenticationError('No username and/or password found in environment variables. Ensure these are set before attempting to authenticate.')

        driver = boot_up_driver()

        # Go to URL
        url_signin = r'https://www.familysearch.org/auth/familysearch/login'
        driver.get(url_signin)
        driver = sign_in(driver, USERNAME, PASSWORD)

        # Occasionally, an invitation to complete a survey appears now. If so, dismiss it.
        xpath_survey_button = r'//*[@id="pagekey__home__lihp_arches"]/div[5]/div[2]/div/div[3]/button[2]'
        try:
            no_survey_button = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, xpath_survey_button)))
            no_survey_button.click()
        except:
            pass
        
        driver = accept_cookies(driver)

        self.is_authenticated = True
        self.authenticated_driver = driver

        return driver

    def get_burial_records(self, place_name, year_from, year_to):
        '''
        Scrapes Name and Burial columns from FamilySearch.org records 
        for place_name, between year_from and year_to inclusive.
        Returns: pandas.DataFrame with columns ('Name', 'Date')
        '''
        if self.authenticated_driver:
            driver = self.authenticated_driver
        else:
            raise AuthenticationError('Please authenticate FamilySearch account.')

        list_dfs = []
        for year in range(year_from, year_to + 1):
            
            dfs_year = []
            more_pages = True
            offset = 0
            max_offset = False
            
            while more_pages:
                params = {
                        'q.deathLikePlace'                : '{}'.format(place_name),
                        'q.deathLikePlace.exact'          : 'on',
                        'q.deathLikeDate.from'            : '{}'.format(year),
                        'q.deathLikeDate.to'              : '{}'.format(year),
                        'm.defaultFacets'                 : 'on',
                        'm.queryRequireDefault'           : 'on',
                        'm.facetNestCollectionInCategory' : 'on',
                        'count'                           : '100',
                        'offset'                          : '{}'.format(offset)
                        }
                base_results_url  = r'https://www.familysearch.org/search/record/results/?'
                query_results_url = base_results_url + urlencode(params)
                driver.get(query_results_url)
                
                shadow = QuietShadow(driver)
                success = False
                while not success:
                    try:
                        spinner = shadow.find_element(r'fs-spinner')
                        table_displayed = WebDriverWait(driver, 10).until(lambda x : bool(spinner.get_attribute('style')))
                        sr_table = shadow.find_element(r'div.table')
                        success = True
                    except:
                        driver.refresh()

                if table_displayed:
                    # Try finding the number of results
                    if not max_offset:
                        try:
                            max_offset = get_max_offset(shadow)
                        # If exception thrown, assume no results found.
                        except:
                            break
                    
                    table_data = scrape_table(shadow, sr_table)

                    # Make DataFrame:
                    df = pd.DataFrame(table_data)
                    dfs_year.append(df)

                offset += 100
                more_pages = (offset <= max_offset)
                
            # If there are any results for that year, concatenate them and append to list_dfs
            if dfs_year:
                df_year = pd.concat(dfs_year, axis=0, ignore_index=True)
                list_dfs.append(df_year)

        # If search query returned any results, concatenate them:
        if list_dfs:    
            df_all = pd.concat(list_dfs, axis=0, ignore_index=True)
        else:
            df_all = pd.DataFrame()

        return df_all 

    def shut_down(self):
        '''
        Close chromedriver.
        '''
        driver = self.authenticated_driver
        if driver:
            driver.close()
        
        return None


# %%
def get_burial_records(driver, place_name, year_from, year_to):
    '''
    Scrapes Name and Burial columns from FamilySearch.org records 
    for place_name, between year_from and year_to inclusive.
    Returns: pandas.DataFrame with columns ('Name', 'Date')
    '''

    list_dfs = []
    for year in range(year_from, year_to + 1):
        
        dfs_year = []
        more_pages = True
        offset = 0
        max_offset = False
        
        while more_pages:
            params = {
                    'q.deathLikePlace'                : '{}'.format(place_name),
                    'q.deathLikePlace.exact'          : 'on',
                    'q.deathLikeDate.from'            : '{}'.format(year),
                    'q.deathLikeDate.to'              : '{}'.format(year),
                    'm.defaultFacets'                 : 'on',
                    'm.queryRequireDefault'           : 'on',
                    'm.facetNestCollectionInCategory' : 'on',
                    'count'                           : '100',
                    'offset'                          : '{}'.format(offset)
                    }
            base_results_url  = r'https://www.familysearch.org/search/record/results/?'
            query_results_url = base_results_url + urlencode(params)
            driver.get(query_results_url)
            shadow = QuietShadow(driver)
            section_right = shadow.find_element(r'div > section.right')
            spinner = shadow.find_element(section_right, r'fs-spinner')
            table_displayed = WebDriverWait(driver, 10).until(lambda x : bool(spinner.get_attribute('style')))
            try:
                shadow.find_element(section_right, r'div.fs-alert')
                driver.refresh()
            except:
                try:
                    max_offset = get_max_offset(shadow)
                except:
                    break
            
            sr_table = shadow.find_element(r'div.table')
                
            table_data = scrape_table(shadow, sr_table)

            # Make DataFrame:
            df = pd.DataFrame(table_data)
            dfs_year.append(df)
            print('year: ', year)
            print('len(df): ', len(df))

            offset += 100
            more_pages = (offset <= max_offset)
            
        # If there are any results for that year, concatenate them and append to list_dfs
        if dfs_year:
            df_year = pd.concat(dfs_year, axis=0, ignore_index=True)
            list_dfs.append(df_year)

    # If search query returned any results, concatenate them:
    if list_dfs:    
        df_all = pd.concat(list_dfs, axis=0, ignore_index=True)
    else:
        df_all = pd.DataFrame()

    return df_all 
