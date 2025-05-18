from PyQt5.QtWidgets import QMainWindow, QTableView, QVBoxLayout, QWidget
from PyQt5.QtCore import QAbstractTableModel, Qt
import pandas as pd

class DataFrameViewer(QMainWindow):
    def __init__(self, dataframe):
        super().__init__()
        self.setWindowTitle("DataFrame Viewer")
        self.setGeometry(200, 200, 800, 600)

        # Создаем QTableView и подключаем модель
        self.table = QTableView()
        self.model = PandasModel(dataframe)
        self.table.setModel(self.model)

        # Устанавливаем макет
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)


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
                return self._data.columns[section]
            if orientation == Qt.Vertical:
                return str(self._data.index[section])
        return None