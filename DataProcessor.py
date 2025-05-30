from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QInputDialog, QDialog, QGroupBox, QComboBox, QCheckBox, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
import pandas as pd
import re

class DataProcessor(QDialog):
    processing_finished = pyqtSignal(pd.DataFrame)
    
    def __init__(self, raw_data_list, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.raw_data = raw_data_list
        self.processed_data = []
        self.column_names = []
        self.current_columns = 1  # Текущее количество колонок
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("Data Processing Module")
        self.setMinimumSize(1200, 900)

        main_layout = QHBoxLayout()

        # Левая панель - обработка данных
        left_panel = QVBoxLayout()

        # Группа для regex операций
        regex_group = QGroupBox("Операции с regex")
        regex_layout = QVBoxLayout()

        # Комбобокс с типами regex операций
        self.regex_type_combo = QComboBox()
        self.regex_type_combo.addItems([
            "Найти все совпадения", 
            "Извлечь группы", 
            "Удалить совпадения",
            "Найти итерационные совпадения"
        ])
        regex_layout.addWidget(QLabel("Тип операци regex:"))
        regex_layout.addWidget(self.regex_type_combo)

        # Поле для ввода regex
        self.regex_edit = QLineEdit()
        self.regex_edit.setPlaceholderText("Введите regex выражение, пример: (\w+)\s(\d+)")
        regex_layout.addWidget(QLabel("Regex выражение:"))
        regex_layout.addWidget(self.regex_edit)

        # Область для выбора колонок
        self.columns_scroll = QScrollArea()
        self.columns_widget = QWidget()
        self.columns_layout = QHBoxLayout()
        self.columns_widget.setLayout(self.columns_layout)
        self.columns_scroll.setWidget(self.columns_widget)
        self.columns_scroll.setWidgetResizable(True)
        self.columns_scroll.setFixedHeight(40)
        regex_layout.addWidget(QLabel("Применить к колонкам:"))
        regex_layout.addWidget(self.columns_scroll)

        # Кнопки действий
        btn_layout = QHBoxLayout()
        self.preview_btn = QPushButton("Предпросмотр изменений")
        self.preview_btn.clicked.connect(self.preview_changes)
        btn_layout.addWidget(self.preview_btn)

        self.apply_btn = QPushButton("Применить изменения")
        self.apply_btn.clicked.connect(self.apply_processing)
        btn_layout.addWidget(self.apply_btn)

        self.split_btn = QPushButton("Разделить на колонки")
        self.split_btn.clicked.connect(self.split_into_columns)
        btn_layout.addWidget(self.split_btn)

        regex_layout.addLayout(btn_layout)
        regex_group.setLayout(regex_layout)
        left_panel.addWidget(regex_group)

        # Таблицы для отображения данных
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(10)
        
        # Таблица с оригинальными данными
        original_table_group = QGroupBox("Исходные данные")
        original_table_layout = QVBoxLayout()
        self.table_original = QTableWidget()
        self.table_original.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        original_table_layout.addWidget(self.table_original)
        original_table_group.setLayout(original_table_layout)
        original_table_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Таблица с обработанными данными
        processed_table_group = QGroupBox("Обработанные данные")
        processed_table_layout = QVBoxLayout()
        self.table_processed = QTableWidget()
        self.table_processed.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        processed_table_layout.addWidget(self.table_processed)
        processed_table_group.setLayout(processed_table_layout)
        processed_table_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        tables_layout.addWidget(original_table_group, stretch=1)
        tables_layout.addWidget(processed_table_group, stretch=1)
        left_panel.addLayout(tables_layout, stretch=1)
        

        # Правая панель - справка по regex
        right_panel = QVBoxLayout()
        help_group = QGroupBox("Помощь по regex")
        help_layout = QVBoxLayout()
        
        # Пресеты regex
        presets_group = QGroupBox("Обычные пресеты")
        presets_layout = QVBoxLayout()
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "Email Extraction - r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'",
            "Phone Numbers - r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4})'",
            "URLs - r'(https?://[^\s]+)'",
            "Dates (MM/DD/YYYY) - r'(\d{2}/\d{2}/\d{4})'",
            "IP Addresses - r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'"
        ])
        self.preset_combo.setMaximumWidth(200)
        self.preset_combo.currentTextChanged.connect(self.load_preset)
        presets_layout.addWidget(QLabel("Пресеты Regex:"))
        presets_layout.addWidget(self.preset_combo)
        
        self.use_preset_btn = QPushButton("Использовать пресет")
        self.use_preset_btn.clicked.connect(self.use_preset)
        self.use_preset_btn.setMaximumWidth(180)
        presets_layout.addWidget(self.use_preset_btn)
        
        presets_group.setLayout(presets_layout)
        help_layout.addWidget(presets_group)
        
        # Справка по regex
        regex_help = QTextEdit()
        regex_help.setReadOnly(True)
        regex_help.setHtml("""
        <h2>Regex быстрый обзор</h2>
        <h3>Базовые операции:</h3>
        <ul>
            <li><b>.</b> - Любой символ кроме новой строки</li>
            <li><b>\w</b> - Словествный символ (a-z, A-Z, 0-9, _)</li>
            <li><b>\d</b> - Цифры (0-9)</li>
            <li><b>\s</b> - Пробелы (пробелы, табуляции, новая строка)</li>
            <li><b>[abc]</b> - Любой из a, b, или c</li>
            <li><b>[^abc]</b> - Не a, b, или c</li>
        </ul>
        
        <h3>Модификаторы множественности:</h3>
        <ul>
            <li><b>*</b> - 0 или более</li>
            <li><b>+</b> - 1 или более</li>
            <li><b>?</b> - 0 или 1</li>
            <li><b>n</b> - Точно n раз</li>
            <li><b>{n,}</b> - n или более раз</li>
            <li><b>{n,m}</b> - Между n и m раз</li>
        </ul>
        
        <h3>Типы операций:</h3>
        <ul>
            <li><b>Найти все совпадения</b> - Найти все совпадения в тексте</li>
            <li><b>Извлечь группы</b> - Извлеч захваченные группы</li>
            <li><b>Удалить совпадения</b> - Удалить найденные вхождения</li>
            <li><b>Найти итерационные совпадения</b> - Найти все вхождения по группам</li>
        </ul>
        """)
        
        help_layout.addWidget(regex_help)
        help_group.setLayout(help_layout)
        help_group.setMaximumWidth(380)
        right_panel.addWidget(help_group, stretch=1)
        
        main_layout.addLayout(left_panel, stretch=10)
        main_layout.addLayout(right_panel, stretch=1)
        self.setLayout(main_layout)

        self.load_raw_data()
        self.update_column_selection()

    def load_preset(self, text):
        # Извлекаем regex из текста пресета
        match = re.search(r" - (r'.+')$", text)
        if match:
            self.regex_edit.setText(match.group(1))

    def use_preset(self):
        # Просто устанавливаем выбранный пресет
        self.load_preset(self.preset_combo.currentText())

    def update_column_selection(self):
        # Очищаем текущие чекбоксы
        for i in reversed(range(self.columns_layout.count())): 
            self.columns_layout.itemAt(i).widget().setParent(None)
        
        # Добавляем чекбоксы для каждой колонки
        for col in range(self.table_processed.columnCount()):
            col_name = self.table_processed.horizontalHeaderItem(col).text()
            cb = QCheckBox(col_name)
            cb.setChecked(True)
            self.columns_layout.addWidget(cb)

    def load_raw_data(self):
        self.table_original.setRowCount(len(self.raw_data))
        self.table_original.setColumnCount(1)
        self.table_original.setHorizontalHeaderLabels(["Original Data"])
        
        for i, item in enumerate(self.raw_data):
            item = str(item) if item is not None else ""
            self.table_original.setItem(i, 0, QTableWidgetItem(item))
        
        self.table_original.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        # Инициализируем processed_data с оригинальными данными
        self.processed_data = [[str(item)] if item is not None else [""] for item in self.raw_data]
        self.update_processed_table()

    def get_selected_columns(self):
        selected = []
        for i in range(self.columns_layout.count()):
            cb = self.columns_layout.itemAt(i).widget()
            if cb.isChecked():
                selected.append(i)
        return selected

    def preview_changes(self):
        pattern = self.regex_edit.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Warning", "Please enter a regex pattern!")
            return

        try:
            regex = re.compile(pattern)
        except re.error as e:
            QMessageBox.warning(self, "Error", f"Invalid regex pattern!\n{str(e)}")
            return

        operation = self.regex_type_combo.currentText()
        selected_cols = self.get_selected_columns()
        
        if not selected_cols:
            QMessageBox.warning(self, "Warning", "Please select at least one column!")
            return

        # Создаем копию текущих данных
        new_data = [row.copy() for row in self.processed_data]
        
        for col in selected_cols:
            for row in range(len(new_data)):
                text = new_data[row][col] if col < len(new_data[row]) else ""
                
                if operation == "Find All Matches":
                    matches = regex.findall(text)
                    if matches:
                        if isinstance(matches[0], tuple):
                            # Для групп объединяем все найденные группы
                            new_text = " ".join([" ".join(filter(None, m)) for m in matches])
                        else:
                            new_text = " ".join(matches)
                        new_data[row][col] = new_text
                    else:
                        new_data[row][col] = ""
                
                elif operation == "Extract Groups":
                    match = regex.search(text)
                    if match:
                        if match.groups():
                            new_text = " ".join(filter(None, match.groups()))
                            new_data[row][col] = new_text
                        else:
                            new_data[row][col] = match.group()
                    else:
                        new_data[row][col] = ""
                
                elif operation == "Remove Matches":
                    new_data[row][col] = regex.sub("", text)
                
                elif operation == "Find Iter Matches":
                    matches = list(regex.finditer(text))
                    if matches:
                        new_text = " ".join([m.group() for m in matches])
                        new_data[row][col] = new_text
                    else:
                        new_data[row][col] = ""

        # Временно обновляем таблицу для предпросмотра
        self.update_table_preview(new_data)

    def update_table_preview(self, data):
        """Обновляет таблицу для предпросмотра без изменения processed_data"""
        rows = len(data)
        cols = max(len(row) for row in data) if data else 0
        
        self.table_processed.setRowCount(rows)
        self.table_processed.setColumnCount(cols)
        
        # Сохраняем текущие заголовки
        current_headers = []
        for i in range(self.table_processed.columnCount()):
            header = self.table_processed.horizontalHeaderItem(i)
            current_headers.append(header.text() if header else f"Column {i+1}")
        
        # Устанавливаем заголовки
        for i in range(cols):
            if i < len(current_headers):
                self.table_processed.setHorizontalHeaderItem(i, QTableWidgetItem(current_headers[i]))
            else:
                self.table_processed.setHorizontalHeaderItem(i, QTableWidgetItem(f"Column {i+1}"))
        
        # Заполняем данные
        for row in range(rows):
            for col in range(cols):
                value = data[row][col] if col < len(data[row]) else ""
                self.table_processed.setItem(row, col, QTableWidgetItem(str(value)))
        
        self.table_processed.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def update_processed_table(self):
        """Обновляет таблицу с обработанными данными из self.processed_data"""
        rows = len(self.processed_data)
        cols = max(len(row) for row in self.processed_data) if self.processed_data else 0
        
        self.table_processed.setRowCount(rows)
        self.table_processed.setColumnCount(cols)
        
        # Устанавливаем заголовки
        for i in range(cols):
            if i < len(self.column_names):
                self.table_processed.setHorizontalHeaderItem(i, QTableWidgetItem(self.column_names[i]))
            else:
                self.table_processed.setHorizontalHeaderItem(i, QTableWidgetItem(f"Column {i+1}"))
        
        # Заполняем данные
        for row in range(rows):
            for col in range(cols):
                value = self.processed_data[row][col] if col < len(self.processed_data[row]) else ""
                self.table_processed.setItem(row, col, QTableWidgetItem(str(value)))
        
        self.table_processed.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.update_column_selection()

    def split_into_columns(self):
        # Определяем, какая колонка выбрана для разделения
        selected_col = None
        selection = self.table_processed.selectedItems()
        
        if selection:
            selected_col = selection[0].column()
        
        if selected_col is not None:
            # Разделяем выбранную колонку
            col_name = self.table_processed.horizontalHeaderItem(selected_col).text()
            data_to_split = []
            for row in self.processed_data:
                if selected_col < len(row):
                    data_to_split.append(str(row[selected_col]))
                else:
                    data_to_split.append("")
        else:
            # Разделяем оригинальные данные
            data_to_split = [str(item) if item is not None else "" for item in self.raw_data]
            selected_col = 0  # Будем заменять первую колонку

        if not data_to_split or all(not s for s in data_to_split):
            QMessageBox.warning(self, "Warning", "No data to split!")
            return

        delimiter, ok = QInputDialog.getText(
            self,
            "Delimiter",
            "Enter delimiter character or string:",
            QLineEdit.Normal,
            ","
        )
        if not ok or delimiter == "":
            QMessageBox.warning(self, "Warning", "Delimiter not specified!")
            return

        max_groups = 0
        split_data = []
        for item in data_to_split:
            parts = item.split(delimiter)
            split_data.append(parts)
            if len(parts) > max_groups:
                max_groups = len(parts)

        if max_groups < 2:
            QMessageBox.warning(self, "Warning", "Data cannot be split into multiple columns with the selected delimiter!")
            return

        # Получаем имена для новых колонок
        new_columns = []
        for i in range(max_groups):
            name, ok = QInputDialog.getText(
                self,
                "Column Name",
                f"Enter name for column {i + 1}:",
                QLineEdit.Normal,
                f"Column_{i + 1}"
            )
            if ok and name:
                new_columns.append(name)
            else:
                new_columns.append(f"Column_{i + 1}")

        # Обновляем processed_data
        new_processed_data = []
        for row_idx, row in enumerate(self.processed_data):
            new_row = row.copy()
            
            # Если разделяем существующую колонку, заменяем ее
            if selected_col is not None and selected_col < len(new_row):
                # Удаляем оригинальную колонку
                del new_row[selected_col]
                # Вставляем новые колонки
                for i, part in enumerate(split_data[row_idx]):
                    new_row.insert(selected_col + i, part)
                # Добавляем пустые значения, если нужно
                while len(new_row) < selected_col + max_groups:
                    new_row.append("")
            else:
                # Просто добавляем новые колонки
                new_row = split_data[row_idx]
            
            new_processed_data.append(new_row)

        self.processed_data = new_processed_data
        
        # Обновляем column_names
        if selected_col is not None and selected_col < len(self.column_names):
            # Удаляем оригинальное имя колонки
            del self.column_names[selected_col]
            # Вставляем новые имена
            for i, name in enumerate(new_columns):
                self.column_names.insert(selected_col + i, name)
        else:
            # Просто используем новые имена
            self.column_names = new_columns

        self.update_processed_table()

    def apply_processing(self):
        if not self.processed_data:
            QMessageBox.warning(self, "Warning", "No processed data available!")
            return None

        # Создаем DataFrame из processed_data
        if self.table_processed.columnCount() > 1:
            data_dict = {}
            for col in range(self.table_processed.columnCount()):
                col_name = self.table_processed.horizontalHeaderItem(col).text()
                col_data = []
                for row in range(self.table_processed.rowCount()):
                    item = self.table_processed.item(row, col)
                    col_data.append(item.text() if item else "")
                data_dict[col_name] = col_data
            df = pd.DataFrame(data_dict)
        else:
            df = pd.DataFrame({
                "Processed_Data": [
                    self.table_processed.item(row, 0).text() if self.table_processed.item(row, 0) else ""
                    for row in range(self.table_processed.rowCount())
                ]
            })

        self.processing_finished.emit(df)
        self.close()