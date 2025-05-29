from PyQt5.QtWidgets import QMainWindow, QTableView, QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtCore import QAbstractTableModel, Qt, QThread, pyqtSignal
import pandas as pd
from PyQt5.QtWidgets import QPushButton, QInputDialog, QMessageBox
from PyQt5.QtWidgets import QFileDialog
import os
import requests
import re
from urllib.parse import urlparse
import mimetypes

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    download_result = pyqtSignal(dict)

    def __init__(self, urls, download_dir):
        super().__init__()
        self.urls = urls
        self.download_dir = download_dir
        self._is_running = True
        self.results = {}
        self.downloaded_files = []

    def is_image_url(self, url):
        """Проверяет, ведёт ли URL на изображение"""
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '')
            return content_type.startswith('image/')
        except:
            return False

    def is_image_file(self, filepath):
        """Проверяет, является ли файл изображением"""
        try:
            import imghdr
            return imghdr.what(filepath) is not None
        except:
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            return os.path.splitext(filepath)[1].lower() in image_extensions

    def get_filename(self, url, response, index):
        """Определяет оптимальное имя файла для сохранения изображения"""
        # 1. Из Content-Disposition
        content_disposition = response.headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            try:
                filename = re.findall('filename=(.+)', content_disposition)[0]
                filename = filename.strip('"\'')
                if filename:
                    return self.sanitize_filename(filename)
            except:
                pass

        # 2. Из URL
        parsed_url = urlparse(url)
        url_path = parsed_url.path
        if '/' in url_path:
            filename = url_path.rsplit('/', 1)[-1]
            if '.' in filename:
                return self.sanitize_filename(filename)

        # 3. Из Content-Type
        content_type = response.headers.get('Content-Type', '')
        extension = None
        if content_type:
            extension = mimetypes.guess_extension(content_type.split(';')[0].strip())
        
        # 4. Генерация имени
        base_name = f"image_{index}"
        return f"{base_name}{extension if extension else '.jpg'}"

    def sanitize_filename(self, filename):
        """Очищает имя файла от недопустимых символов"""
        invalid_chars = '<>:"/\\|?*\0'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        filename = filename.strip('. ')
        if len(filename) > 150:
            name, ext = os.path.splitext(filename)
            filename = name[:150 - len(ext)] + ext
        return filename

    def download_single_image(self, url, index):
        """Загружает одно изображение и возвращает результат"""
        result = {
            'url': url,
            'status': 'error',
            'message': 'Неизвестная ошибка',
            'filepath': None
        }
        
        try:
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                result['message'] = "Некорректный URL"
                return result

            if not self.is_image_url(url):
                result['message'] = "URL не ведёт на изображение"
                return result

            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()

            filename = self.get_filename(url, response, index)
            filepath = os.path.join(self.download_dir, filename)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    if not self._is_running:
                        os.remove(filepath)
                        result['message'] = 'Загрузка отменена'
                        return result
                    f.write(chunk)

            if not self.is_image_file(filepath):
                os.remove(filepath)
                result['message'] = 'Файл не является изображением'
                return result

            result.update({
                'status': 'success',
                'message': 'Успешно загружено',
                'filepath': filepath
            })
            return result

        except requests.exceptions.RequestException as e:
            result['message'] = f'Ошибка загрузки: {str(e)}'
            return result
        except Exception as e:
            result['message'] = f'Неожиданная ошибка: {str(e)}'
            return result

    def run(self):
        try:
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)

            total = len(self.urls)
            self.downloaded_files = []

            for i, url in enumerate(self.urls):
                if not self._is_running:
                    break

                result = self.download_single_image(url, i)
                self.results[url] = result
                
                if result['status'] == 'success' and result['filepath']:
                    self.downloaded_files.append(result['filepath'])

                self.progress.emit(int((i + 1) / total * 100))

        except Exception as e:
            self.error.emit(f"Критическая ошибка: {str(e)}")
        finally:
            self.finished.emit()

    def stop(self):
        self._is_running = False
        self.terminate()


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


class DataFrameViewer(QMainWindow):
    def __init__(self, dataframe):
        super().__init__()
        self.setWindowTitle("DataFrame Viewer")
        self.setGeometry(200, 200, 800, 600)
        
        self.download_thread = None
        self.selected_column = None
        self.results_column = None

        # Инициализация таблицы
        self.table = QTableView()
        self.model = PandasModel(dataframe)
        self.table.setModel(self.model)

        # Кнопки
        self.delete_column_button = QPushButton("Удалить колонку")
        self.clear_table_button = QPushButton("Очистить таблицу")
        self.save_csv_button = QPushButton("Записать в CSV файл")
        self.open_csv_button = QPushButton("Открыть CSV")
        self.download_images_button = QPushButton("Скачать изображения")
        self.cancel_download_button = QPushButton("Отменить загрузку")
        self.cancel_download_button.hide()

        # Подключение кнопок
        self.delete_column_button.clicked.connect(self.delete_column)
        self.clear_table_button.clicked.connect(self.clear_table)
        self.save_csv_button.clicked.connect(self.save_to_csv)
        self.open_csv_button.clicked.connect(self.open_csv)
        self.download_images_button.clicked.connect(self.start_image_download)
        self.cancel_download_button.clicked.connect(self.cancel_image_download)

        # Макет
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_column_button)
        button_layout.addWidget(self.clear_table_button)
        button_layout.addWidget(self.save_csv_button)
        button_layout.addWidget(self.open_csv_button)
        button_layout.addWidget(self.download_images_button)
        button_layout.addWidget(self.cancel_download_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.table)
        main_layout.addLayout(button_layout)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def update_dataframe(self, new_dataframe):
        self.model = PandasModel(new_dataframe)
        self.table.setModel(self.model)

    def delete_column(self):
        if not self.model._data.columns.empty:
            column_name, ok = QInputDialog.getItem(
                self, 
                "Удалить колонку",
                "Выберите колонку для удаления:",
                self.model._data.columns.tolist(),
                0,  # Индекс выбранного по умолчанию
                False  # Не редактируемый
            )
            
            if ok and column_name:
                if column_name in self.model._data.columns:
                    self.model._data.drop(columns=[column_name], inplace=True)
                    self.update_dataframe(self.model._data)
        else:
            QMessageBox.warning(self, "Ошибка", "Нет колонок для удаления")

    def clear_table(self):
        self.model._data.drop(self.model._data.index, inplace=True)
        self.update_dataframe(self.model._data)

    def save_to_csv(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как CSV", "", "CSV Files (*.csv);;All Files (*)", options=options
        )
        if file_path:
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
                self.update_dataframe(df)
                QMessageBox.information(self, "Успех", "CSV файл успешно загружен.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{str(e)}")

    def start_image_download(self):
        # Выбор колонки с URL
        self.selected_column, ok = QInputDialog.getItem(
            self, "Выбор колонки", 
            "Выберите колонку с URL изображений:", 
            self.model._data.columns.tolist(), 0, False
        )
        if not ok or not self.selected_column:
            return

        # Ввод имени колонки для результатов
        self.results_column, ok = QInputDialog.getText(
            self, "Колонка для результатов",
            "Введите имя колонки для записи результатов:",
            text="download_results"
        )
        if not ok or not self.results_column:
            return

        # Проверка/создание колонки для результатов
        if self.results_column not in self.model._data.columns:
            self.model._data[self.results_column] = None

        # Выбор папки для сохранения
        download_dir = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения изображений")
        if not download_dir:
            return

        # Подготовка URL
        urls = self.model._data[self.selected_column].dropna().tolist()
        if not urls:
            QMessageBox.warning(self, "Ошибка", "Выбранная колонка не содержит URL изображений.")
            return

        # Запуск потока загрузки
        self.download_thread = DownloadThread(urls, download_dir)
        self.download_thread.finished.connect(self.finalize_download)
        self.download_thread.error.connect(self.download_error)
        self.download_thread.progress.connect(self.update_progress)
        
        self.download_images_button.hide()
        self.cancel_download_button.show()
        self.download_thread.start()

    def finalize_download(self):
        """Записывает все результаты в DataFrame после завершения загрузки"""
        try:
            if not hasattr(self.download_thread, 'results'):
                return

            # Записываем все результаты
            for url, result in self.download_thread.results.items():
                mask = self.model._data[self.selected_column] == url
                if result['status'] == 'success':
                    self.model._data.loc[mask, self.results_column] = result['filepath']
                else:
                    self.model._data.loc[mask, self.results_column] = result['message']

            # Обновляем отображение
            self.model.layoutChanged.emit()

            # Показываем статистику
            success = sum(1 for r in self.download_thread.results.values() if r['status'] == 'success')
            total = len(self.download_thread.results)
            QMessageBox.information(
                self, "Завершено", 
                f"Загрузка завершена.\nУспешно: {success}\nОшибки: {total - success}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении результатов: {str(e)}")
        finally:
            self.reset_download_ui()

    def cancel_image_download(self):
        if self.download_thread is not None and self.download_thread.isRunning():
            reply = QMessageBox.question(
                self, 
                "Отмена загрузки",
                "Вы уверены, что хотите отменить загрузку и удалить скачанные файлы?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.delete_downloaded_files()
                try:
                    self.download_thread.stop()
                except AttributeError:
                    pass  # Если поток уже завершился
                
                # Помечаем отмененные загрузки
                if hasattr(self, 'selected_column') and hasattr(self, 'results_column'):
                    if self.selected_column in self.model._data.columns:
                        urls = list(getattr(self.download_thread, 'results', {}).keys())
                        mask = self.model._data[self.selected_column].isin(urls)
                        self.model._data.loc[mask, self.results_column] = "Загрузка отменена"
                        self.model.layoutChanged.emit()
            
            self.reset_download_ui()

    def delete_downloaded_files(self):
        """Удаляет все скачанные файлы"""
        if hasattr(self.download_thread, 'downloaded_files'):
            for filepath in self.download_thread.downloaded_files:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось удалить файл {filepath}: {str(e)}")

    def update_progress(self, progress):
        self.setWindowTitle(f"DataFrame Viewer - Загрузка: {progress}%")

    def download_error(self, error_msg):
        QMessageBox.warning(self, "Ошибка загрузки", error_msg)

    def reset_download_ui(self):
        self.setWindowTitle("DataFrame Viewer")
        self.download_images_button.show()
        self.cancel_download_button.hide()
        self.download_thread = None