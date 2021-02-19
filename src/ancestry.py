'''
Author: Henry Yeomans
Created: 2020-12

Class: AncestryScraper
A selenium-based webscraping bot which gathers parish records from Ancestry.co.uk.
'''


import os

from bs4 import BeautifulSoup
from selenium import webdriver    # conda install selenium
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


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


class AncestryScraper:
    '''
    A selenium-based bot which scrapes parish data from ancestry.co.uk.
    '''

    def __init__(self):
        self.authenticated_driver = None


    def authenticate(self):
        '''
        Boots up a chrome webdriver with minimal detectability, signs into ancestry, accepting cookies.
        Returns WebDriver.Chrome at welcome page.
        '''
        # Sign in details
        USERNAME = os.getenv('ANC_USERNAME', None)
        PASSWORD = os.getenv('ANC_PASSWORD', None)
        if not (USERNAME and PASSWORD):
            raise AuthenticationError('No username and/or password found in environment variables. Ensure these are set before attempting to authenticate.')
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


    def shut_down(self):
        '''
        Close chromedriver.
        '''
        driver = self.authenticated_driver
        if driver:
            driver.close()
        
        return None

