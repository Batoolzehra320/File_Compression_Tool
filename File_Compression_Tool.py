import sys
import os
import csv
from datetime import datetime


sys.path.append(os.path.dirname(__file__))

from compression_api import HuffmanCompressionAPI
from PyQt5.QtWidgets import (
    QApplication, QLabel, QWidget, QPushButton, QMainWindow, QVBoxLayout,
    QMessageBox, QLineEdit, QSizePolicy, QStackedWidget, QHBoxLayout,
    QFileDialog, QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QToolButton,
    QDialog, QProgressBar, QTextEdit, QGridLayout, QGroupBox
)
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal

USER_FILE = "users.csv"
HISTORY_FILE = "history.csv"

def read_csv(file_path):
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        return []

def write_csv(file_path, data, fieldnames):
    with open(file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def append_history(record: dict):
    fieldnames = ["username", "file_name", "operation", "date_time", "output_path", "original_size", "compressed_size", "compression_ratio"]
    rows = read_csv(HISTORY_FILE)
    rows.append(record)
    write_csv(HISTORY_FILE, rows, fieldnames)

def authenticate(username, password):
    users = read_csv(USER_FILE)
    for user in users:
        if user.get("username") == username and user.get("password") == password:
            return True
    return False

class CompressionWorker(QThread):
    finished_signal = pyqtSignal(object)
    progress_signal = pyqtSignal(int, int, str, str)
    error_signal = pyqtSignal(str)

    def __init__(self, api, operation, input_path, output_path):
        super().__init__()
        self.api = api
        self.operation = operation
        self.input_path = input_path
        self.output_path = output_path

    def run(self):
        try:
            if self.operation == 'compress':
                result = self.api.compress(self.input_path, self.output_path, self.update_progress)
            else:
                result = self.api.decompress(self.input_path, self.output_path, self.update_progress)
            
            self.finished_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))

    def update_progress(self, current, total, stage, filename):
        self.progress_signal.emit(current, total, stage, filename)

class ResultsDialog(QDialog):
    def __init__(self, result, operation_type, parent=None):
        super().__init__(parent)
        self.result = result
        self.operation_type = operation_type
        self.setWindowTitle(f"{operation_type} Results")
        self.setFixedSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        title = QLabel(f"{self.operation_type} Complete")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        status_label = QLabel("✅ Successful" if self.result.success else "❌ Failed")
        status_label.setFont(QFont("Arial", 12))
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet("color: green; font-weight: bold;" if self.result.success else "color: red; font-weight: bold;")
        layout.addWidget(status_label)

        if self.result.success:
            info_layout = QVBoxLayout()
            info_layout.setSpacing(8)
            
            orig_layout = QHBoxLayout()
            orig_layout.addWidget(QLabel("Original Size:"))
            orig_layout.addWidget(QLabel(self.format_bytes(self.result.original_size)))
            orig_layout.addStretch()
            info_layout.addLayout(orig_layout)

            size_layout = QHBoxLayout()
            if hasattr(self.result, 'compressed_size'):
                size_layout.addWidget(QLabel("Compressed Size:"))
                size_layout.addWidget(QLabel(self.format_bytes(self.result.compressed_size)))
            else:
                size_layout.addWidget(QLabel("Decompressed Size:"))
                size_layout.addWidget(QLabel(self.format_bytes(self.result.decompressed_size)))
            size_layout.addStretch()
            info_layout.addLayout(size_layout)

            if hasattr(self.result, 'compressed_size'):
                ratio_layout = QHBoxLayout()
                ratio_layout.addWidget(QLabel("Compression Ratio:"))
                ratio = self.result.compression_ratio
                ratio_label = QLabel(f"{ratio:.2%}")
                ratio_label.setStyleSheet("color: blue; font-weight: bold;")
                ratio_layout.addWidget(ratio_label)
                ratio_layout.addStretch()
                info_layout.addLayout(ratio_layout)

            
            if hasattr(self.result, 'compressed_size'): 
                savings_layout = QHBoxLayout()
                savings_layout.addWidget(QLabel("Space Saved:"))
                savings = 1 - ratio
                savings_label = QLabel(f"{savings:.2%}")
                savings_label.setStyleSheet("color: green; font-weight: bold;" if savings > 0 else "color: orange; font-weight: bold;")
                savings_layout.addWidget(savings_label)
                savings_layout.addStretch()
                info_layout.addLayout(savings_layout)

            time_layout = QHBoxLayout()
            time_layout.addWidget(QLabel("Processing Time:"))
            time_layout.addWidget(QLabel(f"{self.result.processing_time:.2f} seconds"))
            time_layout.addStretch()
            info_layout.addLayout(time_layout)

            layout.addLayout(info_layout)

        else:
            error_label = QLabel(self.result.error_message)
            error_label.setWordWrap(True)
            error_label.setStyleSheet("color: red; padding: 10px;")
            error_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(error_label)

        layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setFixedSize(100, 35)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def format_bytes(self, bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} TB"

class ProgressDialog(QDialog):
    def __init__(self, operation_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{operation_name} in Progress...")
        self.setFixedSize(400, 150)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        self.status_label = QLabel("Starting...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.file_label = QLabel("")
        self.file_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_label)

        self.setLayout(layout)

    def update(self, current, total, stage, filename):
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
        
        self.status_label.setText(f"{stage.title()}...")
        if filename:
            self.file_label.setText(f"File: {os.path.basename(filename)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api = HuffmanCompressionAPI()
        self.current_user = None

        self.setWindowTitle("ZIIPIT - File Compression Tool")
        self.resize(1200, 720)

        self.theme = "dark"

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.build_login_page()
        self.build_main_pages()

        self.stack.setCurrentWidget(self.login_page)

        self.statusBar().showMessage("Ready")

        self.apply_theme()

    def build_login_page(self):
        page = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 20, 0, 20)
        main_layout.setSpacing(18)
        main_layout.addStretch()

        title = QLabel("Welcome To ZIIPIT File Compressor")
        title.setFont(QFont("Times New Roman", 32, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        logo_label = QLabel()
        logo_pix = QPixmap(r"C:\Users\Hp\AppData\Local\Temp\898a6618-5311-4e0c-9958-f75c9105066e_final draft.zip.66e\final draft\backend\WhatsApp Image 2025-11-01 at 01.52.38_1bb347d6.jpg")
        if not logo_pix.isNull():
            logo_pix = logo_pix.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pix)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("""
            QLabel {
                border: 7px solid #051C3D;
                border-radius: 15px;
                background: transparent;
            }
        """)
        main_layout.addWidget(logo_label, alignment=Qt.AlignCenter)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(10)
        form_layout.setAlignment(Qt.AlignCenter)

        self.Username_Input = QLineEdit()
        self.Username_Input.setPlaceholderText("Username")
        self.Username_Input.setFixedSize(280, 38)
        self.Username_Input.setFont(QFont("Arial", 11))
        self.Username_Input.setStyleSheet(self.input_style())
        form_layout.addWidget(self.Username_Input, alignment=Qt.AlignCenter)

        self.Password_Input = QLineEdit()
        self.Password_Input.setPlaceholderText("Password")
        self.Password_Input.setEchoMode(QLineEdit.Password)
        self.Password_Input.setFixedSize(280, 38)
        self.Password_Input.setFont(QFont("Arial", 11))
        self.Password_Input.setStyleSheet(self.input_style())
        form_layout.addWidget(self.Password_Input, alignment=Qt.AlignCenter)

        self.Login_button = QPushButton("Login")
        self.Login_button.setFixedSize(160, 42)
        self.Login_button.setCursor(Qt.PointingHandCursor)
        self.Login_button.clicked.connect(self.attempt_login)
        self.Login_button.setStyleSheet(self.primary_button_style())
        form_layout.addWidget(self.Login_button, alignment=Qt.AlignCenter)

        signup_btn = QPushButton("Don't have an account? Sign Up")
        signup_btn.setFlat(True)
        signup_btn.setCursor(Qt.PointingHandCursor)
        signup_btn.setFont(QFont("Times New Roman", 10))
        signup_btn.setStyleSheet("""
            QPushButton { color: #0A2A66; background: transparent; border: none; }
            QPushButton:hover { color: #001A44; text-decoration: underline; }
        """)
        signup_btn.clicked.connect(self.open_signup)
        form_layout.addWidget(signup_btn, alignment=Qt.AlignCenter)

        main_layout.addLayout(form_layout)
        main_layout.addStretch()

        page.setLayout(main_layout)
        self.login_page = page
        self.stack.addWidget(page)

    def build_main_pages(self):
        self.app_container = QWidget()
        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        navbar = QFrame()
        navbar.setFixedHeight(64)
        navbar.setStyleSheet(self.navbar_style())
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(18, 8, 18, 8)
        nav_layout.setSpacing(12)

        self.home_button = QPushButton("Home")
        self.compress_button = QPushButton("Compress")
        self.decompress_button = QPushButton("Decompress")
        self.history_button = QPushButton("History")
        self.theme_toggle = QToolButton()
        self.theme_toggle.setText("🌙")
        self.theme_toggle.setCursor(Qt.PointingHandCursor)
        self.logout_button = QPushButton("Logout")

        for b in (self.home_button, self.compress_button, self.decompress_button, self.history_button):
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(self.nav_button_style())

        self.theme_toggle.setStyleSheet(self.theme_toggle_style())
        self.logout_button.setStyleSheet(self.nav_button_style())

        self.home_button.clicked.connect(lambda: self.switch_page("Home"))
        self.compress_button.clicked.connect(lambda: self.switch_page("Compress"))
        self.decompress_button.clicked.connect(lambda: self.switch_page("Decompress"))
        self.history_button.clicked.connect(lambda: self.switch_page("History"))
        self.logout_button.clicked.connect(self.logout)
        self.theme_toggle.clicked.connect(self.toggle_theme)

        nav_layout.addWidget(self.home_button)
        nav_layout.addWidget(self.compress_button)
        nav_layout.addWidget(self.decompress_button)
        nav_layout.addWidget(self.history_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.theme_toggle)
        nav_layout.addWidget(self.logout_button)
        navbar.setLayout(nav_layout)

        header = QFrame()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(18, 12, 18, 12)
        header.setStyleSheet("background: #0E8BA5;")
        logo = QLabel()
        logo_pix = QPixmap("C:/Users/Hp/Downloads/Compressor Logo.png")
        if not logo_pix.isNull():
            logo.setPixmap(logo_pix.scaled(86, 86, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(86, 86)
        title = QLabel("ZIIPIT - File Compressor")
        title.setFont(QFont("Times New Roman", 34, QFont.Bold))
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_layout.addWidget(logo)
        header_layout.addSpacing(12)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header.setLayout(header_layout)

        self.pages = QStackedWidget()

        home_page = QWidget()
        h_layout = QVBoxLayout()
        h_layout.addStretch()
        welcome_lbl = QLabel("Welcome to ZIIPIT Compressor Dashboard")
        welcome_lbl.setFont(QFont("Arial", 24, QFont.Bold))
        welcome_lbl.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(welcome_lbl)
        h_layout.addStretch()
        home_page.setLayout(h_layout)

        compress_page = QWidget()
        c_layout = QVBoxLayout()
        c_layout.addStretch()
        self.compress_select_btn = QPushButton("Select File to Compress")
        self.compress_select_btn.setFixedSize(320, 110)
        self.compress_select_btn.setStyleSheet(self.large_action_style())
        self.compress_select_btn.setCursor(Qt.PointingHandCursor)
        self.compress_select_btn.clicked.connect(self.open_compress_file)
        c_layout.addWidget(self.compress_select_btn, alignment=Qt.AlignCenter)
        c_layout.addStretch()
        compress_page.setLayout(c_layout)

        decompress_page = QWidget()
        d_layout = QVBoxLayout()
        d_layout.addStretch()
        self.decompress_select_btn = QPushButton("Select File to Decompress")
        self.decompress_select_btn.setFixedSize(320, 110)
        self.decompress_select_btn.setStyleSheet(self.large_action_style())
        self.decompress_select_btn.setCursor(Qt.PointingHandCursor)
        self.decompress_select_btn.clicked.connect(self.open_decompress_file)
        d_layout.addWidget(self.decompress_select_btn, alignment=Qt.AlignCenter)
        d_layout.addStretch()
        decompress_page.setLayout(d_layout)

        history_page = QWidget()
        hist_layout = QVBoxLayout()
        hist_layout.setContentsMargins(16, 16, 16, 16)
        hist_layout.setSpacing(10)

        top_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedSize(120, 36)
        refresh_btn.setStyleSheet(self.primary_button_style())
        refresh_btn.clicked.connect(self.load_history)

        clear_btn = QPushButton("Clear History")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFixedSize(120, 36)
        clear_btn.setStyleSheet(self.secondary_button_style())
        clear_btn.clicked.connect(self.clear_history_with_confirm)

        top_row.addStretch()
        top_row.addWidget(refresh_btn)
        top_row.addSpacing(8)
        top_row.addWidget(clear_btn)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "Username", "File Name", "Operation", "Date/Time", 
            "Output Path", "Original Size", "Compressed Size", "Compression Ratio"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)

        hist_layout.addLayout(top_row)
        hist_layout.addWidget(self.history_table)
        history_page.setLayout(hist_layout)

        self.pages.addWidget(home_page)
        self.pages.addWidget(compress_page)
        self.pages.addWidget(decompress_page)
        self.pages.addWidget(history_page)

        v.addWidget(navbar)
        v.addWidget(header)
        v.addWidget(self.pages)
        v.setStretchFactor(self.pages, 1)
        self.app_container.setLayout(v)

        self.stack.addWidget(self.app_container)

    def input_style(self):
        return """
            QLineEdit {
                background: rgba(255,255,255,0.75);
                padding: 8px;
                border-radius: 8px;
                border: none;
            }
            QLineEdit:focus {
                outline: none;
                border: 2px solid rgba(14,139,165,0.9);
            }
        """

    def primary_button_style(self):
        return """
            QPushButton {
                background: rgba(255,255,255,0.35);
                color: white;
                padding: 8px;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.50);
            }
        """

    def secondary_button_style(self):
        return """
            QPushButton {
                background: rgba(255,255,255,0.18);
                color: white;
                padding: 6px;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.30);
            }
        """

    def nav_button_style(self):
        return """
        QPushButton {
            background: transparent;
            color: white;
            font-size: 15px;
            padding: 8px 16px;
            border-radius: 8px;
            border: none;
        }
        QPushButton:hover {
            background-color: rgba(14,139,165,0.18);
        }
        QPushButton:checked {
            background-color: rgba(14,139,165,0.28);
        }
    """

    def large_action_style(self):
        return """
        QPushButton {
            background: rgba(255,255,255,0.35);
            color: #051C3D;
            padding: 12px;
            border-radius: 14px;
            font-weight: bold;
            font-size: 18px;
        }
        QPushButton:hover {
            background-color: #0E8BA5;
            color: white;
        }
    """

    def navbar_style(self):
        return """
            QFrame {
                background-color: #0A6C7F;
                border-bottom: 2px solid #044E5C;
            }
        """

    def theme_toggle_style(self):
        return """
            QToolButton {
                background: transparent;
                border: none;
                font-size: 18px;
                padding: 6px 10px;
            }
            QToolButton:hover {
                background-color: rgba(255,255,255,0.08);
                border-radius: 8px;
            }
        """

    def apply_theme(self):
        if self.theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:1,
                        stop:0 #08304F,
                        stop:0.6 #0A6C7F,
                        stop:1 #95F2E8
                    );
                }
            """)
            self.theme_toggle.setText("🌙")
            self.statusBar().setStyleSheet("background: rgba(0,0,0,0.12); color: white;")
        else:
           self.setStyleSheet("""
    QMainWindow {
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 #E6F7FF,
            stop:0.6 #BAE7FF,
            stop:1 #91D5FF
        );
    }
""")
        self.theme_toggle.setText("☀️")
        self.statusBar().setStyleSheet("background: rgba(255,255,255,0.6); color: black;")

    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.apply_theme()

    def attempt_login(self):
        username = self.Username_Input.text().strip()
        password = self.Password_Input.text().strip()
        if not username or not password:
            QMessageBox.critical(self, "Error", "Please enter both username and password.")
            return

        if authenticate(username, password):
            self.current_user = username
            QMessageBox.information(self, "Login Success", f"Welcome, {username}!")
            self.stack.setCurrentWidget(self.app_container)
            self.switch_page("Home")
            self.statusBar().showMessage(f"Logged in as {username}")
            self.load_history()
        else:
            QMessageBox.critical(self, "Login Failed", "Invalid username or password")

    def logout(self):
        self.current_user = None
        self.Username_Input.clear()
        self.Password_Input.clear()
        self.stack.setCurrentWidget(self.login_page)
        self.statusBar().showMessage("Logged out")

    def open_signup(self):
        signup_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        back_link = QLabel("<a href='#' style='color: #001A44; text-decoration: none; font-weight: bold;'>↩ Back</a>")
        back_link.setFont(QFont("Times New Roman", 20, QFont.Bold))
        back_link.setCursor(Qt.PointingHandCursor)
        back_link.linkActivated.connect(lambda _: self.stack.setCurrentWidget(self.login_page))
        layout.addWidget(back_link, alignment=Qt.AlignLeft)

        title = QLabel("Sign Up")
        title.setFont(QFont("Times New Roman", 36, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        def field(placeholder, pwd=False):
            f = QLineEdit()
            f.setPlaceholderText(placeholder)
            f.setFixedSize(320, 36)
            f.setFont(QFont("Arial", 11))
            f.setStyleSheet(self.input_style())
            if pwd:
                f.setEchoMode(QLineEdit.Password)
            return f

        self.s_fullname = field("Full Name")
        self.s_username = field("Username")
        self.s_password = field("Password", pwd=True)
        self.s_confirm = field("Confirm Password", pwd=True)

        layout.addWidget(self.s_fullname, alignment=Qt.AlignCenter)
        layout.addWidget(self.s_username, alignment=Qt.AlignCenter)
        layout.addWidget(self.s_password, alignment=Qt.AlignCenter)
        layout.addWidget(self.s_confirm, alignment=Qt.AlignCenter)

        create_btn = QPushButton("Create Account")
        create_btn.setFixedSize(160, 40)
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setStyleSheet(self.primary_button_style())
        create_btn.clicked.connect(self.sign_up_action)
        layout.addWidget(create_btn, alignment=Qt.AlignCenter)

        layout.addStretch()
        signup_widget.setLayout(layout)
        self.stack.addWidget(signup_widget)
        self.stack.setCurrentWidget(signup_widget)

    def sign_up_action(self):
        full_name = self.s_fullname.text().strip()
        username = self.s_username.text().strip()
        password = self.s_password.text().strip()
        confirm = self.s_confirm.text().strip()

        if not all([full_name, username, password, confirm]):
            QMessageBox.critical(self, "Error", "All fields are required!")
            return

        if password != confirm:
            QMessageBox.critical(self, "Error", "Passwords do not match.")
            return

        users = read_csv(USER_FILE)
        if any(u.get("username", "").lower() == username.lower() for u in users):
            QMessageBox.critical(self, "Error", "Username already exists.")
            return

        users.append({"full_name": full_name, "username": username, "password": password, "confirm_password": confirm})
        write_csv(USER_FILE, users, ["full_name", "username", "password", "confirm_password"])
        QMessageBox.information(self, "Success", "Account created successfully!")
        self.stack.setCurrentWidget(self.login_page)

    def switch_page(self, name):
        for btn in (self.home_button, self.compress_button, self.decompress_button, self.history_button):
            btn.setChecked(False)

        if name == "Home":
            self.pages.setCurrentIndex(0)
            self.home_button.setChecked(True)
            self.statusBar().showMessage("Home")
        elif name == "Compress":
            self.pages.setCurrentIndex(1)
            self.compress_button.setChecked(True)
            self.statusBar().showMessage("Compress Mode")
        elif name == "Decompress":
            self.pages.setCurrentIndex(2)
            self.decompress_button.setChecked(True)
            self.statusBar().showMessage("Decompress Mode")
        elif name == "History":
            self.pages.setCurrentIndex(3)
            self.history_button.setChecked(True)
            self.statusBar().showMessage("History")
            self.load_history()

    def open_compress_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select file to compress", filter="All Files (*)")
        if not filepath:
            return
        
        output_path, _ = QFileDialog.getSaveFileName(self, "Save Compressed File As", filter="Compressed Files (*.huff)")
        if output_path:
            self.compress_single_file(filepath, output_path)

    def open_decompress_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select compressed file", filter="Compressed Files (*.huff)")
        if file_path:
            output_path, _ = QFileDialog.getSaveFileName(self, "Save Decompressed File As")
            if output_path:
                self.decompress_single_file(file_path, output_path)

    def compress_single_file(self, input_path, output_path):
        self.progress_dialog = ProgressDialog("Compression", self)
        self.progress_dialog.show()
        
        self.worker = CompressionWorker(self.api, 'compress', input_path, output_path)
        self.worker.progress_signal.connect(self.progress_dialog.update)
        self.worker.finished_signal.connect(lambda result: self.on_compression_finished(result, input_path, output_path, "Compression"))
        self.worker.error_signal.connect(self.on_compression_error)
        self.worker.start()

    def decompress_single_file(self, input_path, output_path):
        self.progress_dialog = ProgressDialog("Decompression", self)
        self.progress_dialog.show()
        
        self.worker = CompressionWorker(self.api, 'decompress', input_path, output_path)
        self.worker.progress_signal.connect(self.progress_dialog.update)
        self.worker.finished_signal.connect(lambda result: self.on_compression_finished(result, input_path, output_path, "Decompression"))
        self.worker.error_signal.connect(self.on_compression_error)
        self.worker.start()

    def on_compression_finished(self, result, input_path, output_path, operation_type):
        self.progress_dialog.close()
        
        results_dialog = ResultsDialog(result, operation_type, self)
        results_dialog.exec_()
        
        if result.success:
            record = {
                "username": self.current_user or "unknown",
                "file_name": os.path.basename(input_path),
                "operation": operation_type,
                "date_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "output_path": output_path,
                "original_size": str(result.original_size),
                "compressed_size": str(getattr(result, 'compressed_size', getattr(result, 'decompressed_size', ''))),
                "compression_ratio": f"{result.compression_ratio:.4f}" if hasattr(result, 'compression_ratio') else "N/A"
            }
            append_history(record)
            self.load_history()

    def on_compression_error(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Operation Failed", f"Error: {error_message}")

    def load_history(self):
        rows = read_csv(HISTORY_FILE)
        self.history_table.setRowCount(0)
        rows_sorted = sorted(rows, key=lambda r: r.get("date_time", ""), reverse=True)
        for r in rows_sorted:
            row_idx = self.history_table.rowCount()
            self.history_table.insertRow(row_idx)
            self.history_table.setItem(row_idx, 0, QTableWidgetItem(r.get("username", "")))
            self.history_table.setItem(row_idx, 1, QTableWidgetItem(r.get("file_name", "")))
            self.history_table.setItem(row_idx, 2, QTableWidgetItem(r.get("operation", "")))
            self.history_table.setItem(row_idx, 3, QTableWidgetItem(r.get("date_time", "")))
            self.history_table.setItem(row_idx, 4, QTableWidgetItem(r.get("output_path", "")))
            self.history_table.setItem(row_idx, 5, QTableWidgetItem(r.get("original_size", "")))
            self.history_table.setItem(row_idx, 6, QTableWidgetItem(r.get("compressed_size", "")))
            self.history_table.setItem(row_idx, 7, QTableWidgetItem(r.get("compression_ratio", "")))

    def clear_history_with_confirm(self):
        reply = QMessageBox.question(self, "Clear History", "Are you sure you want to clear all history?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            write_csv(HISTORY_FILE, [], ["username", "file_name", "operation", "date_time", "output_path", "original_size", "compressed_size", "compression_ratio"])
            self.load_history()
            QMessageBox.information(self, "Cleared", "History cleared.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())