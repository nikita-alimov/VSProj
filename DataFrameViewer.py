from PyQt5.QtWidgets import QMainWindow, QTableView, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import QAbstractTableModel, Qt, QThread, pyqtSignal
import pandas as pd
from PyQt5.QtWidgets import QPushButton, QInputDialog, QMessageBox
from PyQt5.QtWidgets import QFileDialog
import os
import requests
from urllib.parse import urlparse
import mimetypes

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    file_downloaded = pyqtSignal(str)

    def __init__(self, urls, download_dir):
        super().__init__()
        self.urls = urls
        self.download_dir = download_dir
        self._is_running = True

    def is_image_url(self, url):
        """Проверяет, ведёт ли URL на изображение"""
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '')
            return content_type.startswith('image/')
        except:
            return False
        
    def run(self):
        try:
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)

            total = len(self.urls)
            downloaded = 0
            downloaded_files = []

            for i, url in enumerate(self.urls):
                if not self._is_running:
                    break

                try:
                    if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                        self.error.emit(f"Некорректный URL: {url}")
                        continue

                    # Проверяем, что URL ведёт на изображение
                    if not self.is_image_url(url):
                        self.error.emit(f"URL не ведёт на изображение: {url}")
                        continue

                    response = requests.get(url, stream=True, timeout=10)
                    response.raise_for_status()

                    # Получаем имя файла из URL или Content-Disposition
                    filename = None
                    
                    # Пробуем получить имя из Content-Disposition
                    content_disposition = response.headers.get('Content-Disposition')
                    if content_disposition:
                        parts = content_disposition.split('filename=')
                        if len(parts) > 1:
                            filename = parts[1].strip('"\'')
                    
                    # Если не получили имя из Content-Disposition, пробуем из URL
                    if not filename:
                        parsed_url = urlparse(url)
                        filename = os.path.basename(parsed_url.path)
                    
                    # Если всё ещё нет имени, генерируем
                    if not filename:
                        # Определяем расширение из Content-Type
                        content_type = response.headers.get('Content-Type')
                        extension = mimetypes.guess_extension(content_type) if content_type else '.jpg'
                        filename = f"image_{i}{extension}"

                    filepath = os.path.join(self.download_dir, filename)

                    # Сохраняем изображение
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            if not self._is_running:
                                break
                            f.write(chunk)

                    # Проверяем, что файл действительно изображение
                    if not self.is_image_file(filepath):
                        os.remove(filepath)
                        self.error.emit(f"Загруженный файл не является изображением: {url}")
                        continue

                    downloaded += 1
                    downloaded_files.append(filepath)
                    self.file_downloaded.emit(filepath)
                    self.progress.emit(int((i + 1) / total * 100))

                except Exception as e:
                    self.error.emit(f"Ошибка при загрузке {url}: {str(e)}")

            self.finished.emit()

        except Exception as e:
            self.error.emit(f"Критическая ошибка: {str(e)}")

    def is_image_file(self, filepath):
        """Проверяет, является ли файл изображением"""
        try:
            import imghdr
            return imghdr.what(filepath) is not None
        except:
            # Fallback проверка по расширению
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            return os.path.splitext(filepath)[1].lower() in image_extensions
        
    def stop(self):
        self._is_running = False
        self.terminate()

class DataFrameViewer(QMainWindow):
    def __init__(self, dataframe):
        super().__init__()
        self.setWindowTitle("DataFrame Viewer")
        self.setGeometry(200, 200, 800, 600)

        self.download_thread = None
        self.downloaded_files = []
        # Создаем QTableView и подключаем модель
        self.table = QTableView()
        self.model = PandasModel(dataframe)
        self.table.setModel(self.model)

        # Создаем кнопки
        self.delete_column_button = QPushButton("Удалить колонку")
        self.clear_table_button = QPushButton("Очистить таблицу")
        self.save_csv_button = QPushButton("Записать в CSV файл")
        self.open_csv_button = QPushButton("Открыть CSV")
        self.download_images_button = QPushButton("Скачать изображения")
        self.cancel_download_button = QPushButton("Отменить загрузку")
        self.cancel_download_button.hide()

        self.save_csv_button.clicked.connect(self.save_to_csv)
        self.open_csv_button.clicked.connect(self.open_csv)
        self.download_images_button.clicked.connect(self.start_image_download)
        self.cancel_download_button.clicked.connect(self.cancel_image_download)


        # Подключаем кнопки к методам
        self.delete_column_button.clicked.connect(self.delete_column)
        self.clear_table_button.clicked.connect(self.clear_table)

        # Добавляем кнопки в макет
        layout2 = QHBoxLayout()
        layout2.addWidget(self.delete_column_button)
        layout2.addWidget(self.clear_table_button)
        layout2.addWidget(self.save_csv_button)
        layout2.addWidget(self.open_csv_button)
        layout2.addWidget(self.download_images_button)
        layout2.addWidget(self.cancel_download_button)

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

    def start_image_download(self):
        # Выбираем колонку с URL
        column_name, ok = QInputDialog.getItem(
            self, "Выбор колонки", 
            "Выберите колонку с URL изображений:", 
            self.model._data.columns.tolist(), 0, False
        )
        
        if not ok or not column_name:
            return

        # Проверяем, что в колонке есть URL
        urls = self.model._data[column_name].dropna().tolist()
        if not urls:
            QMessageBox.warning(self, "Ошибка", "Выбранная колонка не содержит URL изображений.")
            return

        # Выбираем папку для сохранения
        download_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения изображений")
        if not download_dir:
            return

        # Создаем и запускаем поток загрузки
        self.download_thread = DownloadThread(urls, download_dir)
        self.download_thread.progress.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.file_downloaded.connect(self.file_downloaded)

        # Меняем кнопки
        self.download_images_button.hide()
        self.cancel_download_button.show()

        self.download_thread.start()

    def cancel_image_download(self):
        if self.download_thread and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self, "Отмена загрузки",
                "Вы уверены, что хотите отменить загрузку? Удалить уже скачанные файлы?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Cancel
            )

            if reply == QMessageBox.Yes:
                # Удаляем скачанные файлы
                for filepath in self.downloaded_files:
                    try:
                        if os.path.exists(filepath):
                            os.remove(filepath)
                    except Exception as e:
                        QMessageBox.warning(self, "Ошибка", f"Не удалось удалить файл {filepath}: {str(e)}")
                self.downloaded_files = []
                self.download_thread.stop()
            elif reply == QMessageBox.No:
                self.download_thread.stop()
            else:
                return

        self.reset_download_ui()

    def update_progress(self, progress):
        self.setWindowTitle(f"DataFrame Viewer - Загрузка: {progress}%")

    def download_finished(self):
        QMessageBox.information(self, "Успех", f"Загрузка завершена. Скачано {len(self.downloaded_files)} изображений.")
        self.reset_download_ui()

    def download_error(self, error_msg):
        QMessageBox.warning(self, "Ошибка загрузки", error_msg)

    def file_downloaded(self, filepath):
        self.downloaded_files.append(filepath)

    def reset_download_ui(self):
        self.setWindowTitle("DataFrame Viewer")
        self.download_images_button.show()
        self.cancel_download_button.hide()
        self.download_thread = None

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