from typing import List

import selenium.common.exceptions
from bs4 import BeautifulSoup
from selenium import webdriver
from six.moves.urllib.request import urlretrieve
import glob
import os
import re
import sys
import time
import zipfile

done = False
owd = os.getcwd()
downloadDir = owd + "/downloads"
try:
    os.mkdir(downloadDir)
except FileExistsError:
    pass

print(sys.argv)
print("Download Dir:" + downloadDir)
tag = sys.argv[1]
print(tag)
if tag.startswith("refs/tags"):
    tag = tag[10:]
if not tag.startswith("v"):
    raise Exception("Not start with v")
tag = tag[1:]
print(tag)
for downloadItem in os.listdir(downloadDir):
    print("Removing: " + downloadItem)
    os.remove(downloadDir + "/" + downloadItem)

chromeOptions = webdriver.ChromeOptions()
prefs = {"profile.default_content_settings.popups": 0,
         "download.default_directory": downloadDir,
         "safebrowsing.enabled": "false"}
chromeOptions.add_experimental_option("prefs", prefs)
if len(sys.argv) > 2 and sys.argv[2] == "headless":
    # chromeOptions.add_argument("--no-sandbox")#linux only
    chromeOptions.add_argument("--headless")

if os.path.isfile('chromedriver'):
    locationString = 'chromedriver'
else:
    response = urlretrieve('https://chromedriver.storage.googleapis.com/93.0.4577.15/chromedriver_linux64.zip',
                           'chromedriver.zip')
    print("Downloading Chromedriver because no Chromedriver exist")
    zip_ref = zipfile.ZipFile("chromedriver.zip", 'r')
    zip_ref.extractall(owd)
    zip_ref.close()
    locationString = 'chromedriver'
    os.remove("chromedriver.zip")

driver = webdriver.Chrome(executable_path=locationString, options=chromeOptions)
driver.set_page_load_timeout(600)

siteString = "https://anuke.itch.io/mindustry"

driver.get(siteString)
print("10%")
driver.find_element_by_xpath("//a[@class='button buy_btn']").click()
time.sleep(2)
print("20%")
driver.find_element_by_xpath("//a[@class='direct_download_btn']").click()
time.sleep(2)
print("30%")
downloadListSize = len(driver.find_elements_by_xpath("//a[@class='button download_btn']"))
percentage = 30
i = -1
for x in driver.find_elements_by_xpath("//a[@class='button download_btn']"):
    i += 1
    percentage += int(40 / downloadListSize)
    version = \
    str(driver.find_elements_by_class_name("upload")[i].find_element_by_class_name("version_name").text).split(" ")[1]
    if not tag == version:
        downloadListSize -= 1
        continue
    x.click()
    time.sleep(2)
    try:
        driver.find_element_by_xpath('//*[@id="lightbox_container"]/div/div/button').click()
    except selenium.common.exceptions.NoSuchElementException:
        pass
    time.sleep(1)

    print(str(percentage) + "%")

while len(os.listdir(downloadDir)) != downloadListSize:
    time.sleep(1)

downloading = True
while downloading:
    downloading = False
    for file in os.listdir(downloadDir):
        if file.endswith(".crdownload"):
            downloading = True
            break

print("75%")
os.chdir(downloadDir)
time.sleep(2)
print("95%")
driver.close()

print("Closing driver")
for downloadItem in os.listdir(downloadDir):
    renamed = downloadItem
    renamed = renamed.lower()
    renamed = renamed.replace("[android]", "")
    renamed = renamed.replace("-unstable", "")
    renamed = renamed.replace("[v" + tag + "]", "")
    os.rename(downloadItem, renamed)
    print("Downloaded: " + downloadItem + ", renamed to: " + renamed)

if __name__ == '__main__':
    pass
