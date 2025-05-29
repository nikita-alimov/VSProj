from PyQt5.QtWidgets import QDialog, QMessageBox, QVBoxLayout, QHBoxLayout, QInputDialog, QLabel, QComboBox, QPushButton, QTextEdit, QLineEdit, QSizePolicy
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt
from ExtractLinksDataDialog import ExtractLinksDataDialog

class ParseLinksDialog(QDialog):
    def __init__(self, links_by_tag_attribute, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Парсинг ссылок")
        self.setMinimumSize(600, 400)

        self.links_by_tag_attribute = links_by_tag_attribute
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)  # Таймер срабатывает только один раз
        self.timer.timeout.connect(self.apply_filter)  # Скрыть error_label по истечении времени

        # Основной макет
        layout = QVBoxLayout(self)

        # Макет для выбора пары тег-аттрибут
        pair_layout = QHBoxLayout()
        self.pair_label = QLabel("Выберите пару тег-аттрибут:", self)
        self.pair_combobox = QComboBox(self)
        self.pair_combobox.addItems(sorted(links_by_tag_attribute.keys()))
        self.pair_combobox.currentIndexChanged.connect(self.update_links_combobox)
        pair_layout.addWidget(self.pair_label)
        pair_layout.addWidget(self.pair_combobox)
        layout.addLayout(pair_layout)

        # Макет для отображения ссылок
        links_layout = QHBoxLayout()
        self.links_label = QLabel("Ссылки:", self)
        self.links_combobox = QComboBox(self)
        links_layout.addWidget(self.links_label)
        links_layout.addWidget(self.links_combobox)
        layout.addLayout(links_layout)

        # Текстовое поле для отображения выбранной ссылки
        self.link_display = QTextEdit(self)
        self.link_display.setReadOnly(True)
        layout.addWidget(self.link_display)

        # Поле для фильтрации ссылок
        filter_layout = QHBoxLayout()
        self.filter_label = QLabel("Фильтр ссылок:", self)
        self.filter_edit = QLineEdit(self)
        self.filter_edit.textChanged.connect(self.changing)
        filter_layout.addWidget(self.filter_label)
        filter_layout.addWidget(self.filter_edit)
        layout.addLayout(filter_layout)

        # Макет для отображения отфильтрованных ссылок
        filtered_links_layout = QHBoxLayout()
        self.filtered_links_label = QLabel("Отфильтрованные ссылки (0):", self)
        self.filtered_links_combobox = QComboBox(self)
        self.filtered_links_combobox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        filtered_links_layout.addWidget(self.filtered_links_label)
        filtered_links_layout.addWidget(self.filtered_links_combobox)
        layout.addLayout(filtered_links_layout)

        self.extract_links_data_btn = QPushButton("Извлечь данные по ссылкам", self)
        self.extract_links_data_btn.clicked.connect(self.open_extract_links_data_dialog)
        layout.addWidget(self.extract_links_data_btn)

        self.extract_img_btn = QPushButton("Сохранить в датафрейм (только для изображений)", self)
        self.extract_img_btn.clicked.connect(self.extract_img)
        layout.addWidget(self.extract_img_btn)

        self.close_button = QPushButton("Закрыть", self)
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)

        # Изначально обновить ссылки
        self.update_links_combobox()

    def changing(self):
        self.timer.start(500)  # Запустить таймер на 0.5 секунды


    def update_links_combobox(self):
        """Обновить список ссылок в зависимости от выбранной пары тег-аттрибут."""
        selected_pair = self.pair_combobox.currentText()
        links = self.links_by_tag_attribute.get(selected_pair, [])
        self.links_combobox.clear()
        self.links_combobox.addItems(links)

        # Обновить текстовое поле для отображения первой ссылки
        if links:
            self.links_label.setText(f"Ссылки ({len(links)}):")
            self.link_display.setText(links[0])
            self.changing()
        else:
            self.link_display.clear()

        # Подключить событие изменения ссылки
        self.links_combobox.currentIndexChanged.connect(self.update_link_display)

    def update_link_display(self):
        """Обновить текстовое поле для отображения выбранной ссылки."""
        selected_link = self.links_combobox.currentText()
        self.link_display.setText(selected_link)

    def apply_filter(self):
        """Применить фильтр к ссылкам."""

        filter_text = self.filter_edit.text().strip()
        if(not filter_text):
            self.filtered_links_label.setText("Отфильтрованные ссылки (0):")
            self.filtered_links_combobox.clear()
            return
        selected_pair = self.pair_combobox.currentText()
        links = self.links_by_tag_attribute.get(selected_pair, [])

        # Фильтровать ссылки
        filtered_links = [link for link in links if filter_text.lower() in link.lower()]
        
        if filtered_links:
            self.filtered_links_label.setText(f"Отфильтрованные ссылки ({len(filtered_links)}):")
        else:
            self.filtered_links_label.setText("Отфильтрованные ссылки (0):")    

        # Обновить выпадающий список отфильтрованных ссылок
        self.filtered_links_combobox.clear()
        self.filtered_links_combobox.addItems(filtered_links)   

    def open_extract_links_data_dialog(self):
        if self.filtered_links_combobox.count() > 0:
            links = [self.filtered_links_combobox.itemText(i) for i in range(self.filtered_links_combobox.count())]
        else:
            links = [self.links_combobox.itemText(i) for i in range(self.links_combobox.count())]
        if not links:
            QMessageBox.warning(self, "Нет ссылок", "Нет ссылок для обработки.")
            return
        dlg = ExtractLinksDataDialog(links, parent=self, main_window=self.parent())
        dlg.exec_()    

    def extract_img(self):
        """
        Сохраняет ссылки на изображения в датафрейм главного окна (WebScrapingInterface).
        Использует отфильтрованные ссылки, если они есть, иначе все ссылки.
        """
        # Получаем ссылки из отфильтрованного комбобокса или из обычного
        if self.filtered_links_combobox.count() > 0:
            links = [self.filtered_links_combobox.itemText(i) for i in range(self.filtered_links_combobox.count())]
        else:
            links = [self.links_combobox.itemText(i) for i in range(self.links_combobox.count())]

        if not links:
            QMessageBox.warning(self, "Нет ссылок", "Нет ссылок для сохранения в датафрейм.")
            return

        # Проверяем, что ссылки действительно ведут на изображения (опционально)
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        image_links = [link for link in links if any(ext in link.lower() for ext in image_extensions)]
        
        if not image_links:
            reply = QMessageBox.question(
                self,
                "Нет изображений",
                "Среди выбранных ссылок не обнаружено изображений (jpg, png, gif, webp, svg).\n"
                "Все равно сохранить в датафрейм?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            image_links = links  # Используем все ссылки, если пользователь согласился

        # Запрашиваем у пользователя имя поля
        field_name, ok = QInputDialog.getText(
            self,
            "Имя поля",
            "Введите название поля для сохранения ссылок:",
            text="image_url"  # Значение по умолчанию
        )
        
        if not ok or not field_name.strip():
            return  # Пользователь отменил ввод

        field_name = field_name.strip()

        # Получаем доступ к главному окну
        main_window = self.parent()
        if not hasattr(main_window, 'extract_data'):
            QMessageBox.warning(self, "Ошибка", "Не удалось получить доступ к главному окну.")
            return

        # Передаем ссылки в главное окно для сохранения в датафрейм
        main_window.extract_data(data_list=image_links, field_name=field_name)
        
        # Закрываем диалог после успешного сохранения
        self.close()