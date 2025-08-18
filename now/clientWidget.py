import os
import sys
import spacy
from datetime import datetime, timedelta
from PyQt5 import QtWidgets, QtCore, QtGui
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Load the spaCy language model
nlp = spacy.load("en_core_web_sm")

class ClientAccountPage(QtWidgets.QDialog):
    """
    A full‑screen dialog displaying detailed client account information.
    Each field (Name, Age, Total Paid, Owed, Total Amount) is shown in an editable QLineEdit.
    The dialog also displays the client's image (or a default image if none is provided).
    A "Go to PDF Report" button opens the client's PDF report.
    """
    def __init__(self, client_data, parent=None):
        super().__init__(parent)
        # Use translation for window title as well.
        self.setWindowTitle(self.tr("Account Details - {0}").format(client_data.get("Name", self.tr("Unknown"))))
        self.client_data = client_data.copy()  # Work on a copy so original remains unchanged.
        self.resize(900, 700)
        self.setup_ui()
        self.apply_styles()

    # Override tr() to use our custom translation helper.
    def tr(self, text):
        from translation_helper import tr
        return tr(text)

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header with client name.
        self.header_label = QtWidgets.QLabel(self.tr("Account Details for {0}").format(self.client_data.get("Name", self.tr("Unknown"))))
        self.header_label.setFont(QtGui.QFont("Segoe UI", 24, QtGui.QFont.Bold))
        self.header_label.setAlignment(QtCore.Qt.AlignCenter)
        main_layout.addWidget(self.header_label)

        # Create a horizontal layout: left for image, right for details.
        content_layout = QtWidgets.QHBoxLayout()

        # --- Client Image ---
        self.image_label = QtWidgets.QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setScaledContents(True)
        image_path = self.client_data.get("Image", "")
        if image_path and os.path.exists(image_path):
            pixmap = QtGui.QPixmap(image_path)
        else:
            default_image = os.path.join(os.path.dirname(__file__), "default_client.png")
            if os.path.exists(default_image):
                pixmap = QtGui.QPixmap(default_image)
            else:
                pixmap = QtGui.QPixmap(200, 200)
                pixmap.fill(QtGui.QColor("gray"))
        self.image_label.setPixmap(pixmap)
        content_layout.addWidget(self.image_label)

        # --- Client Details Form ---
        form_layout = QtWidgets.QFormLayout()
        self.fields = {}
        # Fields to display and allow editing.
        field_list = ["Name", "Age", "Total Paid", "Owed", "Total Amount"]
        for field in field_list:
            container = QtWidgets.QWidget()
            h_layout = QtWidgets.QHBoxLayout(container)
            h_layout.setContentsMargins(0, 0, 0, 0)
            # Use translation on the field label if needed.
            line_edit = QtWidgets.QLineEdit(str(self.client_data.get(field, "")))
            line_edit.setFont(QtGui.QFont("Segoe UI", 16))
            h_layout.addWidget(line_edit)
            # Optional "Edit" button (for consistency)
            edit_btn = QtWidgets.QPushButton(self.tr("Edit"))
            edit_btn.setFont(QtGui.QFont("Segoe UI", 12))
            h_layout.addWidget(edit_btn)
            form_layout.addRow(f"{field}:", container)
            self.fields[field] = line_edit

        content_layout.addLayout(form_layout)
        main_layout.addLayout(content_layout)

        # "Go to PDF Report" button.
        self.go_to_pdf_btn = QtWidgets.QPushButton(self.tr("Go to PDF Report"))
        self.go_to_pdf_btn.setFont(QtGui.QFont("Segoe UI", 16))
        self.go_to_pdf_btn.clicked.connect(self.open_pdf_report)
        main_layout.addWidget(self.go_to_pdf_btn)

        # Save and Cancel buttons.
        button_layout = QtWidgets.QHBoxLayout()
        self.save_button = QtWidgets.QPushButton(self.tr("Save Changes"))
        self.save_button.setFont(QtGui.QFont("Segoe UI", 16))
        self.save_button.clicked.connect(self.save_changes)
        button_layout.addWidget(self.save_button)
        self.cancel_button = QtWidgets.QPushButton(self.tr("Cancel"))
        self.cancel_button.setFont(QtGui.QFont("Segoe UI", 16))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def apply_styles(self):
        style = """
        QDialog {
            background-color: #f0f0f0;
        }
        QLabel {
            font-family: Arial, sans-serif;
            font-size: 14px;
            color: #003366;
        }
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #E1E4E8;
            border-radius: 8px;
            padding: 8px;
        }
        QPushButton {
            background-color: #008080;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px 18px;
            font-size: 16px;
        }
        QPushButton:hover {
            background-color: #006666;
        }
        """
        self.setStyleSheet(style)

    def open_pdf_report(self):
        client_name = self.client_data.get("Name", self.tr("Unknown"))
        base_filename = "".join(c for c in client_name if c.isalnum() or c in (' ', '_')).replace(" ", "_")
        if not base_filename:
            base_filename = self.tr("Unknown")
        user_home = os.path.expanduser("~")
        save_directory = os.path.join(user_home, "Desktop", "reports")
        pdf_file_path = os.path.join(save_directory, f"{base_filename}_report.pdf")
        if os.path.exists(pdf_file_path):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(pdf_file_path))
        else:
            QtWidgets.QMessageBox.warning(self, self.tr("PDF Report Not Found"),
                                          self.tr("PDF report for {0} not found at:\n{1}").format(client_name, pdf_file_path))

    def save_changes(self):
        for field, widget in self.fields.items():
            self.client_data[field] = widget.text().strip()
        self.accept()

    def get_updated_data(self):
        return self.client_data

    def retranslateUi(self):
        # Update all user-visible texts
        self.setWindowTitle(self.tr("Account Details - {0}").format(self.client_data.get("Name", self.tr("Unknown"))))
        self.header_label.setText(self.tr("Account Details for {0}").format(self.client_data.get("Name", self.tr("Unknown"))))
        # For each field, update the row label (if applicable) and button texts:
        # (Assuming the field names remain the same)
        # Update buttons:
        self.go_to_pdf_btn.setText(self.tr("Go to PDF Report"))
        self.save_button.setText(self.tr("Save Changes"))
        self.cancel_button.setText(self.tr("Cancel"))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    sample_data = {
        "Name": "Ahmdahh Smith",
        "Age": 40,
        "Total Paid": 300,
        "Owed": 50,
        "Total Amount": 350,
        "Image": "default_client.png"  # Ensure this file exists or update the path accordingly.
    }
    dialog = ClientAccountPage(sample_data)
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        updated = dialog.get_updated_data()
        print("Updated data:", updated)
    sys.exit(app.exec_())
