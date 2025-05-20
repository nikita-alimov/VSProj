from PyQt5.QtWidgets import QMainWindow, QTableView, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import QAbstractTableModel, Qt
import pandas as pd
from PyQt5.QtWidgets import QPushButton, QInputDialog, QMessageBox

class DataFrameViewer(QMainWindow):
    def __init__(self, dataframe):
        super().__init__()
        self.setWindowTitle("DataFrame Viewer")
        self.setGeometry(200, 200, 800, 600)

        # Создаем QTableView и подключаем модель
        self.table = QTableView()
        self.model = PandasModel(dataframe)
        self.table.setModel(self.model)

        # Создаем кнопки
        self.delete_column_button = QPushButton("Удалить колонку")
        self.clear_table_button = QPushButton("Очистить таблицу")

        # Подключаем кнопки к методам
        self.delete_column_button.clicked.connect(self.delete_column)
        self.clear_table_button.clicked.connect(self.clear_table)

        # Добавляем кнопки в макет
        layout2 = QHBoxLayout()
        layout2.addWidget(self.delete_column_button)
        layout2.addWidget(self.clear_table_button)

        # Устанавливаем макет
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        layout.addLayout(layout2)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def update_dataframe(self, new_dataframe):
        self.model = PandasModel(new_dataframe)
        self.table.setModel(self.model)

    def delete_column(self):
        column_name, ok = QInputDialog.getText(self, "Удалить колонку", "Введите имя колонки для удаления:")
        if ok:
            if column_name in self.model._data.columns:
                self.model._data.drop(columns=[column_name], inplace=True)
                self.update_dataframe(self.model._data)
            else:
                QMessageBox.warning(self, "Ошибка", f"Колонка '{column_name}' не найдена в датафрейме.")

    def clear_table(self):
        self.model._data.drop(self.model._data.index, inplace=True)
        self.update_dataframe(self.model._data)

class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if not self._data.empty:
                    return self._data.columns[section]
            if orientation == Qt.Vertical:
                if not self._data.empty:
                    return str(self._data.index[section])
        return None