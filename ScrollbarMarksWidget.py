from PyQt5.QtWidgets import QScrollBar, QWidget
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtCore import Qt, QRect

class ScrollbarMarks(QWidget):
    def __init__(self, scrollbar, parent=None):
        super().__init__(parent)
        self.scrollbar = scrollbar
        self.marks = []  # Список позиций для пометок
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # Сделать виджет прозрачным для событий мыши
        self.setFixedWidth(10)  # Ширина виджета для пометок
        self.buffer = None  # Буфер для хранения отрисованных маркеров

    def set_marks(self, marks):
        """Установить позиции для пометок."""
        if self.marks != marks:  # Перерисовывать только при изменении данных
            self.marks = marks
            self.redraw_buffer()  # Перерисовать буфер
            self.update()  # Обновить виджет

    def redraw_buffer(self):
        """Перерисовать буфер с маркерами."""
        self.buffer = QPixmap(self.width(), self.height())
        self.buffer.fill(Qt.transparent)  # Очистить буфер

        painter = QPainter(self.buffer)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 0, 128))  # Полупрозрачный желтый цвет

        for mark in self.marks:
            rect = QRect(0, mark, self.width(), 1)  # Прямоугольник для каждой пометки
            painter.drawRect(rect)

        painter.end()

    def paintEvent(self, event):
        """Отрисовка буфера на виджете."""
        if self.buffer:
            with QPainter(self) as painter:
                painter.drawPixmap(0, 0, self.buffer)