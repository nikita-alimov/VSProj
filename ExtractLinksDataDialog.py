from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTextEdit,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar, QApplication, QSpinBox, QRadioButton,
    QInputDialog, QSizePolicy, QCheckBox
)
from PyQt5.QtCore import QTimer
import requests
from bs4 import BeautifulSoup
from PyQt5.QtGui import QTextCursor
import aiohttp
import asyncio
from playwright.async_api import async_playwright
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options

class ExtractLinksDataDialog(QDialog):
    def __init__(self, links, parent=None, main_window=None):
        super().__init__(parent)
        self.setWindowTitle("Извлечение данных по ссылкам")
        self.setMinimumSize(800, 600)
        self.links = links
        self.current_index = 0
        self.results = []
        self.main_window = main_window

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)  # Таймер срабатывает только один раз
        self.timer.timeout.connect(self.update_result_combo_by_filter) 

        layout = QVBoxLayout(self)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("←", self)
        self.prev_btn.clicked.connect(self.prev_link)
        self.next_btn = QPushButton("→", self)
        self.next_btn.clicked.connect(self.next_link)
        self.link_label = QLabel("", self)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.link_label)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)

        self.html_view = QTextEdit(self)
        self.html_view.setReadOnly(True)
        layout.addWidget(self.html_view)

        filter_layout = QHBoxLayout()
        self.tag_combo = QComboBox(self)
        self.tag_combo.setEditable(True)
        self.tag_combo.setInsertPolicy(QComboBox.NoInsert)
        self.tag_combo.setPlaceholderText("Тег (например, div)")
        self.tag_combo.currentTextChanged.connect(self.update_attr_combo)
        self.tag_combo.currentTextChanged.connect(self.set_delay)

        self.attr_combo = QComboBox(self)
        self.attr_combo.setEditable(True)
        self.attr_combo.setInsertPolicy(QComboBox.NoInsert)
        self.attr_combo.setPlaceholderText("Аттрибут (например, class)")
        self.attr_combo.currentTextChanged.connect(self.set_delay)

        self.value_edit = QLineEdit(self)
        self.value_edit.setPlaceholderText("Фильтр по значению аттрибута (опционально)")
        self.value_edit.textChanged.connect(self.set_delay)

        filter_layout.addWidget(self.tag_combo)
        filter_layout.addWidget(self.attr_combo)
        filter_layout.addWidget(self.value_edit)
        layout.addLayout(filter_layout)

        self.check_box_dynamic = QCheckBox("Парсинг динамического контента", self)
        self.check_box_dynamic.toggled.connect(self.update_link_display_dynamic)


        # Комбобокс для результатов
        result_layout = QHBoxLayout()
        self.result_combo = QComboBox(self)
        self.result_combo.setEditable(False)
        self.result_combo.setPlaceholderText("Результаты извлечения")
        self.result_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.result_lable = QLabel("Результаты: ()", self)
        self.result_combo.activated.connect(self.on_result_combo_activated)
        result_layout.addWidget(self.result_lable)
        result_layout.addWidget(self.result_combo)
        result_layout.addWidget(self.check_box_dynamic)
        
        # --- Срезы и режим извлечения ---
        slice_layout = QHBoxLayout()
        self.slice_start_spin = QSpinBox(self)
        self.slice_start_spin.setMinimum(0)
        self.slice_start_spin.setMaximum(99999)
        self.slice_start_spin.setPrefix("Срез от: ")
        self.slice_start_spin.valueChanged.connect(self.set_delay)

        self.slice_end_spin = QSpinBox(self)
        self.slice_end_spin.setMinimum(0)
        self.slice_end_spin.setMaximum(99999)
        self.slice_end_spin.setPrefix("до: ")
        self.slice_end_spin.valueChanged.connect(self.set_delay)

        slice_layout.addWidget(self.slice_start_spin)
        slice_layout.addWidget(self.slice_end_spin)

        # Радио-кнопки для выбора типа извлекаемого контента
        self.content_radio_layout = QHBoxLayout()
        self.radio_text = QRadioButton("Текст между тегами", self)
        self.radio_attr = QRadioButton("Значение аттрибута", self)
        self.radio_text.setChecked(True)
        self.content_radio_layout.addWidget(self.radio_text)
        self.radio_text.toggled.connect(self.set_delay)
        self.radio_attr.toggled.connect(self.set_delay)
        self.content_radio_layout.addWidget(self.radio_attr)
        slice_layout.addLayout(self.content_radio_layout)
        layout.addLayout(slice_layout)
        layout.addLayout(result_layout)
        
        btns_layout = QHBoxLayout()
        self.extract_current_btn = QPushButton("Извлечь из текущей", self)
        self.extract_current_btn.clicked.connect(self.extract_current)
        self.extract_all_btn = QPushButton("Извлечь из всех", self)
        self.extract_all_btn.clicked.connect(self.extract_all)
        self.show_results_btn = QPushButton("Показать результат", self)
        self.show_results_btn.clicked.connect(self.show_results)
        self.add_to_dataset_btn = QPushButton("Добавить к датасету", self)
        self.add_to_dataset_btn.clicked.connect(self.add_to_dataset)
        btns_layout.addWidget(self.extract_current_btn)
        btns_layout.addWidget(self.extract_all_btn)
        btns_layout.addWidget(self.show_results_btn)
        btns_layout.addWidget(self.add_to_dataset_btn)
        layout.addLayout(btns_layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        # --- Кнопки управления процессом извлечения ---
        self.stop_btn = QPushButton("Стоп", self)
        self.stop_btn.setVisible(False)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        self.resume_btn = QPushButton("Возобновить", self)
        self.resume_btn.setVisible(False)
        self.resume_btn.clicked.connect(self.on_resume_clicked)
        self.cancel_btn = QPushButton("Остановить", self)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.on_cancel_clicked)
        btns_layout.addWidget(self.stop_btn)
        btns_layout.addWidget(self.resume_btn)
        btns_layout.addWidget(self.cancel_btn)

        # --- Переменные для управления процессом ---
        self._extract_paused = False
        self._extract_stopped = False
        self._extract_current_index = 0

        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Ссылка", "Результат"])
        layout.addWidget(self.table)

        self.attr_combo.currentTextChanged.connect(self.update_radio_attr_state)
        self.update_radio_attr_state()
        self.update_link_display()

    def set_delay(self):
        self.timer.start(500)

    # Блокировка radio_attr если не выбран аттрибут
    def update_radio_attr_state(self):
        attr_selected = bool(self.attr_combo.currentText().strip())
        self.radio_attr.setEnabled(attr_selected)
        if not attr_selected and self.radio_attr.isChecked():
            self.radio_text.setChecked(True)

    def prev_link(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_link_display()

    def next_link(self):
        if self.current_index < len(self.links) - 1:
            self.current_index += 1
            self.update_link_display()

    async def fetch_html(self, link):
        async with aiohttp.ClientSession() as session:
            async with session.get(link) as response:
                return await response.text()

    async def fetch_html_dynamic(self, link):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, 
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",  # Важно для Docker/Linux
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",            
                    "--no-zygote",  # Дополнительное ускорение
                    ],
                timeout=30000,          # Таймаут запуска (мс)
            )
            page = await browser.new_page(
                ignore_https_errors=True, # Игнорирует SSL-ошибки
                viewport=None, # Без фиксированного размера окна
            )
            # Жёсткие настройки для ускорения
            page.set_default_timeout(15000)  # Таймаут ожидания элементов (мс)
            page.set_default_navigation_timeout(100000)  # Таймаут загрузки страницы
            # Блокируем ненужные ресурсты (CSS, изображения, шрифты)
            await page.route("**/*.{png,jpg,jpeg,svg,gif,woff2,woff,eot,ttf,css}", lambda route: route.abort())

            # Отключаем Service Workers и кеш (если не нужен)
            await page.context.clear_permissions()
            await page.context.clear_cookies()
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.alert = () => {};
                window.scrollBy = () => {};
            """)
            await page.goto(link, wait_until="domcontentloaded")
            html = await page.content()
            await browser.close()
            return html

    def update_link_display_dynamic(self):
        if not self.check_box_dynamic.isChecked():
            self.update_link_display()
        link = self.links[self.current_index]
        self.link_label.setText(f"{self.current_index+1}/{len(self.links)}: {link}")
        html = asyncio.run(self.fetch_html_dynamic(link))
        self.html_view.setPlainText(BeautifulSoup(html, "html.parser").prettify())
        self.populate_tag_and_attr_combos(html)
        self.update_result_combo_by_filter()

    def update_link_display(self):
        link = self.links[self.current_index]
        self.link_label.setText(f"{self.current_index+1}/{len(self.links)}: {link}")
#         chrome_options = Options()
#         chrome_options.add_argument("--headless")
#         chrome_options.add_argument("--disable-gpu")
#         chrome_options.add_argument("--no-sandbox")
#         chrome_options.add_argument("--disable-dev-shm-usage")
#         chrome_options.add_argument("--window-size=1920,1080")
#         chrome_options.add_argument("--disable-extensions")
#         chrome_options.add_argument("--disable-plugins")
#         prefs = {
#             "profile.managed_default_content_settings.images": 2,
#             "profile.managed_default_content_settings.stylesheets": 2,
#             "profile.managed_default_content_settings.fonts": 2,
#             "profile.managed_default_content_settings.popups": 2,
#             "profile.managed_default_content_settings.geolocation": 2,
#             "profile.managed_default_content_settings.notifications": 2,
#             "profile.managed_default_content_settings.media_stream": 2,
# }
#         chrome_options.add_experimental_option("prefs", prefs)
#         driver = webdriver.Chrome(options=chrome_options)
#         driver.get(link)
#         html = driver.page_source
#         driver.quit()
        # r = requests.get(link, timeout=10)
        # html = r.text
        html = asyncio.run(self.fetch_html(link))
        # html = asyncio.run(self.fetch_html_dynamic(link))
        self.html_view.setPlainText(BeautifulSoup(html, "html.parser").prettify())
        self.populate_tag_and_attr_combos(html)
        self.update_result_combo_by_filter()

    def populate_tag_and_attr_combos(self, html):
        soup = BeautifulSoup(html, "html.parser")
        tags = set([tag.name for tag in soup.find_all()])
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem("")
        for tag in sorted(tags):
            self.tag_combo.addItem(tag)
        self.tag_combo.blockSignals(False)
        self.update_attr_combo()

    def update_attr_combo(self):
        tag = self.tag_combo.currentText().strip()
        html = self.html_view.toPlainText()
        soup = BeautifulSoup(html, "html.parser")
        attrs = set()
        if tag:
            for el in soup.find_all(tag):
                attrs.update(el.attrs.keys())
        else:
            for el in soup.find_all():
                attrs.update(el.attrs.keys())
        self.attr_combo.blockSignals(True)
        self.attr_combo.clear()
        self.attr_combo.addItem("")
        for attr in sorted(attrs):
            self.attr_combo.addItem(attr)
        self.attr_combo.blockSignals(False)
        self.update_result_combo_by_filter()

    def update_result_combo_by_filter(self):
        html = self.html_view.toPlainText()
        tag = self.tag_combo.currentText().strip()
        attr = self.attr_combo.currentText().strip()
        value = self.value_edit.text().strip()
        if not tag and not attr and not value:
            self.result_combo.clear()
            self.result_lable.setText("Результаты: (0)")
            return
        result = self.extract_from_html_with_slice(html, tag, attr, value)
        self.populate_result_combo(result)

    def extract_current(self):
        link = self.links[self.current_index]
        html = self.html_view.toPlainText()
        tag = self.tag_combo.currentText().strip()
        attr = self.attr_combo.currentText().strip()
        value = self.value_edit.text().strip()
        result = self.extract_from_html_with_slice(html, tag, attr, value)
        self.results.append((link, result))
        QMessageBox.information(self, "Готово", "Данные извлечены из текущей ссылки.")

    # def extract_all(self):
    #     self.results.clear()
    #     tag = self.tag_combo.currentText().strip()
    #     attr = self.attr_combo.currentText().strip()
    #     value = self.value_edit.text().strip()
    #     self.progress_bar.setVisible(True)
    #     self.progress_bar.setMinimum(0)
    #     self.progress_bar.setMaximum(len(self.links))
    #     self.progress_bar.setValue(0)
    #     for i, link in enumerate(self.links):
    #         try:
    #             html = requests.get(link, timeout=10).text
    #             result = self.extract_from_html_with_slice(html, tag, attr, value)
    #         except Exception as e:
    #             result = f"Ошибка: {e}"
    #         self.results.append((link, result))
    #         self.progress_bar.setValue(i + 1)
    #         QApplication.processEvents()
    #     self.progress_bar.setVisible(False)
    #     QMessageBox.information(self, "Готово", "Данные извлечены из всех ссылок.")

    def extract_from_html_with_slice(self, html, tag, attr, value):
        soup = BeautifulSoup(html, "html.parser")
        elements = soup.find_all(tag) if tag else soup.find_all()
        filtered = []
        for el in elements:
            if attr:
                if el.has_attr(attr):
                    if not value or value in str(el[attr]):
                        if self.radio_attr.isChecked():
                            filtered.append(str(el[attr]))
                        else:
                            filtered.append(el.get_text(strip=True))
            else:
                if self.radio_attr.isChecked():
                     continue  # нельзя извлекать значение аттрибута без выбора аттрибута
                filtered.append(el.get_text(strip=True))
        start = self.slice_start_spin.value()
        end = self.slice_end_spin.value()
        if end > 0:
            filtered = filtered[start:end]
        else:
            filtered = filtered[start:]
        return "; ".join(filtered)

    def populate_result_combo(self, result_str):
        self.result_combo.clear()
        self.result_combo.addItem("")
        results = [r for r in result_str.split("; ") if r]
        self.result_combo.addItems(results)
        self.result_lable.setText(f"Результаты: ({len(results)})")

    def show_results(self):
        self.table.setRowCount(len(self.results))
        for i, (link, result) in enumerate(self.results):
            self.table.setItem(i, 0, QTableWidgetItem(link))
            self.table.setItem(i, 1, QTableWidgetItem(result))

    def add_to_dataset(self):
        if self.main_window and hasattr(self.main_window, "extract_data"):
            QMessageBox.information(self, "Интеграция", "Вызовите здесь функцию добавления к датасету.")
        else:
            QMessageBox.warning(self, "Ошибка", "Главное окно не передано или не содержит функцию extract_data.")

    def highlight_result_in_html(self, result_text):
        # Очистить предыдущие подсветки
        cursor = self.html_view.textCursor()
        cursor.select(QTextCursor.Document)
        # cursor.setCharFormat(QTextCharFormat())  # сбросить форматирование

        # Найти и подсветить первое вхождение result_text
        html = self.html_view.toPlainText()
        if not result_text:
            return

        start_idx = html.find(result_text)
        if start_idx == -1:
            return

        end_idx = start_idx + len(result_text)

        # Установить курсор на найденный текст
        cursor.setPosition(start_idx)
        cursor.setPosition(end_idx, QTextCursor.KeepAnchor)

        # fmt = QTextCharFormat()
        # fmt.setBackground(QColor(255, 255, 0, 128))  # полупрозрачный желтый
        # cursor.setCharFormat(fmt)

        # Прокрутить к выделенному месту
        self.html_view.setTextCursor(cursor)


    def on_result_combo_activated(self):
        result_text = self.result_combo.currentText()
        if result_text:
            self.highlight_result_in_html(result_text)
            self.auto_select_tag_attr_value(result_text)

    def auto_select_tag_attr_value(self, result_text):
        html = self.html_view.toPlainText()
        soup = BeautifulSoup(html, "html.parser")
        # Найти все элементы, чей текст совпадает с result_text
        matches = []
        for tag in soup.find_all():
            text = tag.get_text(strip=True)
            if text == result_text:
                matches.append(tag)

        if not matches:
            return

        # Сформировать список вариантов для выбора и сопоставить их с тегами
        options = []
        option_tags = []
        for tag in matches:
            tag_name = tag.name
            attrs = tag.attrs
            if len(attrs) > 1:
                for attr_name, attr_value in attrs.items():
                    options.append(f"Тег: <{tag_name}>, Аттрибут: {attr_name}, Значение: {attr_value}")
                    new_tag = soup.new_tag(tag_name)
                    new_tag[attr_name] = attr_value
                    option_tags.append(new_tag)
            elif attrs:
                attr_name, attr_value = next(iter(attrs.items()))
                options.append(f"Тег: <{tag_name}>, Аттрибут: {attr_name}, Значение: {attr_value}")
                option_tags.append(tag)
            else:
                options.append(f"Тег: <{tag_name}>, Без аттрибутов")
                option_tags.append(tag)

        # Если найдено несколько вариантов, спросить пользователя
        if len(options) > 1:
            dialog = QInputDialog(self)
            # dialog.setStyleSheet("""
            #     QComboBox {
            #         max-width: 500px;
            #     }
            #     QInputDialog {                  
            #         max-width: 500px;             
            #     }
                
            # """)
            # for widget in dialog.children():
            #     print(widget.metaObject().className())
            # combo = dialog.findChild(QComboBox)
            # if combo:
            #     combo.setFixedWidth(500)
            item, ok = dialog.getItem(
                self,
                "Выбор селектора",
                "Найдено несколько совпадений. Выберите нужный вариант:",
                options,
                0,
                False
            )
            if not ok:
                return
            selected_idx = options.index(item)
            selected_tag = option_tags[selected_idx]
        else:
            selected_tag = matches[0]

        # Применить выбранный селектор
        tag_name = selected_tag.name
        idx = self.tag_combo.findText(tag_name)
        if idx != -1:
            self.tag_combo.setCurrentIndex(idx)
        else:
            self.tag_combo.setCurrentText(tag_name)
        if selected_tag.attrs:
            attr_name, attr_value = next(iter(selected_tag.attrs.items()))
            idx_attr = self.attr_combo.findText(attr_name)
            if idx_attr != -1:
                self.attr_combo.setCurrentIndex(idx_attr)
                self.value_edit.setText(str(attr_value))
            else:
                self.attr_combo.setCurrentText(attr_name)
                self.value_edit.setText(str(attr_value))
        else:
            self.attr_combo.setCurrentIndex(0)
            self.value_edit.clear()

    def on_stop_clicked(self):
        self._extract_paused = True
        self.stop_btn.setVisible(False)
        self.resume_btn.setVisible(True)
        self.cancel_btn.setVisible(True)

    def on_resume_clicked(self):
        self._extract_paused = False
        self.resume_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.stop_btn.setVisible(True)
        self._continue_extract_all()

    def on_cancel_clicked(self):
        self._extract_stopped = True
        self.resume_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.stop_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        QMessageBox.information(self, "Остановлено", "Извлечение остановлено. Результаты сохранены.")

    def extract_all(self):
        self.results.clear()
        tag = self.tag_combo.currentText().strip()
        attr = self.attr_combo.currentText().strip()
        value = self.value_edit.text().strip()
        self.progress_bar.setVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(len(self.links))
        self.progress_bar.setValue(0)
        self._extract_paused = False
        self._extract_stopped = False
        self._extract_current_index = 0
        self.stop_btn.setVisible(True)
        self.resume_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self._extract_all_links(tag, attr, value)

    def _extract_all_links(self, tag, attr, value):
        while self._extract_current_index < len(self.links):
            if self._extract_stopped:
                break
            if self._extract_paused:
                return  # Остановить цикл, пока не возобновят
            i = self._extract_current_index
            link = self.links[i]
            try:
                html = requests.get(link, timeout=10).text
                result = self.extract_from_html_with_slice(html, tag, attr, value)
            except Exception as e:
                result = f"Ошибка: {e}"
            self.results.append((link, result))
            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()
            self._extract_current_index += 1
        self.stop_btn.setVisible(False)
        self.resume_btn.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        if not self._extract_stopped:
            QMessageBox.information(self, "Готово", "Данные извлечены из всех ссылок.")

    def _continue_extract_all(self):
        tag = self.tag_combo.currentText().strip()
        attr = self.attr_combo.currentText().strip()
        value = self.value_edit.text().strip()
        self._extract_all_links(tag, attr, value)

    