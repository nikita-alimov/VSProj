from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QLabel, QSpinBox

class SliceInputDialog(QDialog):
    def __init__(self, max_index, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Параметры извлечения данных")

        # Макет диалога
        layout = QVBoxLayout(self)

        # Поле для ввода начала среза
        self.start_label = QLabel("Начальная строка (0-based):", self)
        self.start_input = QSpinBox(self)
        self.start_input.setRange(0, max_index)
        layout.addWidget(self.start_label)
        layout.addWidget(self.start_input)

        # Поле для ввода конца среза
        self.end_label = QLabel("Конечная строка (0-based, включительно):", self)
        self.end_input = QSpinBox(self)
        self.end_input.setRange(0, max_index)
        self.end_input.setValue(max_index)
        layout.addWidget(self.end_label)
        layout.addWidget(self.end_input)

        # Поле для ввода имени поля
        self.field_label = QLabel("Название поля для сохранения данных:", self)
        self.field_input = QLineEdit(self)
        layout.addWidget(self.field_label)
        layout.addWidget(self.field_input)

        # Кнопки OK и Cancel
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_values(self):
        """Возвращает значения, введенные пользователем."""
        return self.start_input.value(), self.end_input.value(), self.field_input.text()