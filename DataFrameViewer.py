from PyQt5.QtWidgets import QMainWindow, QTableView, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import QAbstractTableModel, Qt
import pandas as pd
from PyQt5.QtWidgets import QPushButton, QInputDialog, QMessageBox
from PyQt5.QtWidgets import QFileDialog
import os

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
        self.save_csv_button = QPushButton("Записать в CSV файл")
        self.open_csv_button = QPushButton("Открыть CSV")

        self.save_csv_button.clicked.connect(self.save_to_csv)
        self.open_csv_button.clicked.connect(self.open_csv)



        # Подключаем кнопки к методам
        self.delete_column_button.clicked.connect(self.delete_column)
        self.clear_table_button.clicked.connect(self.clear_table)

        # Добавляем кнопки в макет
        layout2 = QHBoxLayout()
        layout2.addWidget(self.delete_column_button)
        layout2.addWidget(self.clear_table_button)
        layout2.addWidget(self.save_csv_button)
        layout2.addWidget(self.open_csv_button)

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

    def save_to_csv(self):

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как CSV", "", "CSV Files (*.csv);;All Files (*)", options=options
        )
        if file_path:
            if os.path.exists(file_path):
                reply = QMessageBox.question(
                    self, "Файл существует",
                    "Файл уже существует. Перезаписать?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            try:
                self.model._data.to_csv(file_path, index=False)
                QMessageBox.information(self, "Успех", "Данные успешно сохранены в CSV файл.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{str(e)}")

    def open_csv(self):

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Открыть CSV", "", "CSV Files (*.csv);;All Files (*)", options=options
        )
        if file_path:
            try:
                df = pd.read_csv(file_path)
                if not isinstance(df, pd.DataFrame):
                    raise ValueError("Файл не содержит валидный DataFrame.")
                self.update_dataframe(df)
                QMessageBox.information(self, "Успех", "CSV файл успешно загружен.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{str(e)}")    

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