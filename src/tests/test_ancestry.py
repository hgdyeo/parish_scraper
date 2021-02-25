import pytest
import selenium
import mock

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
        return store.mock_urls_html

    with server.run():
        yield server


class MockInputElement(selenium.webdriver.remote.webelement.WebElement):

    def __init__(self, parent, id_):
        super().__init__(parent, id_)
    
    def send_keys(self, value):
        super().send_keys(value)
        assert self.get_attribute('value') == value
        return


def test_accept_cookies(scraper_server):
    driver = webdriver.Chrome()
    driver.get(r'http://127.0.0.1:1337/?cookies=notAccepted')
    driver = accept_cookies(driver)
    p_success = driver.find_element_by_css_selector('p')
    assert p_success.text == 'success'
    driver.close()


@mock.patch('selenium.webdriver.remote.webelement.WebElement', side_effect=MockInputElement)
def test_sign_in(scraper_server):
    driver = webdriver.Chrome()
    driver.get(r'http://127.0.0.1:1337/signin')
    driver = sign_in(driver, username='hello', password='world')
    p_success = driver.find_element_by_css_selector('p')
    assert p_success.text == 'success'
    driver.close()


def test_sign_in_exception(scraper_server):
    driver = webdriver.Chrome()
    driver.get(r'http://127.0.0.1:1337/')
    with pytest.raises(AuthenticationError):
        driver = sign_in(driver, username='hello', password='world')
    driver.close()


def test_collect_urls(scraper_server):
    driver = webdriver.Chrome()
    driver.get(r'http://127.0.0.1:1337/urls')
    driver, url_key, urls_dict = collect_urls(driver, store.mock_option_names)
    assert url_key == store.expected_url_key
    print(urls_dict)
    assert urls_dict == store.expected_urls_dict
    driver.close()

