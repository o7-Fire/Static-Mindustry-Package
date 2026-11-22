import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote, urlparse

import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def filename_from_response(response, url):
    cd = response.headers.get("content-disposition", "")
    for part in cd.split(";"):
        part = part.strip()
        if part.lower().startswith("filename*="):
            value = part.split("=", 1)[1].strip().strip('"')
            if "''" in value:
                value = value.split("''", 1)[1]
            return unquote(value)
        if part.lower().startswith("filename="):
            return unquote(part.split("=", 1)[1].strip().strip('"'))
    name = os.path.basename(urlparse(response.url or url).path)
    return name or "download"


def download_file(session, url, download_dir):
    with session.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        name = filename_from_response(response, url)
        path = os.path.join(download_dir, name)
        with open(path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return name


def create_driver(download_dir, headless):
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": False,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    if headless:
        options.add_argument("--headless=new")

    chrome_path = os.environ.get("CHROME_PATH")
    if chrome_path:
        options.binary_location = chrome_path

    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chromedriver_path:
        return webdriver.Chrome(service=Service(chromedriver_path), options=options)
    return webdriver.Chrome(options=options)


def wait_click(driver, by, value, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        elements = driver.find_elements(by, value)
        for element in elements:
            if element.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                driver.execute_script("arguments[0].click();", element)
                return element
        time.sleep(0.5)
    raise TimeoutException(f"Clickable element not found: {value}")


def normalize_tag(tag):
    if tag.startswith("refs/tags/"):
        tag = tag[len("refs/tags/") :]
    if tag.startswith("v"):
        tag = tag[1:]
    return tag


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Missing tag argument")

    download_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    tag = normalize_tag(sys.argv[1])
    headless = len(sys.argv) > 2 and sys.argv[2] == "headless"

    for item in os.listdir(download_dir):
        os.remove(os.path.join(download_dir, item))

    driver = create_driver(download_dir, headless)
    driver.set_page_load_timeout(600)

    try:
        driver.get("https://anuke.itch.io/mindustry")
        try:
            wait_click(driver, By.CSS_SELECTOR, "a.button.buy_btn, a.buy_btn", timeout=20)
            time.sleep(2)
        except TimeoutException:
            driver.get("https://anuke.itch.io/mindustry/purchase")
            time.sleep(2)

        try:
            wait_click(driver, By.CSS_SELECTOR, "a.direct_download_btn, a[data-label='no_thanks']", timeout=20)
        except TimeoutException:
            try:
                wait_click(driver, By.PARTIAL_LINK_TEXT, "No thanks", timeout=10)
            except TimeoutException:
                pass
        time.sleep(2)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".upload, a.download_btn"))
        )

        uploads = driver.find_elements(By.CSS_SELECTOR, ".upload")
        buttons = driver.find_elements(By.CSS_SELECTOR, "a.button.download_btn, a.download_btn")
        download_urls = []

        for i, button in enumerate(buttons):
            version = ""
            if i < len(uploads):
                try:
                    version_text = uploads[i].find_element(By.CSS_SELECTOR, ".version_name").text
                    parts = version_text.split()
                    if parts:
                        version = parts[-1]
                except NoSuchElementException:
                    pass

            if version and version != tag:
                continue

            href = button.get_attribute("href")
            if href:
                download_urls.append(href)

        if not download_urls:
            for button in buttons:
                href = button.get_attribute("href")
                if href:
                    download_urls.append(href)

        cookies = driver.get_cookies()
        user_agent = driver.execute_script("return navigator.userAgent")
    finally:
        driver.quit()

    session = requests.Session()
    session.headers.update({"User-Agent": user_agent})
    for cookie in cookies:
        session.cookies.set(cookie.get("name"), cookie.get("value"), domain=cookie.get("domain"), path=cookie.get("path"))

    expected = len(download_urls)
    completed = 0
    last_percent = -1
    if expected == 0:
        return

    with ThreadPoolExecutor(max_workers=min(4, expected)) as executor:
        futures = [executor.submit(download_file, session, url, download_dir) for url in download_urls]
        for future in as_completed(futures):
            future.result()
            completed += 1
            percent = min(100, int(completed * 100 / expected))
            if percent != last_percent:
                print(f"{percent}%", flush=True)
                last_percent = percent

    for name in os.listdir(download_dir):
        renamed = name.lower().replace("[android]", "").replace("[pre-alpha]", "").replace("-unstable", "").replace(f"[v{tag}]", "")
        if renamed != name:
            os.rename(os.path.join(download_dir, name), os.path.join(download_dir, renamed))
        print(f"Downloaded: {name}, renamed to: {renamed}")


if __name__ == "__main__":
    main()
