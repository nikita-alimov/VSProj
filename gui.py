from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QPushButton, QLineEdit, QSizePolicy, QShortcut, QLineEdit, QComboBox
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
        layout4 = QHBoxLayout()
        layout5 = QHBoxLayout()
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

        # Dropdown menus for tags and attributes
        self.tags_dropdown = QComboBox(self)
        self.tags_dropdown.setPlaceholderText("Select a tag")
        layout4.addWidget(self.tags_dropdown)

        self.attributes_dropdown = QComboBox(self)
        self.attributes_dropdown.setPlaceholderText("Select an attribute")
        layout5.addWidget(self.attributes_dropdown)
        self.tags_dropdown.setFixedWidth(self.attributes_dropdown.sizeHint().width())

        # Поля для отображения текущих фильтров
        self.filtered_tags_view = QLineEdit(self)
        self.filtered_tags_view.setReadOnly(True)
        layout4.addWidget(self.filtered_tags_view)

        self.filtered_attributes_view = QLineEdit(self)
        self.filtered_attributes_view.setReadOnly(True)
        layout5.addWidget(self.filtered_attributes_view)

        # Button to clear the last entry in the filtered tags view
        self.clear_tags_button = QPushButton("Удалить последний тег", self)
        self.clear_tags_button.clicked.connect(self.remove_last_tag)
        layout4.addWidget(self.clear_tags_button)

        # Button to clear the last entry in the filtered attributes view
        self.clear_attributes_button = QPushButton("Удалить последний аттрибут", self)
        self.clear_attributes_button.clicked.connect(self.remove_last_attribute)
        layout5.addWidget(self.clear_attributes_button)
        self.clear_tags_button.setFixedWidth(self.clear_attributes_button.sizeHint().width())


        # Set layout for the main window
        layout3.addLayout(layout)
        layout3.addLayout(layout2)
        layoutFinal.addLayout(layout3)
        layoutFinal.addLayout(layout4)
        layoutFinal.addLayout(layout5)
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

        self.tags_dropdown.activated.connect(self.filter_by_tag)
        self.attributes_dropdown.activated.connect(self.filter_by_attribute)

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

        # Initialize dropdowns
        # self.tags_dropdown.addItem("Loading...")
        # self.attributes_dropdown.addItem("Loading...")
        
    def resizeEvent(self, event):
        """Обновить размеры scrollbar_marks при изменении размеров окна."""
        super().resizeEvent(event)
        self.resize_timer.start(200) # Перезапустить таймер (200 мс задержка)

    def on_resize_finished(self):
        """Обработчик завершения изменения размера окна."""
        self.update_scrollbar_marks_size()
        self.update_scrollbar_marks()  # Обновить пометки на скроллбаре

    def remove_last_tag(self):
        """Удалить последний тег из QLineEdit и обновить фильтрацию."""
        tags = self.filtered_tags_view.text().strip().split(";")
        if tags:
            tags.pop()  # Удалить последний тег
            self.filtered_tags_view.setText(";".join(tags))  # Обновить QLineEdit
            self.update_filter_from_line_edit()  # Обновить фильтрацию

    def remove_last_attribute(self):
        """Удалить последний атрибут из QLineEdit и обновить фильтрацию."""
        attributes = self.filtered_attributes_view.text().strip().split(";")
        if attributes:
            attributes.pop()  # Удалить последний атрибут
            self.filtered_attributes_view.setText(";".join(attributes))  # Обновить QLineEdit
            self.update_filter_from_line_edit()  # Обновить фильтрацию

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
        page.toHtml(lambda html: self.update_dropdowns(self.display_pretty_html(html)))  # Обновить выпадающие меню
        self.filtered_tags_view.clear()  # Очистить QLineEdit для тегов
        self.filtered_attributes_view.clear()  # Очистить QLineEdit для атрибутов
        # page.toHtml(lambda html: self.update_filter_from_line_edit())  # Обновить фильтрацию

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
                pretty_html = self.display_pretty_html(html)
                self.html_view.setPlainText(pretty_html)  # Устанавливаем HTML в текстовое поле

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
                self.html_view.setPlainText(pretty_html)  # Устанавливаем отформатированный HTML
            finally:
                driver.quit()

    def update_dropdowns(self, html):
        """Обновить выпадающие меню тегов и атрибутов."""
        soup = BeautifulSoup(html, 'html.parser')
        # Извлечь все уникальные теги
        tags = {tag.name for tag in soup.find_all()}
        self.tags_dropdown.clear()
        self.tags_dropdown.addItems(sorted(tags))

        # Извлечь все уникальные атрибуты с их значениями
        attributes_with_values = set()
        for tag in soup.find_all():
            for attr, value in tag.attrs.items():
                # Добавить атрибуты в формате "атрибут=значение"
                if isinstance(value, list):  # Если значение атрибута — список (например, class)
                    attributes_with_values.add(f"{attr}={' '.join(value)}")
                else:
                    attributes_with_values.add(f"{attr}={value}")

        self.attributes_dropdown.clear()
        self.attributes_dropdown.addItems(sorted(attributes_with_values))

    def filter_by_tag(self):
        """Фильтровать элементы HTML по выбранному тегу."""
        # Обновить текстовое поле с текущими тегами
        current_text = self.filtered_tags_view.text()
        if self.tags_dropdown.currentText() in current_text.split(";"):
            return
        
        soup = BeautifulSoup(self.html_view.toPlainText(), 'html.parser')  # Использовать полученный HTML

        # Получить текущий выбранный тег из выпадающего меню
        selected_tag = self.tags_dropdown.currentText()
        if selected_tag:
            filtered_elements = soup.find_all(selected_tag)
            soup = BeautifulSoup("\n".join(str(element) for element in filtered_elements), 'html.parser')
            self.html_view.setPlainText(self.display_pretty_html(str(soup)))
            if current_text:
                self.filtered_tags_view.setText(f"{current_text};{selected_tag}")
            else:
                self.filtered_tags_view.setText(selected_tag)
            self.update_dropdowns(self.html_view.toPlainText())  # Обновить выпадающие меню с отфильтрованным HTML

            

    def filter_by_attribute(self):
        """Фильтровать элементы HTML по выбранному атрибуту."""
        # Обновить текстовое поле с текущими атрибутами      
        current_text = self.filtered_attributes_view.text()
        selected_attribute_value = self.attributes_dropdown.currentText()
        if selected_attribute_value in current_text.split(";"):
            return
        
        soup = BeautifulSoup(self.html_view.toPlainText(), 'html.parser') 

        # Разделить выбранное значение на атрибут и значение
        if "=" in selected_attribute_value:
            attr, value = selected_attribute_value.split("=", 1)
        else:
            attr, value = selected_attribute_value, None

        # Фильтровать элементы
        filtered_elements = []
        for tag in soup.find_all():
            if value is not None:  # Если указано значение атрибута
                attr_value = tag.attrs.get(attr)
                if isinstance(attr_value, list):  # Если значение атрибута — список (например, class)
                    if all(val.strip() in attr_value for val in value.split()):
                        filtered_elements.append(tag)      
                elif attr_value == value:  # Если значение атрибута — строка
                    filtered_elements.append(tag)
            else:  # Если фильтруем только по наличию атрибута
                if attr in tag.attrs:
                    filtered_elements.append(tag)
        soup = BeautifulSoup("\n".join(str(element) for element in filtered_elements), 'html.parser')
        self.html_view.setPlainText(self.display_pretty_html(str(soup)))
        self.update_dropdowns(self.html_view.toPlainText())
        if current_text:
            self.filtered_attributes_view.setText(f"{current_text};{selected_attribute_value}")
        else:
            self.filtered_attributes_view.setText(selected_attribute_value)


    def apply_filters(self, html, tags, attributes):
        """Применить фильтры к HTML-коду."""
        soup = BeautifulSoup(html, 'html.parser')  # Использовать полученный HTML

        # Фильтровать по тегам
        if tags:
            filtered_elements = []
            for tag in tags:
                filtered_elements = soup.find_all(tag)
                soup = BeautifulSoup("\n".join(str(element) for element in filtered_elements), 'html.parser')
            

        # Фильтровать по атрибутам
        if attributes:
            for attribute in attributes:
                filtered_elements = []
                if "=" in attribute:
                    attr, value = attribute.split("=", 1)   
                else:
                    attr, value = attribute, None            
                for tag in soup.find_all():
                    if value is not None:
                        attr_value = tag.attrs.get(attr)
                        if isinstance(attr_value, list):  # Если значение атрибута — список (например, class)
                            # Проверяем, содержится ли любое слово из value в списке
                            if all(val.strip() in attr_value for val in value.split()):
                                filtered_elements.append(tag)
                                
                        elif attr_value == value:  # Если значение атрибута — строка
                            # Проверяем, совпадает ли строка или содержит искомое значение
                                filtered_elements.append(tag) 
                    else:  # Если фильтруем только по наличию атрибута
                        if attr in tag.attrs:
                            filtered_elements.append(tag)                                    
                soup = BeautifulSoup("\n".join(str(element) for element in filtered_elements), 'html.parser')

        # Обновить отображение в html_view
        self.html_view.setPlainText(self.display_pretty_html(str(soup)))
        self.update_dropdowns(self.html_view.toPlainText())  # Обновить выпадающие меню с отфильтрованным HTML

    def update_filter_from_line_edit(self):
        """Обновить фильтрацию на основе содержимого QLineEdit."""
        # Получить текущие теги и атрибуты из QLineEdit
        tags = [tag.strip() for tag in self.filtered_tags_view.text().strip().split(";") if tag.strip()]
        attributes = [attr.strip() for attr in self.filtered_attributes_view.text().strip().split(";") if attr.strip()]

        # Использовать исходный HTML
        page = self.web_view.page()
        page.toHtml(lambda html: self.apply_filters(html, tags, attributes))  # Передать HTML в обработчик
        

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebScrapingInterface()
    window.show()
    sys.exit(app.exec_())