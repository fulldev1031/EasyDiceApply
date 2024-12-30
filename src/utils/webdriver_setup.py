from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
import zipfile
import os

def create_proxy_extension(proxy_host, proxy_port, proxy_username=None, proxy_password=None):
    """Create a Chrome extension to handle proxy with optional authentication."""
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        }
    }
    """

    background_js = f"""
    var config = {{
            mode: "fixed_servers",
            rules: {{
              singleProxy: {{
                scheme: "http",
                host: "{proxy_host}",
                port: parseInt({proxy_port})
              }},
              bypassList: ["localhost","127.0.0.1"]
            }}
          }};
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
    """

    if proxy_username and proxy_password:
        background_js += f"""
                            function callbackFn(details) {{
                                return {{
                                    authCredentials: {{
                                        username: "{proxy_username}",
                                        password: "{proxy_password}"
                                    }}
                                }};
                            }}
                            chrome.webRequest.onAuthRequired.addListener(
                                callbackFn,
                                {{urls: ["<all_urls>"]}},
                                ['blocking']
                            );
                        """

    # Create a temporary directory to store the extension files
    extension_dir = os.path.join(os.getcwd(), 'proxy_extension')
    os.makedirs(extension_dir, exist_ok=True)

    # Write manifest.json and background.js to the extension directory
    with open(os.path.join(extension_dir, 'manifest.json'), 'w') as f:
        f.write(manifest_json)
    with open(os.path.join(extension_dir, 'background.js'), 'w') as f:
        f.write(background_js)

    # Create a ZIP file of the extension
    extension_path = os.path.join(os.getcwd(), 'uploads/proxy_auth_extension.zip')
    with zipfile.ZipFile(extension_path, 'w') as zp:
        zp.write(os.path.join(extension_dir, 'manifest.json'), 'manifest.json')
        zp.write(os.path.join(extension_dir, 'background.js'), 'background.js')

    # Clean up the temporary directory
    os.remove(os.path.join(extension_dir, 'manifest.json'))
    os.remove(os.path.join(extension_dir, 'background.js'))
    os.rmdir(extension_dir)

    return extension_path

def setup_driver(proxy=None, proxy_auth=None):
    """Initialize and configure the Chrome WebDriver with optional proxy settings."""
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-notifications')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)

    try:
        if proxy:
            proxy_host, proxy_port = proxy.split(':')
            if proxy_auth:
                proxy_username, proxy_password = proxy_auth
                extension_path = create_proxy_extension(proxy_host, proxy_port, proxy_username, proxy_password)
                options.add_extension(extension_path)
            else:
                options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20)
        return driver, wait

    except WebDriverException as e:
        print(f"WebDriver failed to initialize with proxy: {proxy}. Error: {e}")
        return None, None
