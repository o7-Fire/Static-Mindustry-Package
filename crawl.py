import os
import sys
import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def create_driver(download_dir, headless):
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": False,
        "profile.default_content_setting_values.automatic_downloads": 1,
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

        download_page = driver.current_url
        uploads = driver.find_elements(By.CSS_SELECTOR, ".upload")
        buttons = driver.find_elements(By.CSS_SELECTOR, "a.button.download_btn, a.download_btn")
        targets = []

        for i in range(len(buttons)):
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
            targets.append(i)

        if not targets:
            targets = list(range(len(buttons)))

        expected = len(targets)
        started = 0
        last_percent = -1
        for index in targets:
            for attempt in range(3):
                if driver.current_url != download_page:
                    driver.get(download_page)
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".upload, a.download_btn"))
                    )
                buttons = driver.find_elements(By.CSS_SELECTOR, "a.button.download_btn, a.download_btn")
                if index >= len(buttons):
                    break
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", buttons[index])
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", buttons[index])

                deadline = time.time() + 60
                download_started = False
                while time.time() < deadline:
                    try:
                        dismiss = driver.find_element(By.CSS_SELECTOR, "#lightbox_container .close_btn, #lightbox_container button")
                        if dismiss.is_displayed():
                            dismiss.click()
                    except NoSuchElementException:
                        pass
                    files = os.listdir(download_dir)
                    current = len([f for f in files if not f.endswith(".crdownload")])
                    in_progress = any(f.endswith(".crdownload") for f in files)
                    if current > started or in_progress:
                        started = max(started, current)
                        download_started = True
                        break
                    time.sleep(1)
                if download_started:
                    break

            completed = len([f for f in os.listdir(download_dir) if not f.endswith(".crdownload")])
            if expected > 0:
                percent = min(100, int(completed * 100 / expected))
                if percent != last_percent:
                    print(f"{percent}% ({completed}/{expected})", flush=True)
                    last_percent = percent

        deadline = time.time() + 60
        while time.time() < deadline:
            files = os.listdir(download_dir)
            completed = [f for f in files if not f.endswith(".crdownload")]
            if expected > 0:
                percent = min(100, int(len(completed) * 100 / expected))
                if percent != last_percent:
                    print(f"{percent}% ({completed}/{expected})", flush=True)
                    last_percent = percent
            if files and not any(f.endswith(".crdownload") for f in files) and len(completed) >= expected:
                break
            time.sleep(1)
        else:
            raise TimeoutException("Timed out waiting for downloads")
    finally:
        driver.quit()

    for name in os.listdir(download_dir):
        renamed = name.lower().replace("[android]", "").replace("[pre-alpha]", "").replace("-unstable", "").replace(f"[v{tag}]", "")
        if renamed != name:
            os.rename(os.path.join(download_dir, name), os.path.join(download_dir, renamed))
        print(f"Downloaded: {name}, renamed to: {renamed}")


if __name__ == "__main__":
    main()
