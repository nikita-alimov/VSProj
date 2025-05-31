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
from DataProcessor import DataProcessor  # Импортируем модуль обработки данных

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
        self.apply_styles()
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
        self.drop_empty_button = QPushButton("Удалить строки с пустыми значениями")
        self.process_data_button = QPushButton("Обработать данные")
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
        self.process_data_button.clicked.connect(self.open_data_processor)
        self.drop_empty_button.clicked.connect(self.drop_empty_rows)

        # Макет
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.delete_column_button)
        button_layout.addWidget(self.clear_table_button)
        button_layout.addWidget(self.drop_empty_button)
        button_layout.addWidget(self.process_data_button)  # Добавляем в существующий layout
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

    def apply_styles(self):
        """Применить стили к интерфейсу."""
        self.setStyleSheet("""
            QDialog, QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }

            QLineEdit, QTextEdit, QComboBox {
                        background-color: #252526;
                        color: #d4d4d4;
                        border: 1px solid #3c3c3c;
                        border-radius: 4px;
                        padding: 4px;
                    }

            QPushButton {
                background-color: #007acc;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }

            QPushButton:hover {
                background-color: #005f9e;
            }

            QPushButton:pressed {
                background-color: #004a7c;
            }

            QTextEdit {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px;
            }

            QComboBox {
                background-color: #252526;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 4px;
            }

            QComboBox QAbstractItemView {
                background-color: #1e1e1e;
                color: #d4d4d4;
                selection-background-color: #007acc;
            }

            QMenuBar {
                background-color: #2d2d2d;
                color: #d4d4d4;
            }

            QMenuBar::item {
                background-color: #2d2d2d;
                color: #d4d4d4;
            }

            QMenuBar::item:selected {
                background-color: #007acc;
            }

            QMenu {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }

            QMenu::item:selected {
                background-color: #007acc;
            }

            QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 14px;  
            margin: 0px 3px 0px 3px;
            border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #5a5a5a;  
                min-height: 14px;
                border-radius: 7px;  
                margin-top: 14px;  /* Отступ сверху для верхней кнопки */
                margin-bottom: 14px;  /* Отступ снизу для нижней кнопки */
            }

            QScrollBar::handle:vertical:hover {
                background-color: #787878;  
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background-color: #3c3c3c;  /* Темный фон для кнопок */
                height: 14px;  /* Высота кнопок */
                subcontrol-origin: margin;
                border-radius: 1px;  /* Закругленные края */
            }

            QScrollBar::add-line:vertical {
                subcontrol-position: bottom;  /* Позиция кнопки вниз */
            }

            QScrollBar::sub-line:vertical {
                subcontrol-position: top;  /* Позиция кнопки вверх */
            }

            QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
                background-color: #5a5a5a;  /* Более светлый серый при наведении */
            }

            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;  /* Убираем фон между ползунком и краями */
            }

            QInputDialog, QDialog {
            max-width: 600px;
            }
            QInputDialog QLineEdit, QInputDialog QComboBox {
                min-width: 300px;
                max-width: 500px;
            }      
            /* --- Стили для таблиц --- */
            QTableView, QTableWidget {
                background-color: #232323;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                gridline-color: #444444;
                selection-background-color: #264f78;
                selection-color: #ffffff;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                padding: 4px;
                font-weight: bold;
            }
            QTableCornerButton::section {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
            }
            QTableView QTableCornerButton::section, QTableWidget QTableCornerButton::section {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
            }
            QTableView::item:selected, QTableWidget::item:selected {
                background-color: #264f78;
                color: #ffffff;
            }
            QTableView::item, QTableWidget::item {
                padding: 4px;
            }                       
        """)

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

    def drop_empty_rows(self):
        if not self.model._data.columns.empty:
            column_name, ok = QInputDialog.getItem(
                self, 
                "Удалить строки с пустыми значениями",
                "Выберите колонку для проверки:",
                self.model._data.columns.tolist(),
                0,  # Индекс выбранного по умолчанию
                False  # Не редактируемый
            )
            
            if ok and column_name:
                initial_count = len(self.model._data)
                # Сохраняем копию исходного DataFrame для сравнения
                original_df = self.model._data.copy()
                
                # Удаляем строки с пустыми значениями (NaN, None или пустые строки)
                self.model._data.dropna(subset=[column_name], inplace=True)
                
                # Также удаляем строки с пустыми строками, если колонка строковая
                if pd.api.types.is_string_dtype(self.model._data[column_name]):
                    self.model._data = self.model._data[
                        self.model._data[column_name].astype(str).str.strip() != ''
                    ]
                
                # Сбрасываем индекс, чтобы нумерация была последовательной
                self.model._data.reset_index(drop=True, inplace=True)
                
                removed_count = initial_count - len(self.model._data)
                self.update_dataframe(self.model._data)
                
                if removed_count > 0:
                    QMessageBox.information(
                        self, 
                        "Готово", 
                        f"Удалено {removed_count} строк с пустыми значениями в колонке '{column_name}'.\n"
                        f"Индексы строк были сброшены."
                    )
                else:
                    QMessageBox.information(
                        self,
                        "Нет изменений",
                        f"В колонке '{column_name}' не найдено пустых значений."
                    )
        else:
            QMessageBox.warning(self, "Ошибка", "Нет колонок для проверки")

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

    def handle_processed_data(self, processed_df):
        """Обрабатывает результат работы модуля"""
        # Варианты действий с обработанными данными:
        actions = [
            "Заменить исходные данные", 
            "Добавить как новые колонки",
            "Создать новый DataFrame"
        ]
        
        action, ok = QInputDialog.getItem(
            self,
            "Действие с результатом",
            "Выберите как сохранить обработанные данные:",
            actions,
            0, False
        )
        
        if not ok:
            return
            
        if action == "Заменить исходные данные":
            # Заменяем текущий DataFrame
            self.update_dataframe(processed_df)
        elif action == "Добавить как новые колонки":
            # Объединяем с существующими данными
            new_df = pd.concat([self.model._data, processed_df], axis=1)
            self.update_dataframe(new_df)
        else:  # "Создать новый DataFrame"
            # Создаем новый просмотрщик
            new_viewer = DataFrameViewer(processed_df)
            new_viewer.show()

    def open_data_processor(self):
        # Получаем текущие данные из модели
        df = self.model._data
        
        # Выбираем колонку для обработки
        column, ok = QInputDialog.getItem(
            self,
            "Выбор колонки",
            "Выберите колонку для обработки:",
            df.columns.tolist(),
            0, False
        )
        
        if not ok or not column:
            return
            
        # Получаем данные выбранной колонки
        raw_data = df[column].tolist()
        selection = self.table.selectionModel()
        selected_rows = [index.row() for index in selection.selectedRows()]
        
        if selected_rows:
            # Предложить выбор - обработать все или только выделенное
            choice = QMessageBox.question(
                self,
                "Выбор данных",
                "Обработать выделенные строки или всю колонку?",
                # "Выделенные|Всю колонку",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if choice == QMessageBox.Yes:
                raw_data = [self.model._data.iloc[row][column] for row in selected_rows]

        # Создаем и настраиваем модуль обработки
        processor = DataProcessor(raw_data, self)  # Передаем self как parent
        processor.setWindowTitle(f"Обработка данных: {column}")
        
        # Подключаем сигнал завершения обработки
        processor.processing_finished.connect(self.handle_processed_data)
        processor.exec_()
