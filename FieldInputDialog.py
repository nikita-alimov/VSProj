from PyQt5.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QSizePolicy, QLineEdit, QDialogButtonBox, QLabel, QSpinBox, QRadioButton, QButtonGroup, QMessageBox
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import QTimer
from bs4 import BeautifulSoup

class SliceInputDialog(QDialog):
    def __init__(self, html, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Параметры извлечения данных")

        self.changing_timer = QTimer(self)
        self.changing_timer.setSingleShot(True)
        self.changing_timer.timeout.connect(self.filter_data)

        # Таймер для скрытия error_label
        self.error_timer = QTimer(self)
        self.error_timer.setSingleShot(True)  # Таймер срабатывает только один раз
        self.error_timer.timeout.connect(self.hide_error_label)  # Скрыть error_label по истечении времени

        # Сохранить HTML и инициализировать BeautifulSoup
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')
        self.all_data = []
        
        # Макет диалога
        layout = QVBoxLayout(self)

        # Поле для ввода названия тега (необязательно)
        self.tag_label = QLabel("Название тега из которого нужно извлеч данные (необязательно):", self)
        self.tag_input = QComboBox(self)
        self.tag_input.addItem("")  # Пустой элемент
        self.tag_input.addItems(sorted({tag.name for tag in self.soup.find_all()}))
        self.tag_input.activated.connect(self.filter_data)  # Обновить данные при изменении
        layout.addWidget(self.tag_label)
        layout.addWidget(self.tag_input)

        # Поле для ввода названия атрибута (необязательно)
        self.attribute_label = QLabel("Название атрибута из которого нужно извлеч данные (необязательно):", self)
        self.attribute_input = QComboBox(self)
        self.attribute_input.addItem("")  # Пустой элемент
        self.attribute_input.addItems(sorted({attr for tag in self.soup.find_all() for attr in tag.attrs}))
        self.attribute_input.activated.connect(self.filter_data)  # Обновить данные при изменении
        layout.addWidget(self.attribute_label)
        layout.addWidget(self.attribute_input)

        # Поле для фильтрации по значению атрибута (необязательно)
        self.filter_attribute_value_label = QLabel("Значение фильтра аттрибута (необязательно):", self)
        self.filter_attribute_value_input = QLineEdit(self)
        self.filter_attribute_value_input.textChanged.connect(self.changing_delay)
        layout.addWidget(self.filter_attribute_value_label)
        layout.addWidget(self.filter_attribute_value_input)

        # Радиокнопки для выбора способа извлечения данных
        self.extract_mode_label = QLabel("Выберите способ извлечения данных:", self)
        layout.addWidget(self.extract_mode_label)

        self.extract_mode_group = QButtonGroup(self)  # Создаем группу для радиокнопок

        self.extract_text_radio = QRadioButton("Извлекать текст между тегами", self)
        self.extract_attribute_radio = QRadioButton("Извлекать значение атрибута", self)
        self.extract_text_radio.setChecked(True)  # Установить вариант по умолчанию

        self.extract_mode_group.addButton(self.extract_text_radio)
        self.extract_mode_group.addButton(self.extract_attribute_radio)
        self.extract_text_radio.toggled.connect(self.filter_data)  # Обновить данные при изменении

        layout.addWidget(self.extract_text_radio)
        layout.addWidget(self.extract_attribute_radio)
        
        # Поле для ввода начала среза
        self.start_label = QLabel("Начальная строка (0-based):", self)
        self.start_input = QSpinBox(self)
        self.start_input.setRange(0, 0)
        layout.addWidget(self.start_label)
        layout.addWidget(self.start_input)

        # Поле для ввода конца среза
        self.end_label = QLabel("Конечная строка (0-based, включительно):", self)
        self.end_input = QSpinBox(self)
        self.end_input.setRange(0, 0)
        # self.end_input.setValue(max_index)
        layout.addWidget(self.end_label)
        layout.addWidget(self.end_input)

        # Чекбокс для исключения или вывода пустых значений
        self.exclude_empty_checkbox = QCheckBox("Исключить пустые значения", self)
        self.exclude_empty_checkbox.setChecked(True)  # По умолчанию исключать пустые значения
        self.exclude_empty_checkbox.toggled.connect(self.filter_data)  # Обновить данные при изменении состояния
        layout.addWidget(self.exclude_empty_checkbox)

        # Поле для отображения всех элементов после фильтрации и среза
        self.result_label = QLabel("Результаты фильтрации (0):", self)
        self.result_combobox = QComboBox(self)
        self.result_combobox.setMinimumWidth(self.tag_input.minimumSizeHint().width())
        self.result_combobox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.result_combobox.setMaximumWidth(400) 
        layout.addWidget(self.result_label)
        layout.addWidget(self.result_combobox)

        # Поле для ввода имени поля
        self.field_label = QLabel("Название поля для сохранения данных:", self)
        self.field_input = QLineEdit(self)
        layout.addWidget(self.field_label)
        layout.addWidget(self.field_input)

        # Поле для отображения ошибок
        self.error_label = QLabel("", self)
        self.error_label.setStyleSheet("color: red;")  # Красный текст для ошибок
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Кнопки OK и Cancel
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.validate_inputs)  # Проверить ввод перед принятием
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        # Изначально обновить данные
        self.filter_data()

    def get_values(self):
        """Возвращает значения, введенные пользователем."""
        return self.all_data, self.start_input.value(), self.end_input.value(), self.field_input.text()
    
    def changing_delay(self):
        """Запускает таймер при изменении текста в поле фильтрации."""
        self.changing_timer.start(500)

    def validate_inputs(self):
        """Проверить корректность введенных данных."""
        start = self.start_input.value()
        end = self.end_input.value()
        field_name = self.field_input.text().strip()

        # Проверить корректность диапазона
        if start > end:
            self.error_label.setText("Начальная строка не может быть больше конечной.")
            self.error_label.show()
            self.error_timer.start(7000)  # Перезапустить таймер на 7 секунд
            return

        # Проверить, введено ли имя поля
        if not field_name:
            self.error_label.setText("Название поля не может быть пустым.")
            self.error_label.show()
            self.error_timer.start(7000)  # Перезапустить таймер на 7 секунд
            return

        # Если все проверки пройдены, принять диалог
        self.accept()

    def hide_error_label(self):
        """Скрыть error_label."""
        self.error_label.hide()

    def filter_data(self):
        """Фильтрует данные из HTML на основе выбранных параметров."""
        selected_tag = self.tag_input.currentText()
        selected_attribute = self.attribute_input.currentText()
        extract_text = self.extract_text_radio.isChecked()
        filter_value = self.filter_attribute_value_input.text().strip()
        
        # Фильтровать данные
        if extract_text:
            # Извлекать текст между тегами
            if selected_tag:
                if selected_attribute:
                    self.all_data = [
                        element.get_text(strip=True)
                        for element in self.soup.find_all(selected_tag)
                        if element.has_attr(selected_attribute) and (
                            not filter_value or (
                                isinstance(element.get(selected_attribute), list) and filter_value in element.get(selected_attribute)
                            ) or (
                                isinstance(element.get(selected_attribute), str) and filter_value in element.get(selected_attribute)
                            )
                        )
                    ]
                else:
                    self.all_data = [element.get_text(strip=True) for element in self.soup.find_all(selected_tag)]
            elif selected_attribute:
                self.all_data = [
                    element.get_text(strip=True)
                    for element in self.soup.find_all()
                    if element.has_attr(selected_attribute) and (
                        not filter_value or (
                            isinstance(element.get(selected_attribute), list) and filter_value in element.get(selected_attribute)
                        ) or (
                            isinstance(element.get(selected_attribute), str) and filter_value in element.get(selected_attribute)
                        )
                    )
                ]
            else:
                self.all_data = [element.get_text(strip=True) for element in self.soup.find_all()]
        else:
            # Извлекать значение атрибута
            if not selected_attribute:
                self.error_label.setText("Название поля не может быть пустым.")
                self.error_label.show()
                self.extract_text_radio.setChecked(True) 
                self.error_timer.start(7000)  # Перезапустить таймер на 7 секунд
                return
            
            elif not selected_tag:
                self.all_data = [
                    " ".join(element.get(selected_attribute, [])).strip() if isinstance(element.get(selected_attribute), list) 
                    else element.get(selected_attribute, "").strip() 
                    for element in self.soup.find_all()
                ]
            else:
                self.all_data = [                    
                    " ".join(element.get(selected_attribute, [])).strip() if isinstance(element.get(selected_attribute), list) 
                    else element.get(selected_attribute, "").strip() 
                    for element in self.soup.find_all(selected_tag)]
            if self.all_data:
                # Фильтровать данные по значению атрибута, если указано
                if filter_value:
                    self.all_data = [
                        value for value in self.all_data if filter_value in value
                    ]
        if self.all_data:
            # Исключить пустые значения, если установлен флажок
            if self.exclude_empty_checkbox.isChecked():
                self.all_data = [value for value in self.all_data if value]        

        # Обновить диапазоны SpinBox
        max_index = max(0, len(self.all_data) - 1)
        self.start_input.setRange(0, max_index)
        self.end_input.setRange(0, max_index)
        self.end_input.setValue(max_index)

        # Обновить результаты при изменении фильтрации
        self.result_combobox_update()

    def result_combobox_update(self):
        """Обновить выпадающий список с результатами фильтрации."""
        self.result_combobox.clear()
        self.result_combobox.addItems(self.all_data)
        self.result_label.setText(f"Результаты фильтрации ({len(self.all_data)}):")