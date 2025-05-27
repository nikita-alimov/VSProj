import asyncio
from PyQt5.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox, QMainWindow, QVBoxLayout, QHBoxLayout, QAction, QWidget, QTextEdit, QPushButton, QLineEdit, QSizePolicy, QShortcut, QLineEdit, QComboBox
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QTimer
from PyQt5.QtGui import QKeySequence, QTextCursor, QColor
from bs4 import BeautifulSoup
import sys
from qasync import QEventLoop
import requests
import pandas as pd
from selenium_test import set_driver  # Импортируем функцию для установки драйвера Selenium
from ScrollbarMarksWidget import ScrollbarMarks  # Импортируем класс для пометок на скроллбаре
from DataFrameViewer import DataFrameViewer # Импортируем класс для отображения DataFrame
from FieldInputDialog import SliceInputDialog
from ParseLinksDialog import ParseLinksDialog  # Импортируем класс для отображения ссылок




class WebScrapingInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Web Scraping Helper")
        self.setGeometry(100, 100, 1200, 800)

        # Применить стили
        self.apply_styles()

        # Main layout
        layout = QVBoxLayout()
        layout2 = QVBoxLayout()
        layout3 = QHBoxLayout()
        layout4 = QHBoxLayout()
        layout5 = QHBoxLayout()
        layout6 = QVBoxLayout()
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
        self.web_view.loadFinished.connect(lambda _: self.scrape_button.click())
        self.web_view.urlChanged.connect(self.update_url_input)
        layout.addWidget(self.web_view)

        # # Load button
        # self.load_button = QPushButton("Load Website", self)
        # self.load_button.clicked.connect(self.load_website)
        # layout.addWidget(self.load_button)

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

        # Добавить кнопку для извлечения данных
        self.extract_data_button = QPushButton("Извлечь данные", self)
        self.extract_data_button.clicked.connect(self.extract_data)
        layout2.addWidget(self.extract_data_button)

        self.parse_links_button = QPushButton("Парсить ссылки", self)
        self.parse_links_button.clicked.connect(self.parse_links)
        layout2.addWidget(self.parse_links_button)

        self.fetch_button = QPushButton("Fetch HTML (Direct)", self)
        self.fetch_button.clicked.connect(self.fetch_html)
        self.fetch_button.hide()
        layout2.addWidget(self.fetch_button)

        # Selenium Scrape button
        self.selenium_scrape_button = QPushButton("Scrape HTML (Selenium)", self)
        self.selenium_scrape_button.clicked.connect(self.selenium_scrape_html)
        self.selenium_scrape_button.hide()
        layout2.addWidget(self.selenium_scrape_button)

        # Dropdown menus for tags and attributes
        self.tags_dropdown = QComboBox(self)
        self.tags_dropdown.setPlaceholderText("Select a tag")
        layout4.addWidget(self.tags_dropdown)

        self.attributes_dropdown = QComboBox(self)
        self.attributes_dropdown.setPlaceholderText("Select an attribute with value")
        layout6.addWidget(self.attributes_dropdown)
        self.tags_dropdown.setFixedWidth(self.attributes_dropdown.sizeHint().width())

        self.attributes_dropdown_without_value = QComboBox(self)
        self.attributes_dropdown_without_value.setPlaceholderText("Select an attribute")
        layout6.addWidget(self.attributes_dropdown_without_value)
        self.attributes_dropdown_without_value.setFixedWidth(self.attributes_dropdown.sizeHint().width())
        layout5.addLayout(layout6)

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

        # Добавляем главное меню
        self.create_menu()

        # Html view search functionality
        self.search_results = []  # Список всех найденных вхождений
        self.current_search_index = -1  # Текущий индекс вхождения

        self.next_result_shortcut = QShortcut(QKeySequence("F3"), self)
        self.next_result_shortcut.activated.connect(lambda: self.move_to_search_result(1))  # Следующее вхождение

        self.prev_result_shortcut = QShortcut(QKeySequence("Shift+F3"), self)
        self.prev_result_shortcut.activated.connect(lambda: self.move_to_search_result(-1))  # Предыдущее вхождение

        self.tags_dropdown.activated.connect(self.filter_by_tag)
        self.attributes_dropdown.activated.connect(self.filter_by_attribute)
        self.attributes_dropdown_without_value.activated.connect(self.filter_by_attribute)

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


    def create_menu(self):
        """Создать главное меню."""
        menu_bar = self.menuBar()

        # Добавляем меню "Tools"
        tools_menu = menu_bar.addMenu("Tools")

        # Добавляем пункт меню "Show DataFrame"
        show_df_action = QAction("Show DataFrame", self)
        show_df_action.triggered.connect(self.show_dataframe)
        tools_menu.addAction(show_df_action)

    def parse_links(self):
        """Извлечь ссылки с сайта и сгруппировать их по парам тег-атрибут."""
        html = self.html_view.toPlainText()
        soup = BeautifulSoup(html, 'html.parser')

        # Словарь для хранения ссылок, сгруппированных по тегам и атрибутам
        links_by_tag_attribute = {}

        # Перебираем все теги с атрибутами, содержащими ссылки
        base_url = self.url_input.text()  # Получаем базовый URL из строки ввода

        for tag in soup.find_all():
            for attr, value in tag.attrs.items():
                if isinstance(value, str):
                    # Проверяем, является ли ссылка абсолютной или относительной
                    if value.startswith("http://") or value.startswith("https://"):
                        # Абсолютная ссылка
                        key = f"{tag.name}[{attr}]"
                        if key not in links_by_tag_attribute:
                            links_by_tag_attribute[key] = []
                        links_by_tag_attribute[key].append(value)
                    elif value.startswith("/"):
                        # Относительная ссылка
                        absolute_url = QUrl(base_url).resolved(QUrl(value)).toString()
                        key = f"{tag.name}[{attr}]"
                        if key not in links_by_tag_attribute:
                            links_by_tag_attribute[key] = []
                        links_by_tag_attribute[key].append(absolute_url)

        # # Выводим результат в консоль (или обрабатываем дальше)
        # for key, links in links_by_tag_attribute.items():
        #     print(f"{key}:")
        #     for link in links:
        #         print(f"  {link}")
            # Открыть диалог для отображения ссылок
        dialog = ParseLinksDialog(links_by_tag_attribute, self)
        dialog.exec_()

        # return links_by_tag_attribute
    
    def extract_data(self, data_list=None, field_name=None):
        """Извлечь данные по текущим фильтрам и сохранить в DataFrame."""
        # Получить текущий HTML из html_view
        if hasattr(self, 'dataframe') and self.dataframe.empty:
            del self.dataframe
        all_data = []
        if data_list:
            # Используем готовый список
            all_data = data_list
            start, end = 0, len(all_data) - 1
        else:
            html = self.html_view.toPlainText()
            dialog = SliceInputDialog(html, self)
            if dialog.exec_() == QDialog.Accepted:
                all_data, start, end, field_name = dialog.get_values()
            else:
                all_data = []

        # soup = BeautifulSoup(html, 'html.parser')



        # Извлечь текст всех элементов
        # all_data = [element.get_text(strip=True) for element in soup.find_all()]
        # Показать диалог для ввода параметров
        
        # dialog.attribute_input.clear()
        # dialog.attribute_input.addItem("")
        # dialog.attribute_input.addItems([self.attributes_dropdown_without_value.itemText(i) for i in range(self.attributes_dropdown_without_value.count())])
        # dialog.tag_input.clear()
        # dialog.tag_input.addItem("")
        # dialog.tag_input.addItems([self.tags_dropdown.itemText(i) for i in range(self.tags_dropdown.count())])

            # Check if a specific attribute is selected in FieldInputDialog
            
            # Check if the user wants to extract text between tags
            # if dialog.extract_text_radio.isChecked():
            #     # Extract text between the selected tags
            #     if selected_tag:
            #         if selected_attribute:
            #             all_data = [
            #                 element.get_text(strip=True)
            #                 for element in soup.find_all(selected_tag)
            #                 if element.has_attr(selected_attribute)
            #             ]
            #         else:
            #             all_data = [element.get_text(strip=True) for element in soup.find_all(selected_tag)]
            #     elif selected_attribute:
            #         all_data = [
            #             element.get_text(strip=True)
            #             for element in soup.find_all()
            #             if element.has_attr(selected_attribute)
            #         ]

            # else:
            #     if not selected_attribute:
            #         QMessageBox.warning(self, "Ошибка", "Выберите атрибут для извлечения.")
            #         return
            #     if not selected_tag:
            #         # Extract the values of the selected attribute
            #         all_data = [element.get(selected_attribute, "").strip() for element in soup.find_all()]
            #     else:
            #         all_data = [element.get(selected_attribute, "").strip() for element in soup.find_all(selected_tag)]    

            # Проверить корректность диапазона
            # if start > end:
            #     QMessageBox.warning(self, "Ошибка", "Начальная строка не может быть больше конечной.")
            #     return

            # # Проверить, введено ли имя поля
            # if not field_name.strip():
            #     QMessageBox.warning(self, "Ошибка", "Название поля не может быть пустым.")
            #     return

        # # Запросить у пользователя диапазон строк
        # start, ok_start = QInputDialog.getInt(self, "Введите начало среза", "Начальная строка (0-based):", 0, 0, len(all_data) - 1)
        # if not ok_start:
        #     return  # Пользователь отменил ввод

        # end, ok_end = QInputDialog.getInt(self, "Введите конец среза", "Конечная строка (0-based, включительно):", start, start, len(all_data) - 1)
        # if not ok_end:
        #     return  # Пользователь отменил ввод

        # # Убедиться, что диапазон корректен
        # if start > end:
        #     QMessageBox.warning(self, "Ошибка", "Начальная строка не может быть больше конечной.")
        #     return
        if all_data:
        # Взять срез данных
            extracted_data = all_data[start:end + 1]

            # Запросить у пользователя название поля
            # field_name, ok = QInputDialog.getText(self, "Введите название поля", "Название поля для сохранения данных:")
            # if not ok or not field_name.strip():
            #     return  # Пользователь отменил ввод

            field_name = field_name.strip()

            # Проверить, существует ли поле в DataFrame
            if hasattr(self, 'dataframe'):
                if field_name in self.dataframe.columns:
                    # Если поле существует, предложить варианты действий
                    actions = ["Перезаписать данные", "Дополнить данные"]
                    action, ok = QInputDialog.getItem(
                        self,
                        "Поле уже существует",
                        f"Поле '{field_name}' уже существует. Выберите действие:",
                        actions,
                        editable=False
                    )
                    if action == "Перезаписать данные":
                        # Проверить соответствие размеров
                        if len(self.dataframe.columns) == 1:
                            del self.dataframe
                            self.dataframe = pd.DataFrame({field_name: extracted_data})

                        elif len(self.dataframe) != len(extracted_data):
                            if len(extracted_data) > len(self.dataframe):
                                # Спросить у пользователя, хочет ли он обрезать данные или дополнить другие колонки NaN
                                actions = ["Обрезать данные", "Дополнить другие колонки значениями NaN"]
                                action, ok = QInputDialog.getItem(
                                    self,
                                    "Обрезать или дополнить данные?",
                                    "Количество строк в новых данных больше, чем в DataFrame. "
                                    "Выберите действие:",
                                    actions,
                                    editable=False
                                )
                                if not ok:
                                    return  # Пользователь отменил ввод

                                if action == "Обрезать данные":
                                    # Обрезать extracted_data до размера DataFrame
                                    extracted_data = extracted_data[:len(self.dataframe)]
                                elif action == "Дополнить другие колонки значениями NaN":
                                    # Извлечь все старые колонки и дополнить их до новой размерности
                                    old_columns = {column: self.dataframe[column].tolist() for column in self.dataframe.columns}
                                    for column in old_columns:
                                        old_columns[column].extend([float('nan')] * (len(extracted_data) - len(self.dataframe)))

                                    # Добавить новую колонку с извлеченными данными
                                    old_columns[field_name] = extracted_data

                                    # Удалить старый DataFrame и создать новый с дополненными колонками
                                    del self.dataframe
                                    self.dataframe = pd.DataFrame(old_columns)
                            else:
                                # Спросить у пользователя, хочет ли он дополнить данные
                                reply = QMessageBox.question(
                                    self,
                                    "Дополнить данные?",
                                    "Количество строк в новых данных меньше, чем в DataFrame. "
                                    "Хотите дополнить данные значениями NaN?",
                                    QMessageBox.Yes | QMessageBox.No,
                                    QMessageBox.No
                                )
                                if reply == QMessageBox.Yes:
                                    # Дополнить extracted_data значениями NaN до размера DataFrame
                                    extracted_data.extend([float('nan')] * (len(self.dataframe) - len(extracted_data)))
                                else:
                                    return
                                # Перезаписать данные
                            self.dataframe[field_name] = extracted_data

                    elif action == "Дополнить данные":
                        if len(self.dataframe.columns) == 1:
                            current_data = self.dataframe[field_name].tolist()
                            new_data = current_data + extracted_data
                            del self.dataframe
                            self.dataframe = pd.DataFrame({field_name: new_data})
                        else:    
                            # Удалить значения NaN из дополняемой колонки
                            existing_data = self.dataframe[field_name].dropna().tolist()
                            # Попытаться дополнить колонку новыми данными
                            updated_column = existing_data + extracted_data    
                            
                            # Проверить соответствие размеров
                            if len(updated_column) != len(self.dataframe):
                                if len(updated_column) > len(self.dataframe):
                                    # Спросить у пользователя, хочет ли он обрезать данные или дополнить другие колонки NaN
                                    actions = ["Обрезать данные", "Дополнить другие колонки значениями NaN"]
                                    action, ok = QInputDialog.getItem(
                                        self,
                                        "Обрезать или дополнить данные?",
                                        "Количество строк в новых данных больше, чем в DataFrame. "
                                        "Выберите действие:",
                                        actions,
                                        editable=False
                                    )
                                    if not ok:
                                        return  # Пользователь отменил ввод

                                    if action == "Обрезать данные":
                                        # Обрезать updated_column до размера DataFrame
                                        updated_column = updated_column[:len(self.dataframe)]
                                    elif action == "Дополнить другие колонки значениями NaN":
                                        # Извлечь все старые колонки и дополнить их до новой размерности
                                        old_columns = {column: self.dataframe[column].tolist() for column in self.dataframe.columns}
                                        for column in old_columns:
                                            old_columns[column].extend([float('nan')] * (len(extracted_data) - len(self.dataframe)))

                                        # Добавить новую колонку с извлеченными данными
                                        old_columns[field_name] = extracted_data

                                        # Удалить старый DataFrame и создать новый с дополненными колонками
                                        del self.dataframe
                                        self.dataframe = pd.DataFrame(old_columns)
                                else:
                                    # Спросить у пользователя, хочет ли он дополнить данные
                                    reply = QMessageBox.question(
                                        self,
                                        "Дополнить данные?",
                                        "Количество строк в новых данных меньше, чем в DataFrame. "
                                        "Хотите дополнить данные значениями NaN?",
                                        QMessageBox.Yes | QMessageBox.No,
                                        QMessageBox.No
                                    )
                                    if reply == QMessageBox.Yes:
                                        # Дополнить updated_column значениями NaN до размера DataFrame
                                        updated_column.extend([float('nan')] * (len(self.dataframe) - len(updated_column)))
                                    else:
                                        return

                            # Установить обновленную колонку в DataFrame
                            self.dataframe[field_name] = updated_column
                else:
                    # Проверить соответствие размеров для нового поля
                    if len(self.dataframe) != len(extracted_data):
                        if len(extracted_data) > len(self.dataframe):
                            # Спросить у пользователя, хочет ли он обрезать данные или дополнить другие колонки NaN
                            actions = ["Обрезать данные", "Дополнить другие колонки значениями NaN"]
                            action, ok = QInputDialog.getItem(
                                self,
                                "Обрезать или дополнить данные?",
                                "Количество строк в новых данных больше, чем в DataFrame. "
                                "Выберите действие:",
                                actions,
                                editable=False
                            )
                            if not ok:
                                return  # Пользователь отменил ввод

                            if action == "Обрезать данные":
                                # Обрезать extracted_data до размера DataFrame
                                extracted_data = extracted_data[:len(self.dataframe)]
                            elif action == "Дополнить другие колонки значениями NaN":
                                    # Извлечь все старые колонки и дополнить их до новой размерности
                                    old_columns = {column: self.dataframe[column].tolist() for column in self.dataframe.columns}
                                    for column in old_columns:
                                        old_columns[column].extend([float('nan')] * (len(extracted_data) - len(self.dataframe)))

                                    # Добавить новую колонку с извлеченными данными
                                    old_columns[field_name] = extracted_data

                                    # Удалить старый DataFrame и создать новый с дополненными колонками
                                    del self.dataframe
                                    self.dataframe = pd.DataFrame(old_columns)
                        else:
                            # Спросить у пользователя, хочет ли он дополнить данные
                            reply = QMessageBox.question(
                                self,
                                "Дополнить данные?",
                                "Количество строк в новых данных меньше, чем в DataFrame. "
                                "Хотите дополнить данные значениями NaN?",
                                QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No
                            )
                            if reply == QMessageBox.Yes:
                                # Дополнить extracted_data значениями NaN до размера DataFrame
                                extracted_data.extend([float('nan')] * (len(self.dataframe) - len(extracted_data)))
                            else:
                                return
                    self.dataframe[field_name] = extracted_data
            else:
                # Создать новый DataFrame, если он не существует
                self.dataframe = pd.DataFrame({field_name: extracted_data})

            # Установить обновленный DataFrame в DataFrameViewer
            self.set_dataframe(self.dataframe)

    def set_dataframe (self, dataframe):
        if hasattr(self, 'dataframe_viewer'):
            # If the DataFrameViewer already exists, update its DataFrame
            self.dataframe_viewer.update_dataframe(dataframe)
        else:
            # Otherwise, create a new DataFrameViewer
            self.dataframe_viewer = DataFrameViewer(dataframe)

    def show_dataframe(self):
        """Открыть новое окно для отображения DataFrame."""
        # self.dataframe_viewer = DataFrameViewer(dataframe)
        if not hasattr(self, 'dataframe_viewer'):
            self.dataframe_viewer = DataFrameViewer(pd.DataFrame())
        # if hasattr(self, 'dataframe_viewer') and self.dataframe_viewer.isVisible():
        #     # Закрыть существующее окно перед обновлением
        #     self.dataframe_viewer.close()

        self.dataframe_viewer.show()

    def apply_styles(self):
        """Применить стили к интерфейсу."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }

            QLineEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px;
            }

            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }

            QPushButton:hover {
                background-color: #005f9e;
            }

            QPushButton:pressed {
                background-color: #004a7c;
            }

            QTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px;
            }

            QComboBox {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px;
            }

            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #d4d4d4;
                selection-background-color: #007acc;
            }

            QMenuBar {
                background-color: #2d2d2d;
                color: #d4d4d4;
            }

            QMenuBar::item {
                background-color: #2d2d2d;
                color: #d4d4d4;
            }

            QMenuBar::item:selected {
                background-color: #007acc;
            }

            QMenu {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }

            QMenu::item:selected {
                background-color: #007acc;
            }

            QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 14px;  
            margin: 0px 3px 0px 3px;
            border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #5a5a5a;  
                min-height: 14px;
                border-radius: 7px;  
                margin-top: 14px;  /* Отступ сверху для верхней кнопки */
                margin-bottom: 14px;  /* Отступ снизу для нижней кнопки */
            }

            QScrollBar::handle:vertical:hover {
                background-color: #787878;  
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background-color: #3c3c3c;  /* Темный фон для кнопок */
                height: 14px;  /* Высота кнопок */
                subcontrol-origin: margin;
                border-radius: 1px;  /* Закругленные края */
            }

            QScrollBar::add-line:vertical {
                subcontrol-position: bottom;  /* Позиция кнопки вниз */
            }

            QScrollBar::sub-line:vertical {
                subcontrol-position: top;  /* Позиция кнопки вверх */
            }

            QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
                background-color: #5a5a5a;  /* Более светлый серый при наведении */
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;  /* Убираем фон между ползунком и краями */
            }
        """)

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
        attributes_without_value = set()
        for tag in soup.find_all():
            for attr, value in tag.attrs.items():
                # Добавить атрибуты в формате "атрибут=значение"
                if isinstance(value, list):  # Если значение атрибута — список (например, class)
                    attributes_with_values.add(f"{attr}={' '.join(value)}")
                else:
                    attributes_with_values.add(f"{attr}={value}")

            for attr in tag.attrs.keys():
                attributes_without_value.add(attr)  # Добавить атрибуты без значений

        self.attributes_dropdown.clear()
        self.attributes_dropdown.addItems(sorted(attributes_with_values))
        self.attributes_dropdown_without_value.clear()
        self.attributes_dropdown_without_value.addItems(sorted(attributes_without_value))
        self.scrollbar_marks.set_marks([])  # Очистить метки на скроллбаре

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
            # Найти только верхнеуровневые элементы
            filtered_elements = []
            for element in soup.find_all(selected_tag):
                # Проверяем, является ли элемент вложенным
                if not element.find_parent(selected_tag):
                    filtered_elements.append(element)

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
        selected_attribute_value = self.attributes_dropdown.currentText() or self.attributes_dropdown_without_value.currentText()
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
            for tag in tags:
                filtered_elements = []
                for element in soup.find_all(tag):
                    # Проверяем, является ли элемент вложенным
                    if not element.find_parent(tag):
                        filtered_elements.append(element)    
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
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = WebScrapingInterface()
    window.show()
    with loop:
        # Запустить основной цикл событий
        loop.run_forever()
    # sys.exit(app.exec_())