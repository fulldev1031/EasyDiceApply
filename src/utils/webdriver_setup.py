from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium_stealth import stealth
import zipfile
import os
import shutil
import base64
import json

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
    uploads_dir = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    extension_dir = os.path.join(uploads_dir, 'proxy_extension')
    os.makedirs(extension_dir, exist_ok=True)

    # Write manifest.json and background.js to the extension directory
    with open(os.path.join(extension_dir, 'manifest.json'), 'w') as f:
        f.write(manifest_json)
    with open(os.path.join(extension_dir, 'background.js'), 'w') as f:
        f.write(background_js)

    return extension_dir

def setup_driver(proxy=None, proxy_auth=None):
    """Initialize and configure the Chrome WebDriver with optional proxy settings."""
    options = webdriver.ChromeOptions()
    # Headless mode
    options.add_argument('--headless')  # Run browser in headless mode
    options.add_argument('--disable-gpu')  # Disable GPU acceleration
    options.add_argument('--no-sandbox')  # Bypass OS security model
    options.add_argument('--disable-dev-shm-usage')  # Overcome resource limitations
    # Disable bot-detection features
    # options.add_argument('--disable-notifications')
    # options.add_argument('--start-maximized')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Suppress extension warnings
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])

    try:
        if proxy:
            proxy_host, proxy_port = proxy.split(':')
            if proxy_auth:
                proxy_username, proxy_password = proxy_auth
                
                # Create proxy extension
                extension_dir = create_proxy_extension(proxy_host, proxy_port, proxy_username, proxy_password)
                
                # Load the extension
                options.add_argument(f'--load-extension={extension_dir}')
                
                # Disable other extensions to prevent conflicts
                options.add_argument(f'--disable-extensions-except={extension_dir}')
                
                # Set proxy directly as well for redundancy
                options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')
            else:
                options.add_argument(f'--proxy-server=http://{proxy_host}:{proxy_port}')

        driver = webdriver.Chrome(options=options)
        
        # Apply stealth mode
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        # WebDriver wait instance
        wait = WebDriverWait(driver, 20)
        return driver, wait

    except WebDriverException as e:
        print(f"WebDriver failed to initialize with proxy: {proxy}. Error: {e}")
        return None, None

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password, plugin_path):
    """Create a dedicated proxy auth extension specifically for handling authentication dialogs."""
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 3,
        "name": "Proxy Auth Handler",
        "permissions": ["webRequest"],
        "host_permissions": ["<all_urls>"],
        "background": {
            "service_worker": "background.js"
        }
    }
    """
    
    background_js = f"""
    // Handle proxy auth
    chrome.webRequest.onAuthRequired.addListener(
        function(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_username}",
                    password: "{proxy_password}"
                }}
            }};
        }},
        {{urls: ["<all_urls>"]}},
        []
    );

    // Add basic auth headers to all requests
    chrome.webRequest.onBeforeSendHeaders.addListener(
        function(details) {{
            const authHeader = 'Basic ' + btoa('{proxy_username}:{proxy_password}');
            let hasProxyAuth = false;
            
            for (let i = 0; i < details.requestHeaders.length; i++) {{
                if (details.requestHeaders[i].name === 'Proxy-Authorization') {{
                    details.requestHeaders[i].value = authHeader;
                    hasProxyAuth = true;
                    break;
                }}
            }}
            
            if (!hasProxyAuth) {{
                details.requestHeaders.push({{
                    name: 'Proxy-Authorization',
                    value: authHeader
                }});
            }}
            
            return {{requestHeaders: details.requestHeaders}};
        }},
        {{urls: ["<all_urls>"]}},
        ["requestHeaders", "extraHeaders"]
    );
    """
    
    # Create a ZIP file of the extension
    os.makedirs(os.path.dirname(plugin_path), exist_ok=True)
    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)
