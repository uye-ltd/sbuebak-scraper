import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from src.config import Config

log = logging.getLogger(__name__)


def create_driver(config: Config) -> webdriver.Chrome:
    options = Options()

    if config.headless:
        options.add_argument("--headless=new")

    w, h = config.window_size
    options.add_argument(f"--window-size={w},{h}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ru")

    # Reduce bot-detection signals
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")

    # "none" returns immediately after the request is sent, without waiting for
    # DOMContentLoaded or any resources. VK's React bootstrap alone takes ~20s
    # before DOMContentLoaded fires, so "eager" still blocks for that full time.
    # With "none" we wait only for the specific DOM elements we actually need
    # via explicit WebDriverWait calls in scraper.py.
    options.page_load_strategy = "none"

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(config.implicit_wait_sec)

    # Patch navigator.webdriver to undefined
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    return driver


def wait_for_manual_login(driver: webdriver.Chrome, login_url: str) -> None:
    """
    Navigate to the VK login page and block until the user completes login.
    Detection: the URL changes away from the login/feed page once authenticated.
    """
    driver.get(login_url)
    log.info("Browser opened. Please log in to VK manually.")

    print("Press ENTER here once you are logged in and see your feed… ", end="", flush=True)
    input()
    log.info("Login confirmed. Continuing.")
