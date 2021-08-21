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

for downloadItem in os.listdir(downloadDir):
    print("Removing: " + downloadItem)
    os.remove(downloadDir+"/"+downloadItem)

chromeOptions = webdriver.ChromeOptions()
prefs = {"profile.default_content_settings.popups": 0,
         "download.default_directory": downloadDir,
         "safebrowsing.enabled": "false"}
chromeOptions.add_experimental_option("prefs", prefs)
if len(sys.argv) > 2 and sys.argv[2] == "headless":
    #chromeOptions.add_argument("--no-sandbox")#linux only
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
for x in driver.find_elements_by_xpath("//a[@class='button download_btn']"):
    x.click()
    time.sleep(2)
    try:
        driver.find_element_by_xpath('//*[@id="lightbox_container"]/div/div/button').click()
    except selenium.common.exceptions.NoSuchElementException:
        pass
    time.sleep(1)
    percentage += 40 / downloadListSize
    print(str(percentage) + "%")

while len(os.listdir(downloadDir)) != downloadListSize:
    time.sleep(1)

print("75%")
os.chdir(downloadDir)
for downloadItem in os.listdir(downloadDir):
    if sys.argv[1] not in downloadItem:
        print("Deleting: " + downloadItem)
        os.remove(downloadItem)

print("80%")
percentage = 80
globSize = len(glob.glob("*.zip"))
for file in glob.glob("*.zip"):
    print("Extracting " + str(file))
    zip_ref = zipfile.ZipFile(file, 'r')
    zip_ref.extractall(owd)
    zip_ref.close()
    percentage += 20 / downloadListSize
    print(str(percentage) + "%")

time.sleep(2)
print("100%")
driver.close()

print("Closing driver")
for downloadItem in os.listdir(downloadDir):
    print("Downloaded: " + downloadItem)

if __name__ == '__main__':
    pass