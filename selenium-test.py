from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Подключение к Selenium Grid
options = webdriver.ChromeOptions()
driver = webdriver.Remote(
    command_executor="http://localhost:4444/wd/hub",
    options=options
)

# Открываем веб-страницу
driver.get("https://www.google.com")

# Находим поле поиска и вводим текст
search_box = driver.find_element(By.NAME, "q")
search_box.send_keys("Selenium with Docker")
search_box.send_keys(Keys.RETURN)
print("Searching for 'Selenium with Docker'...")
# Закрываем браузер
driver.quit()