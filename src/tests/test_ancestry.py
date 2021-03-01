import pytest
import selenium
import mock
import numpy as np
import pandas as pd

from flask import Flask, request
from parish_scraper.ancestry import *
from selenium import webdriver    
from tests.conftest import WebServer

class Store:
#==============================================================================
#============================test_accept_cookies===============================
    mock_html_cookies = '''
                        <html><body><div id="Banner_cookie_0">
                        <div></div><div><div><div></div><div><div>
                        <button onclick="location.href='http://127.0.0.1:1337/?cookies=accepted'" type="button">Accept cookies
                        </button><button>Reject Cookies</button></div></div></div></div></div>
                        </body></html>
                        '''
#==============================================================================
#============================test_sign_in======================================
    mock_html_iframe = '''
                        <html>
                        <input id="username" placeholder="Email address or Username"></input>
                        <input id="password" placeholder="Password"></input>
                        <button id="signInBtn" onclick="location.href='http://127.0.0.1:1337/?cookies=accepted'" type="button">
                        Sign in</button>
                        </html>
                        '''
    mock_html_signin = '''
                        <html><body><div><iframe id="signInFrame" src="http://127.0.0.1:1337/signin?iframe=true">
                        #document
                        </iframe></div></body></html>
                       '''
#==============================================================================
#============================test_collect_urls=================================
    base_url = r'http:/127.0.0.1:1337'
    mock_urls_html = '''
                     <html><div id="divBL_4"><div><ul>
                     <li><a href="/hello/example">hello example</a></li>
                     <li><a href="/world/whatever">world whatever<a></li>
                     </ul></div></div></html>
                     '''
    expected_url_key = ('hello', 'world', '123', 'abc')
    expected_urls_dict = {'hello example': 'http://127.0.0.1:1337/hello/example', 
                          'world whatever': 'http://127.0.0.1:1337/world/whatever'}
    mock_option_names = ['hello', 'world', '123', 'abc']
#==============================================================================
#============================test_get_browse_levels============================
    mock_bc_html = '''
                   <html><div id="browseControls">
                   <label>Hello</label>
                   <label>World</label>
                   <label>Example</label>
                   <label>Whatever</label>
                   </div></html>
                   '''
    expected_labels = ('Hello', 'World', 'Example', 'Whatever')
#==============================================================================
#============================test_get_useful_elements==========================
    def display(table_button='', next_page_button='', grid_container_html=''):
        html = '''
                <html>
                <div class="paging-wrapper" id="buttonsPanel">
                <button {}>Table</button>
                <span class="imageCountText middle">123</span>
                </div>
                <button class="page" {}>Next Page</button>
                <div class="index-panel">Index Panel
                <div class="grid-container">{}</div>
                </div>
                </html>
                '''.format(table_button, next_page_button, grid_container_html)
        return html

    mock_elements_html = display()

    expected_paging_wrapper_id = 'buttonsPanel'

    expected_elements_text = {'buttons_panel'    : 'Table 123',
                              'table_button'     : 'Table',
                              'next_page_button' : 'Next Page',
                              'num_pages'        : '123',
                              'index_panel'      : 'Index Panel'}
#==============================================================================
#============================test_get_useful_elements==========================
    mock_enabled_html = display('', '', '<div>Hello World</div>')
    mock_disabled_html = display('disabled', '', '<div>Disabled Button</div>')
    expected_gc_html = '<div>Hello World</div>'
#==============================================================================
#============================test_get_useful_elements==========================
#%%
    def generate_table_html(data):
        rows = []
        for row in data:
            cells = []
            for cell in row:
                cell_html = '<div>{}</div>'.format(cell)
                cells.append(cell_html)
            row_html = '<div class="grid-row">{}</div>'.format(''.join(cells))
            rows.append(row_html)
        table_html = ''.join(rows)
        return table_html
#%%
    mock_table_html = generate_table_html((('Test Column 1', 'Test Column 2', 'Test Column 3'), 
                                            ('Hello', 'Test', '123'),
                                            ('World', 'Example', 'abc')))

    expected_table_df = pd.DataFrame({'Test Column 1' : ['Hello', 'World'],
                                      'Test Column 2' : ['Test', 'Example'],
                                      'Test Column 3' : ['123', 'abc']})                                    
#==============================================================================
#============================test_get_useful_elements==========================
    mock_p2_table_html = generate_table_html((('Test Column 1', 'Test Column 2', 'Test Column 3', 'Test Column 4'), 
                                            ('Goodbye', 'Whatever', '987', 'True'),
                                            ('Universe', 'Mock', 'xyz', 'False')))

    on_click = '''
               onclick="location.href='http://127.0.0.1:1337/imageviewer?page=2'" type="button"
               '''

    mock_p1_html = display('', on_click, mock_table_html)
    mock_p2_html = display('', 'disabled', mock_p2_table_html)
    expected_df_concat = pd.DataFrame({'Test Column 1' : ['Hello', 'World', 'Goodbye', 'Universe'],
                                       'Test Column 2' : ['Test', 'Example', 'Whatever', 'Mock'],
                                       'Test Column 3' : ['123', 'abc', '987', 'xyz'],
                                       'Test Column 4' : [np.nan, np.nan, 'True', 'False']}) 
#==============================================================================
store = Store()

@pytest.fixture(scope="module")
def scraper_server():
    app = Flask("scraper_server")
    server = WebServer(app)

    @server.app.route('/', methods=['GET', 'POST'])
    def display_page():
        cookies = request.args.get('cookies')
        if cookies == 'notAccepted':
            html = store.mock_html_cookies
        elif cookies == 'accepted':
            html = '<html><p>success</p></html>'
        else:
            html = '<html><p>home</p></html>'
        return html

    @app.route('/signin', methods=['GET', 'POST'])
    def display_signin():
        is_iframe = request.args.get('iframe')
        if is_iframe:
            html = store.mock_html_iframe
        else:
            html = store.mock_html_signin
        return html

    @app.route('/urls', methods=['GET', 'POST'])
    def display_urls():
        browse = request.args.get('browse')
        if browse:
            html = store.mock_bc_html
        else:
            html = store.mock_urls_html
        return html

    @app.route('/imageviewer')
    def display_image_viewer():
        is_table = request.args.get('table')
        button   = request.args.get('button')
        page     = request.args.get('page')
        if page == '0':
            if is_table:
                pass
            else:
                if button == 'enabled':
                    html = store.mock_enabled_html
                elif button == 'disabled':
                    html = store.mock_disabled_html
                else:
                    html = store.mock_elements_html
        elif page == '1':
            html = store.mock_p1_html
        elif page == '2':
            html = store.mock_p2_html
        return html

    with server.run():
        yield server
    

class MockInputElement(selenium.webdriver.remote.webelement.WebElement):

    def __init__(self, parent, id_):
        super().__init__(parent, id_)
    
    def send_keys(self, value):
        super().send_keys(value)
        assert self.get_attribute('value') == value
        return

driver = webdriver.Chrome()

def test_accept_cookies(scraper_server):
    global driver
    driver.get(r'http://127.0.0.1:1337/?cookies=notAccepted')
    driver = accept_cookies(driver)
    p_success = driver.find_element_by_css_selector('p')
    assert p_success.text == 'success'



@mock.patch('selenium.webdriver.remote.webelement.WebElement', side_effect=MockInputElement)
def test_sign_in(scraper_server):
    global driver
    driver.get(r'http://127.0.0.1:1337/signin')
    driver = sign_in(driver, username='hello', password='world')
    p_success = driver.find_element_by_css_selector('p')
    assert p_success.text == 'success'



def test_collect_urls(scraper_server):
    global driver
    driver.get(r'http://127.0.0.1:1337/urls')
    driver, url_key, urls_dict = collect_urls(driver, store.mock_option_names)
    assert url_key == store.expected_url_key
    print(urls_dict)
    assert urls_dict == store.expected_urls_dict



def test_get_browse_labels(scraper_server):
    global driver
    driver.get(r'http://127.0.0.1:1337/urls?browse=True')
    labels = get_browse_labels(driver)
    assert labels == store.expected_labels


def test_get_useful_elements(scraper_server):
    global driver
    driver.get(r'http://127.0.0.1:1337/imageviewer?page=0')
    elements = get_useful_elements(driver)
    assert elements.keys() == store.expected_elements_text.keys()
    for key, element in elements.items():
        if key == 'num_pages':
            assert element == store.expected_elements_text[key]
        else:
            assert element.text == store.expected_elements_text[key]



def test_get_table_html(scraper_server):
    global driver
    driver.get(r'http://127.0.0.1:1337/imageviewer?page=0&button=enabled')
    elements = get_useful_elements(driver)
    driver, gc_html = get_table_html(driver, **elements)
    assert gc_html == store.expected_gc_html
    driver.get(r'http://127.0.0.1:1337/imageviewer?page=0&button=disabled')
    elements = get_useful_elements(driver)
    driver, gc_html = get_table_html(driver, **elements)
    assert gc_html is None


def test_make_grid_container_df():
    actual_df = make_grid_container_df(store.mock_table_html)
    assert actual_df.equals(store.expected_table_df)


def test_scrape_record(scraper_server):
    global driver
    driver, df_concat = scrape_record(driver, r'http://127.0.0.1:1337/imageviewer?page=1')
    assert df_concat.equals(store.expected_df_concat)


def test_close():
    global driver
    driver.close()