import demistomock as demisto
from CommonServerPython import *
from CommonServerUserPython import *

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import sys
import base64

PROXY = demisto.getParam('proxy')

if PROXY:
    HTTP_PROXY = os.environ.get('http_proxy')
    HTTPS_PROXY = os.environ.get('https_proxy')

WITH_ERRORS = demisto.params().get('with_error', True)


def init_driver():
    demisto.debug('Creating chrome driver')

    with open('log.txt', 'w') as log:
        sys.stdout = log
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--disable_infobars')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--start-fullscreen')
        chrome_options.add_argument('--ignore-certificate-errors')

        driver = webdriver.Chrome(executable_path=ChromeDriverManager().install(), options=chrome_options)

    sys.stdout = sys.__stdout__
    demisto.debug('creating chrome driver - FINISHED')

    return driver


def rasterize(file_name: str, path: str, width: int, height: int, r_type='png'):
    driver = init_driver()

    try:
        demisto.debug('Navigating to url')

        driver.get(path)
        driver.implicitly_wait(5)

        demisto.debug('Navigating to url - FINISHED')

        if r_type == 'pdf':
            result = get_pdf(driver, file_name, width, height)
        else:
            result = get_image(driver, file_name, width, height)

        return result

    except NoSuchElementException as ex:
        if 'invalid argument' in str(ex):
            message = "Can't access the URL. It might be malicious, or unreachable for one of several reasons. " \
                      "You can choose to receive this errors as warnings in the instance settings"
            return_error(message) if WITH_ERRORS else return_warning(message)

        return_error(str(ex)) if WITH_ERRORS else return_warning(str(ex))


def get_image(driver, file_name: str, width: int, height: int):
    demisto.debug('Taking Screenshot and saving it')

    # Set windows size
    driver.set_window_size(width, height)

    image = driver.get_screenshot_as_png()
    driver.quit()

    file = fileResult(filename=file_name, data=image)
    file['Type'] = entryTypes['image']
    demisto.debug('Taking Screenshot and saving it - FINISHED')

    return file


def get_pdf(driver, file_name: str, width: int, height: int):
    demisto.debug("Taking PDF and saving it")

    driver.set_window_size(width, height)
    resource = f"{driver.command_executor._url}/session/{driver.session_id}/chromium/send_command_and_get_result"
    body = json.dumps({'cmd': 'Page.printToPDF', 'params': {'landscape': False}})
    response = driver.command_executor._request('POST', resource, body)

    if response.get('status'):
        demisto.results(response.get('status'))
        return_error(response.get('value'))

    file = fileResult(filename=file_name, data=base64.b64decode(response.get('value').get('data')))
    file['Type'] = entryTypes['image']
    demisto.debug("Taking PDF and saving it - FINISHED")

    return file


def rasterize_command():
    url = demisto.getArg('url')
    width = demisto.getArg('width', 800)
    height = demisto.getArg('height', 1600)
    r_type = demisto.getArg('type', 'png')

    if not (url.startswith('http')):
        url = "http://" + url
    friendly_name = f'url.{"pdf" if r_type == "pdf" else "png"}'  # type: ignore
    proxy_flag = ""
    if PROXY:
        proxy_flag = f"--proxy={HTTPS_PROXY if url.startswith('https') else HTTP_PROXY}"  # type: ignore
    demisto.debug('rasterize proxy settings: ' + proxy_flag)

    results = rasterize(friendly_name, url, width, height, r_type)

    demisto.results(results)


def rasterize_image_command():
    url = demisto.getArg('url')
    width = demisto.getArg('width')
    height = demisto.getArg('height')

    if not (url.startswith('http')):
        url = f'http://{url}'
    friendly_name = 'url.png'  # type: ignore
    proxy_flag = ""
    if PROXY:
        proxy_flag = f"--proxy={HTTPS_PROXY if url.startswith('https') else HTTP_PROXY}"  # type: ignore
    demisto.debug('rasterize proxy settings: ' + proxy_flag)

    results = rasterize(friendly_name, url, width, height)

    demisto.results(results)


def rasterize_email_command():
    html_body = demisto.getArg('htmlBody')
    w = demisto.getArg('width', 800)
    h = demisto.getArg('height', 1600)
    r_type = demisto.getArg('type', 'png')

    name = f'email.{"pdf" if r_type == "pdf" else "png"}'  # type: ignore
    with open('htmlBody.html', 'w') as f:
        f.write(f'<html style="background:white";>{html_body}</html>')
        result = rasterize(file_name=name, path=f'file://{os.path.realpath(f.name)}', r_type=r_type, width=w, height=h)

    demisto.results(result)


def test():
    with open('htmlBody.html', 'w') as f:
        f.write('<html style="background:white";><head></head><body><div>Hello World!</div></body></html>')
        rasterize(file_name='test.png', path=f'file://{os.path.realpath(f.name)}', r_type='pdf', width=800, height=800)
    demisto.results('ok')
    sys.exit(0)


try:
    if demisto.command() == 'test-module':
        test()

    elif demisto.command() == 'rasterize-image':
        rasterize_image_command()

    elif demisto.command() == 'rasterize-email':
        rasterize_email_command()

    elif demisto.command() == 'rasterize':
        rasterize_command()

    else:
        return_error('Unrecognized command')

except Exception as ex:
    return_error(str(ex))
