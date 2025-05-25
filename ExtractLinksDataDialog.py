from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QTextEdit,
    QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar, QApplication, QSpinBox, QRadioButton,
    QInputDialog, QSizePolicy, QCheckBox
)
from PyQt5.QtCore import QTimer, QEvent
import requests
from bs4 import BeautifulSoup
from PyQt5.QtGui import QTextCursor
import aiohttp
import asyncio
from playwright.async_api import async_playwright
from qasync import asyncSlot, QEventLoop
import nest_asyncio
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

        # Применяем патч для вложенных event loop
        # nest_asyncio.apply()
        
        # Создаем адаптированный event loop
        # self.loop = QEventLoop(self)
        # asyncio.set_event_loop(self.loop)
        # self.loop = asyncio.get_event_loop()
        # if not self.loop.is_running():
        #     # Создаем новый loop если нет запущенного
        #     self.loop = asyncio.new_event_loop()
        #     asyncio.set_event_loop(self.loop)
        
        # Флаг для отслеживания работы
        self._is_extracting = False

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)  # Таймер срабатывает только один раз
        self.timer.timeout.connect(self.update_result_combo_by_filter) 

        layout = QVBoxLayout(self)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("←", self)
        self.prev_btn.clicked.connect(lambda: asyncio.create_task(self.prev_link()))
        self.next_btn = QPushButton("→", self)
        self.next_btn.clicked.connect(lambda: asyncio.create_task(self.next_link()))
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
        self.check_box_dynamic.toggled.connect(lambda: asyncio.create_task(self.update_link_display_dynamic()))


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
        asyncio.create_task(self.update_link_display())

    def set_delay(self):
        self.timer.start(500)

    # Блокировка radio_attr если не выбран аттрибут
    def update_radio_attr_state(self):
        attr_selected = bool(self.attr_combo.currentText().strip())
        self.radio_attr.setEnabled(attr_selected)
        if not attr_selected and self.radio_attr.isChecked():
            self.radio_text.setChecked(True)

    async def prev_link(self):
        if self.current_index > 0:
            self.current_index -= 1
            await self.update_link_display_dynamic()

    async def next_link(self):
        if self.current_index < len(self.links) - 1:
            self.current_index += 1
            await self.update_link_display_dynamic()

    async def fetch_html(self, link):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(link) as response:
                    return await response.text()
        except Exception as e:
            print(f"Error fetching {link}: {e}")
            return ""

    async def fetch_html_dynamic(self, link):
        try:
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
        except Exception as e:
            print(f"Error fetching dynamic content {link}: {e}")
            return ""
   
    async def update_link_display_dynamic(self):
        if not self.check_box_dynamic.isChecked():
            await self.update_link_display()
            return
        link = self.links[self.current_index]
        self.link_label.setText(f"{self.current_index+1}/{len(self.links)}: {link}")
        html = await self.fetch_html_dynamic(link)
        self.html_view.setPlainText(BeautifulSoup(html, "html.parser").prettify())
        self.populate_tag_and_attr_combos(html)
        self.update_result_combo_by_filter()
    
    async def update_link_display(self):
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
        html = await self.fetch_html(link)
        # html = asyncio.run(self.fetch_html_dynamic(link))
        self.html_view.setPlainText(BeautifulSoup(html, "html.parser").prettify())
        self.populate_tag_and_attr_combos(html)
        # self.update_result_combo_by_filter()

        # html = asyncio.run(self.fetch_html_dynamic(link))
    # def _handle_fetched_html(self, html):
    #     if html:
    #         self.html_view.setPlainText(BeautifulSoup(html, "html.parser").prettify())
    #         self.populate_tag_and_attr_combos(html)
    #         self.update_result_combo_by_filter()

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
        self.value_edit.clear()
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

    @asyncSlot()
    async def extract_all(self):
        if self._is_extracting:
            return
        try:
            self._is_extracting = True
            self.loop = asyncio.get_event_loop()
            self.results.clear()
            tag = self.tag_combo.currentText().strip()
            attr = self.attr_combo.currentText().strip()
            value = self.value_edit.text().strip()
            
            # Настройка UI
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

            # Запуск асинхронного процесса
            if self.check_box_dynamic.isChecked():
                await self._extract_all_links_playwright(tag, attr, value)
            else:
                await self._extract_all_links_aiohttp(tag, attr, value)
        finally:
            self._is_extracting = False
            # Завершение
            self.stop_btn.setVisible(False)
            self.progress_bar.setVisible(False)
            if not self._extract_stopped:
                QMessageBox.information(self, "Готово", "Данные извлечены из всех ссылок.")

    async def _extract_all_links_aiohttp(self, tag, attr, value):
        async with aiohttp.ClientSession() as session:
            while self._extract_current_index < len(self.links):
                if self._extract_stopped:
                    break
                
                while self._extract_paused:
                    await asyncio.sleep(0.5)  # Небольшая пауза при ожидании
                    QApplication.processEvents()
                    continue

                i = self._extract_current_index
                link = self.links[i]
                
                try:
                    html = await self.fetch_html(session, link)
                    result = self.extract_from_html_with_slice(html, tag, attr, value)
                except Exception as e:
                    result = f"Ошибка: {e}"
                
                self.results.append((link, result))
                self.progress_bar.setValue(i + 1)
                QApplication.processEvents()
                self._extract_current_index += 1
    # async def _extract_all_links_aiohttp(self, tag, attr, value):
    #     connector = aiohttp.TCPConnector(limit=10)  # Ограничение параллельных соединений
    #     timeout = aiohttp.ClientTimeout(total=30)
    #     async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
    #         semaphore = asyncio.Semaphore(10)  # Максимум 10 параллельных запросов
    #         tasks = []
            
    #         for i in range(self._extract_current_index, len(self.links)):
    #             if self._extract_stopped:
    #                 break
                
    #             task = asyncio.create_task(
    #                 self._process_aiohttp_request(
    #                     session, 
    #                     self.links[i], 
    #                     tag, 
    #                     attr, 
    #                     value, 
    #                     semaphore
    #                 )
    #             )
    #             # task.add_done_callback(
    #             #     lambda t: QApplication.postEvent(self, _TaskDoneEvent(t))
    #             # )
    #             tasks.append(task)
            
    #         while tasks and not self._extract_stopped:
    #             await asyncio.sleep(0.1)  # Даем возможность обработать события Qt
    #             QApplication.processEvents()

    # async def _process_aiohttp_request(self, session, url, tag, attr, value, semaphore):
    #     async with semaphore:
    #         while self._extract_paused and not self._extract_stopped:
    #             await asyncio.sleep(0.5)
    #             QApplication.processEvents()
            
    #         if self._extract_stopped:
    #             return
                
    #         try:
    #             async with session.get(url) as response:
    #                 html = await response.text()
    #                 # result = self.extract_from_html_with_slice(html, tag, attr, value)
                    
    #                 # Передаем результат в основной поток Qt
    #                 self.loop.call_soon_threadsafe(
    #                     lambda: self._handle_page_result(url, html, tag, attr, value))
                    
    #         except Exception as e:
    #             QMessageBox.information(self, "Ошибка", f"Ошибка при обработке {url}: {str(e)}") 
    #             # self.loop.call_soon_threadsafe(
    #             #     lambda: self._handle_extraction_result(url, error_msg))
    #             return
            
    async def _extract_all_links_playwright(self, tag, attr, value):
        async with async_playwright() as p:
            # Настройка браузера с оптимизациями
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            # Семафор для ограничения параллельных вкладок
            semaphore = asyncio.Semaphore(5)  # 5 параллельных вкладок
            
            async def process_link(link):
                async with semaphore:
                    if self._extract_stopped:
                        return 
                    
                    while self._extract_paused:
                        await asyncio.sleep(0.5)
                        QApplication.processEvents()
                        if self._extract_stopped:
                            return 
                    
                    try:
                        context = await browser.new_context()
                        page = await context.new_page()
                        
                        # Ускоренные настройки страницы
                        await page.route("**/*.{png,jpg,svg,woff2,css}", lambda route: route.abort())
                        await page.goto(link, timeout=15000, wait_until="domcontentloaded")
                        
                        html = await page.content()
                        result = self.extract_from_html_with_slice(html, tag, attr, value)
                        
                        await context.close()
                        
                        return (link, result)
                    except Exception as e:
                        await context.close()
                        return (link, f"Ошибка: {e}")

            # Запускаем задачи параллельно
            tasks = []
            for i in range(self._extract_current_index, len(self.links)):
                if self._extract_stopped:
                    break
                tasks.append(process_link(self.links[i]))
            
            # Обрабатываем результаты по мере выполнения
            for future in asyncio.as_completed(tasks):
                result = await future
                if result:
                    self.results.append(result)
                    self._extract_current_index += 1
                    self.progress_bar.setValue(self._extract_current_index)
                    QApplication.processEvents()

            await browser.close()       
    # async def _extract_all_links_playwright(self, tag, attr, value):
    #     # def create_task_callback(task):
    #     #     """Мост между asyncio и Qt"""
    #     #     def callback():
    #     #         if task.done():
    #     #             self.loop.call_soon_threadsafe(task.result)
    #     #         else:
    #     #             QTimer.singleShot(100, callback)
    #     #     return callback
        
    #     async with async_playwright() as p:
    #         # Настройка браузера с оптимизациями
    #         browser = await p.chromium.launch(
    #             headless=True,
    #             args=["--disable-blink-features=AutomationControlled"]
    #         )
            
    #         # Семафор для ограничения параллельных вкладок
    #         semaphore = asyncio.Semaphore(5)  # 5 параллельных вкладок
    #         tasks = set()
    #         for i in range(self._extract_current_index, len(self.links)):
    #             if self._extract_stopped:
    #                 break
                    
    #             task = asyncio.create_task(
    #                 self._process_playwright_page(browser, self.links[i], tag, attr, value, semaphore)
    #             )
    #             # task.add_done_callback(
    #             #     lambda t: QApplication.postEvent(self, _TaskDoneEvent(t))
    #             # )
    #             tasks.add(task)

    #         while tasks and not self._extract_stopped:
    #             await asyncio.sleep(0.1)
    #             QApplication.processEvents()

    #         await browser.close()

    # async def _process_playwright_page(self, browser, link, tag, attr, value, semaphore):
    #     async with semaphore:
    #         context = await browser.new_context()
    #         try:
    #             page = await context.new_page()
    #             await page.goto(link)
    #             html = await page.content()
                
    #             # Возвращаем результат в UI поток
    #             self.loop.call_soon_threadsafe(
    #                 lambda: self._handle_page_result(link, html, tag, attr, value))
    #         finally:
    #             await context.close()

    def _handle_page_result(self, link, html, tag, attr, value):
        """Обработка результата в основном потоке Qt"""
        result = self.extract_from_html_with_slice(html, tag, attr, value)
        self.results.append((link, result))
        self._extract_current_index += 1
        self.progress_bar.setValue(self._extract_current_index)

    def closeEvent(self, event):
        """Корректное завершение при закрытии окна"""
        if self._is_extracting:
            self._extract_stopped = True
            # Останавливаем все pending tasks
            for task in asyncio.all_tasks(self.loop):
                task.cancel()
        super().closeEvent(event)



    def _continue_extract_all(self):
        tag = self.tag_combo.currentText().strip()
        attr = self.attr_combo.currentText().strip()
        value = self.value_edit.text().strip()
        
        if self.check_box_dynamic.isChecked():
            asyncio.create_task(self._extract_all_links_playwright(tag, attr, value))
        else:
            asyncio.create_task(self._extract_all_links_aiohttp(tag, attr, value))

# class _TaskDoneEvent(QEvent):
#     """Специальное событие для обработки завершения задач"""
#     def __init__(self, task):
#         super().__init__(QEvent.Type(QEvent.User+1))
#         self.task = task
    