from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QPushButton, QLineEdit, QSizePolicy, QShortcut, QLineEdit
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtGui import QKeySequence, QTextCharFormat, QTextCursor, QColor
from bs4 import BeautifulSoup
import sys
import requests
from selenium_test import set_driver  # Импортируем функцию для установки драйвера Selenium
from ScrollbarMarksWidget import ScrollbarMarks  # Импортируем класс для пометок на скроллбаре
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options

class WebScrapingInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Web Scraping Helper")
        self.setGeometry(100, 100, 1200, 800)

        # Main layout
        layout = QVBoxLayout()
        layout2 = QVBoxLayout()
        layout3 = QHBoxLayout()
        layoutFinal = QVBoxLayout()

        # URL input field
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter website URL...")
        self.url_input.setText("https://www.google.com")
                # Connect Enter key press to load_website
        self.url_input.returnPressed.connect(self.load_website)

        layoutFinal.addWidget(self.url_input)

        # Web view to display the website
        self.web_view = QWebEngineView(self)
        self.web_view.setUrl(QUrl("https://www.google.com"))
        self.web_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Update URL input field dynamically when web_view URL changes
        self.web_view.urlChanged.connect(self.update_url_input)
        layout.addWidget(self.web_view)

        # Load button
        self.load_button = QPushButton("Load Website", self)
        self.load_button.clicked.connect(self.load_website)
        layout.addWidget(self.load_button)

        # Text area to display HTML source
        self.html_view = QTextEdit(self)
        self.html_view.setReadOnly(True)
        layout2.addWidget(self.html_view)

        # Search bar for html_view (hidden by default)
        self.search_input_html = QLineEdit(self)
        self.search_input_html.setPlaceholderText("Search in HTML view...")
        self.search_input_html.setVisible(False)  # Initially hidden
        self.search_input_html.returnPressed.connect(self.search_in_html_view)  # Trigger search on Enter
        layout2.addWidget(self.search_input_html)

        # Shortcut to show the search bar
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.toggle_search_bar)

        # Scrape button
        self.scrape_button = QPushButton("Scrape HTML", self)
        self.scrape_button.clicked.connect(self.scrape_html)
        layout2.addWidget(self.scrape_button)

        self.fetch_button = QPushButton("Fetch HTML (Direct)", self)
        self.fetch_button.clicked.connect(self.fetch_html)
        layout2.addWidget(self.fetch_button)

        # Selenium Scrape button
        self.selenium_scrape_button = QPushButton("Scrape HTML (Selenium)", self)
        self.selenium_scrape_button.clicked.connect(self.selenium_scrape_html)
        layout2.addWidget(self.selenium_scrape_button)

        layout3.addLayout(layout)
        layout3.addLayout(layout2)
        layoutFinal.addLayout(layout3)
        container = QWidget()
        container.setLayout(layoutFinal)
        self.setCentralWidget(container)

        # Html view search functionality
        self.search_results = []  # Список всех найденных вхождений
        self.current_search_index = -1  # Текущий индекс вхождения

        self.next_result_shortcut = QShortcut(QKeySequence("F3"), self)
        self.next_result_shortcut.activated.connect(lambda: self.move_to_search_result(1))  # Следующее вхождение

        self.prev_result_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        self.prev_result_shortcut.activated.connect(lambda: self.move_to_search_result(-1))  # Предыдущее вхождение

        # Подключить сигнал contentsChanged к методу обновления размеров scrollbar_marks
        self.html_view.document().contentsChanged.connect(self.update_scrollbar_marks_size)

        # Создать виджет для пометок на скроллбаре
        self.scrollbar_marks = ScrollbarMarks(self.html_view.verticalScrollBar(), self)
        self.scrollbar_marks.setParent(self.html_view.verticalScrollBar())
        self.scrollbar_marks.move(0, 0)
        self.scrollbar_marks.resize(self.scrollbar_marks.width(), self.html_view.height())

        # Таймер для обработки завершения изменения размера окна
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)  # Таймер срабатывает только один раз
        self.resize_timer.timeout.connect(self.on_resize_finished)  # Подключить обработчик
        
    def resizeEvent(self, event):
        """Обновить размеры scrollbar_marks при изменении размеров окна."""
        super().resizeEvent(event)
        self.resize_timer.start(200) # Перезапустить таймер (200 мс задержка)

    def on_resize_finished(self):
        """Обработчик завершения изменения размера окна."""
        self.update_scrollbar_marks_size()
        self.update_scrollbar_marks()  # Обновить пометки на скроллбаре

    def update_url_input(self, url):
        self.url_input.setText(url.toString())

    def update_scrollbar_marks_size(self):
        """Обновить размеры scrollbar_marks в соответствии с размерами скроллбара."""
        scrollbar = self.html_view.verticalScrollBar()

        # Высота кнопок вверх и вниз
        button_height = scrollbar.style().pixelMetric(scrollbar.style().PM_ScrollBarExtent)
        
        # Новая высота scrollbar_marks
        new_height = scrollbar.height() - 2 * button_height

        # Переместить scrollbar_marks вниз, чтобы исключить верхнюю кнопку
        self.scrollbar_marks.move(0, button_height)

        # Установить новые размеры
        self.scrollbar_marks.resize(scrollbar.width(), new_height)

    def load_website(self):
        url = self.url_input.text()
        if url:
            self.web_view.setUrl(QUrl(url))
        print(f"Loading website: {url}")

    def toggle_search_bar(self):
        """Toggle the visibility of the search bar."""
        is_visible = self.search_input_html.isVisible()
        self.search_input_html.setVisible(not is_visible)
        if not is_visible:
            self.search_input_html.setFocus()  # Focus on the search bar when shown
        else:
            # Если поле поиска скрывается, сбросить подсветку
            self.html_view.setExtraSelections([])  # Убрать все подсветки
            self.search_results = []  # Очистить список результатов
            self.current_search_index = -1  # Сбросить текущий индекс
            self.scrollbar_marks.set_marks([])  # Очистить метки на скроллбаре

    def search_in_html_view(self):
        """Search for text in the HTML view."""
        search_query = self.search_input_html.text()
        if search_query:
            # Сброс предыдущих выделений
            self.html_view.setExtraSelections([])

            # Установить курсор в начало текста
            cursor = self.html_view.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.html_view.setTextCursor(cursor)  # Установить курсор в начало текста

            # Найти все вхождения
            self.search_results = []  # Сброс списка результатов
            extra_selections = []

            while self.html_view.find(search_query):
                # Сохранить курсор текущего вхождения
                self.search_results.append(self.html_view.textCursor())      

                # Настройка подсветки
                extra_selection = QTextEdit.ExtraSelection()
                extra_selection.cursor = self.html_view.textCursor() # Получить текущий курсор
                extra_selection.format.setBackground(QColor(255, 255, 0, 128))  # Полупрозрачный желтый
                extra_selections.append(extra_selection)

            # Установить все подсветки
            self.html_view.setExtraSelections(extra_selections)

            if not self.search_results:
                print("Text not found")
            else:
                print(f"Found {len(self.search_results)} occurrences of '{search_query}'")
                self.current_search_index = 0  # Сбросить индекс на первое вхождение
                self.move_to_search_result(0)  # Переместиться на первое вхождение 
            # Обновить пометки на скроллбаре
            self.update_scrollbar_marks()    


    def move_to_search_result(self, direction):
        """Перемещение между результатами поиска."""
        if not self.search_results:
            print("No search results to navigate.")
            return

        # Обновить текущий индекс
        self.current_search_index += direction
        if self.current_search_index >= len(self.search_results):
            self.current_search_index = 0  # Циклический переход к первому вхождению
        elif self.current_search_index < 0:
            self.current_search_index = len(self.search_results) - 1  # Циклический переход к последнему вхождению
        
        # Настройка подсветки
        extra_selections = []
        for i, cursor in enumerate(self.search_results):
            extra_selection = QTextEdit.ExtraSelection()
            extra_selection.cursor = cursor
            if i == self.current_search_index:
                # Подсветка текущего вхождения (королевский синий)
                extra_selection.format.setBackground(QColor(65, 105, 225, 128))  # Полупрозрачный королевский синий
            else:
                # Подсветка остальных вхождений (желтый)
                extra_selection.format.setBackground(QColor(255, 255, 0, 128))  # Полупрозрачный желтый
            extra_selections.append(extra_selection)

        # Установить все подсветки
        self.html_view.setExtraSelections(extra_selections)

        # Установить курсор на текущий результат
        current_cursor = self.search_results[self.current_search_index]
        self.html_view.setTextCursor(current_cursor)
        self.html_view.setFocus()



        print(f"Moved to occurrence {self.current_search_index + 1} of {len(self.search_results)}")            

    def update_scrollbar_marks(self):
        """Обновить пометки на скроллбаре для найденных вхождений."""
        if not self.search_results:
            self.scrollbar_marks.set_marks([])  # Очистить пометки
            return

        # Разбить текст на строки с учетом ширины текстового поля
        document = self.html_view.document()
        block = document.begin()
        total_lines = 0  # Общее количество строк в документе
        line_map = []  # Сопоставление строк с блоками

        # Получить высоту скроллбара и высоту кнопок
        scrollbar = self.html_view.verticalScrollBar()
        scrollbar_height = scrollbar.height()
        button_height = scrollbar.style().pixelMetric(scrollbar.style().PM_ScrollBarExtent)

        # Вычислить доступную высоту для маркеров
        available_height = scrollbar_height - 2 * button_height

        while block.isValid():
            block_layout = block.layout()
            if block_layout:
                # Перебираем строки внутри блока
                for i in range(block_layout.lineCount()):
                    line = block_layout.lineAt(i)
                    line_map.append((total_lines, block, line))  # Сохраняем строку, блок и линию
                    total_lines += 1
            block = block.next()
       

        marks = []  # Список для хранения позиций меток
        line_map_dict = {  # Создаем словарь для быстрого поиска
            (mapped_block.position(), mapped_line.lineNumber()): line_index
            for line_index, mapped_block, mapped_line in line_map
        }
        # Найти строки, где есть вхождения
        for cursor in self.search_results:
            cursor_position = cursor.position()
            block = document.findBlock(cursor_position)
            block_layout = block.layout()
            if block_layout:
                for i in range(block_layout.lineCount()):
                    line = block_layout.lineAt(i)

                    # Проверяем, находится ли курсор в пределах строки
                    line_start = line.textStart()
                    line_end = line_start + line.textLength()
                    if line_start <= (cursor_position - block.position()) <= line_end:
                        # Используем словарь для быстрого поиска индекса строки
                        key = (block.position(), line.lineNumber())
                        if key in line_map_dict:
                            line_index = line_map_dict[key]
                            relative_position = line_index / total_lines
                            mark_position = int(relative_position * available_height)
                            marks.append(mark_position)
                        break
        
        self.scrollbar_marks.set_marks(marks)

    def scrape_html(self):
        # url = self.url_input.text()
        page = self.web_view.page()
        page.toHtml(lambda html: self.html_view.setPlainText(self.display_pretty_html(html)))

        # page.toHtml(lambda html: print(html))
        # page.toHtml(lambda html: self.write_to_file(html))
    def display_pretty_html(self, html):
        # Используем BeautifulSoup для форматирования HTML
        soup = BeautifulSoup(html, 'html.parser')
        pretty_html = soup.prettify()
        return pretty_html
        # self.html_view.setPlainText(pretty_html)  # Устанавливаем отформатированный HTML
        # write_to_file(pretty_html)  # Записываем в файл

    def write_to_file(self, html):
        with open("output.html", "w", encoding="utf-8") as file:
            file.write(self.display_pretty_html(html))
        print("HTML has been written to output.html")
            

    def fetch_html(self):
        url = self.url_input.text()
        if url:
            try:
                response = requests.get(url)
                response.raise_for_status()  # Проверяем наличие ошибок
                html = response.text
                self.html_view.setText(html)  # Устанавливаем HTML в текстовое поле
            except requests.exceptions.RequestException as e:
                print(f"Error fetching URL: {e}")    
    # Selenium Scrape button
    def selenium_scrape_html(self):
        url = self.url_input.text()
        if url:

            # chrome_options = Options()
            # chrome_options.add_argument("--headless")
            # chrome_service = Service()  # Adjust path to chromedriver if necessary
            driver = set_driver()

            try:
                driver.get(url)
                html_source = driver.page_source
                pretty_html = self.display_pretty_html(html_source)
                self.html_view.setText(pretty_html)  # Устанавливаем отформатированный HTML
            finally:
                driver.quit()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebScrapingInterface()
    window.show()
    sys.exit(app.exec_())