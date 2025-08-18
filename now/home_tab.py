import sys
import re
import json
import spacy
from PyQt5 import QtWidgets, QtCore, QtGui
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# Load the spaCy language model
nlp = spacy.load("en_core_web_sm")


def parse_patient_info(text):
    """
    Process free-form human language text and extract patient information.
    """
    doc = nlp(text)
    info = {
        "Name": None,
        "Age": None,
        "Symptoms": [],
        "Notes": text  # Fallback: store the original text.
    }

    # Extract a person's name using spaCy's NER
    for ent in doc.ents:
        if ent.label_ == "PERSON" and info["Name"] is None:
            info["Name"] = ent.text

    # Use regex to extract age (e.g., "age 45" or "45 years old")
    age_match = re.search(r'age\s+(\d+)', text, re.IGNORECASE)
    if age_match:
        info["Age"] = int(age_match.group(1))
    else:
        age_match = re.search(r'(\d+)\s+years?\s+old', text, re.IGNORECASE)
        if age_match:
            info["Age"] = int(age_match.group(1))

    # Identify common symptoms via keyword matching
    symptom_keywords = [
        "pain", "headache", "nausea", "dizziness", "fever",
        "cough", "shortness of breath", "chest pain"
    ]
    for keyword in symptom_keywords:
        if keyword in text.lower() and keyword not in info["Symptoms"]:
            info["Symptoms"].append(keyword)

    return info


class ExtractionTab(QtWidgets.QWidget):
    """Tab for loading free text, processing it, and saving as PDF."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header label for this tab
        header_label = QtWidgets.QLabel("Data Extraction")
        header_label.setAlignment(QtCore.Qt.AlignCenter)
        header_font = QtGui.QFont("Arial", 16, QtGui.QFont.Bold)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Input area with label
        input_label = QtWidgets.QLabel("Enter patient information:")
        layout.addWidget(input_label)

        self.input_text = QtWidgets.QTextEdit()
        self.input_text.setFixedHeight(120)
        layout.addWidget(self.input_text)

        # Horizontal layout for buttons (Load Test Data & Process Input)
        button_layout = QtWidgets.QHBoxLayout()
        self.load_test_button = QtWidgets.QPushButton("Load Test Data")
        self.load_test_button.setFixedHeight(40)
        self.load_test_button.clicked.connect(self.load_test_data)
        button_layout.addWidget(self.load_test_button)

        self.process_button = QtWidgets.QPushButton("Process Input")
        self.process_button.setFixedHeight(40)
        self.process_button.clicked.connect(self.process_input)
        button_layout.addWidget(self.process_button)
        layout.addLayout(button_layout)

        # Extracted data table label
        table_label = QtWidgets.QLabel("Extracted Information:")
        layout.addWidget(table_label)

        # Expert table to display extracted data
        self.tableWidget = QtWidgets.QTableWidget()
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Field", "Value"])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        layout.addWidget(self.tableWidget)

        # Save data button
        self.save_button = QtWidgets.QPushButton("Save Data as PDF")
        self.save_button.setFixedHeight(40)
        self.save_button.clicked.connect(self.save_data)
        layout.addWidget(self.save_button)

        layout.addStretch()

    def load_test_data(self):
        """Load sample test data into the text input area."""
        test_data = (
            "Patient John Doe, age 45, complains of severe headache and nausea. "
            "Additionally, he experiences intermittent chest pain and mild cough. "
            "The patient is allergic to penicillin and has a blood pressure reading of 140/90 mmHg. "
            "He also reports a slight fever, dizziness, and shortness of breath. "
            "Further details: the patient has a history of hypertension and is currently on medication."
        )
        self.input_text.setPlainText(test_data)

    def process_input(self):
        text = self.input_text.toPlainText()
        if not text.strip():
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please enter some text.")
            return

        # Process the text and extract data
        self.current_data = parse_patient_info(text)
        self.populate_table(self.current_data)

    def populate_table(self, data):
        """Populate the table widget with extracted data."""
        self.tableWidget.setRowCount(0)  # Clear any existing rows
        for row, (field, value) in enumerate(data.items()):
            self.tableWidget.insertRow(row)
            field_item = QtWidgets.QTableWidgetItem(field)
            # Convert list to a comma-separated string if needed
            if isinstance(value, list):
                value = ", ".join(value)
            value_item = QtWidgets.QTableWidgetItem(str(value))
            self.tableWidget.setItem(row, 0, field_item)
            self.tableWidget.setItem(row, 1, value_item)

    def save_data(self):
        """Save the extracted data as a PDF file using the patient's name as the default file name."""
        if not hasattr(self, 'current_data'):
            QtWidgets.QMessageBox.warning(self, "No Data", "Please process some text first.")
            return

        # Retrieve patient name from the data (use "patient" if not found)
        patient_name = self.current_data.get("Name", "patient")
        # Sanitize the patient name for file naming (remove illegal characters)
        patient_name_sanitized = "".join(c for c in patient_name if c.isalnum() or c in (' ', '_')).strip().replace(" ",
                                                                                                                    "_")
        if not patient_name_sanitized:
            patient_name_sanitized = "patient"
        default_file_name = f"{patient_name_sanitized}.pdf"

        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Extracted Data as PDF", default_file_name, "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_path:
            try:
                # Create a PDF document using ReportLab
                doc = SimpleDocTemplate(file_path, pagesize=letter)
                elements = []
                styles = getSampleStyleSheet()

                # Add a title to the PDF
                title = Paragraph("Extracted Patient Data", styles['Title'])
                elements.append(title)
                elements.append(Spacer(1, 12))

                # Prepare the data for the table in the PDF
                table_data = [["Field", "Value"]]
                for field, value in self.current_data.items():
                    if isinstance(value, list):
                        value = ", ".join(value)
                    table_data.append([field, str(value)])

                # Create the table with custom styling
                t = Table(table_data, colWidths=[150, 350])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(t)

                # Build the PDF file
                doc.build(elements)
                QtWidgets.QMessageBox.information(self, "Success", "PDF saved successfully!")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Save Error", f"An error occurred: {e}")


class NewClientTab(QtWidgets.QWidget):
    """Tab for manually entering new client data via a form."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header label for this tab
        header_label = QtWidgets.QLabel("Add New Client")
        header_label.setAlignment(QtCore.Qt.AlignCenter)
        header_font = QtGui.QFont("Arial", 16, QtGui.QFont.Bold)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Create form fields for new client data
        form_layout = QtWidgets.QFormLayout()
        self.name_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Name:", self.name_edit)
        self.age_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Age:", self.age_edit)
        self.symptoms_edit = QtWidgets.QLineEdit()
        form_layout.addRow("Symptoms (comma-separated):", self.symptoms_edit)
        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setFixedHeight(80)
        form_layout.addRow("Notes:", self.notes_edit)
        layout.addLayout(form_layout)

        # Save button for the new client
        self.save_new_button = QtWidgets.QPushButton("Save New Client as PDF")
        self.save_new_button.setFixedHeight(40)
        self.save_new_button.clicked.connect(self.save_new_client)
        layout.addWidget(self.save_new_button)

        layout.addStretch()

    def save_new_client(self):
        """Collect data from form fields and save as a PDF."""
        name = self.name_edit.text().strip()
        age = self.age_edit.text().strip()
        symptoms = self.symptoms_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()

        if not name:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please enter the client's name.")
            return

        # Build a dictionary to hold the client data
        client_data = {
            "Name": name,
            "Age": age if age else "N/A",
            "Symptoms": [s.strip() for s in symptoms.split(",")] if symptoms else [],
            "Notes": notes if notes else ""
        }

        # Sanitize the name for file naming
        client_name_sanitized = "".join(c for c in name if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
        if not client_name_sanitized:
            client_name_sanitized = "client"
        default_file_name = f"{client_name_sanitized}.pdf"

        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save New Client Data as PDF", default_file_name, "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_path:
            try:
                doc = SimpleDocTemplate(file_path, pagesize=letter)
                elements = []
                styles = getSampleStyleSheet()

                # Add a title
                title = Paragraph("New Client Data", styles['Title'])
                elements.append(title)
                elements.append(Spacer(1, 12))

                # Prepare table data
                table_data = [["Field", "Value"]]
                for field, value in client_data.items():
                    if isinstance(value, list):
                        value = ", ".join(value)
                    table_data.append([field, str(value)])

                t = Table(table_data, colWidths=[150, 350])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(t)
                doc.build(elements)
                QtWidgets.QMessageBox.information(self, "Success", "PDF saved successfully!")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Save Error", f"An error occurred: {e}")


class EditClientTab(QtWidgets.QWidget):
    """Tab for loading an existing client's data from JSON and editing the patient info."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header_label = QtWidgets.QLabel("Load & Edit Client")
        header_label.setAlignment(QtCore.Qt.AlignCenter)
        header_font = QtGui.QFont("Arial", 16, QtGui.QFont.Bold)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Load Client Data button
        self.load_button = QtWidgets.QPushButton("Load Client Data (JSON)")
        self.load_button.setFixedHeight(40)
        self.load_button.clicked.connect(self.load_client_data)
        layout.addWidget(self.load_button)

        # Form fields for client data (similar to NewClientTab)
        form_layout = QtWidgets.QFormLayout()
        self.edit_name = QtWidgets.QLineEdit()
        form_layout.addRow("Name:", self.edit_name)
        self.edit_age = QtWidgets.QLineEdit()
        form_layout.addRow("Age:", self.edit_age)
        self.edit_symptoms = QtWidgets.QLineEdit()
        form_layout.addRow("Symptoms (comma-separated):", self.edit_symptoms)
        self.edit_notes = QtWidgets.QTextEdit()
        self.edit_notes.setFixedHeight(80)
        form_layout.addRow("Notes:", self.edit_notes)
        layout.addLayout(form_layout)

        # Button to save edited client data as PDF
        self.save_edit_button = QtWidgets.QPushButton("Save Changes as PDF")
        self.save_edit_button.setFixedHeight(40)
        self.save_edit_button.clicked.connect(self.save_edited_client)
        layout.addWidget(self.save_edit_button)

        layout.addStretch()

    def load_client_data(self):
        """Load client data from a JSON file and populate the form fields."""
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Client Data JSON", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    client_data = json.load(f)
                # Populate form fields with loaded data
                self.edit_name.setText(client_data.get("Name", ""))
                self.edit_age.setText(str(client_data.get("Age", "")))
                symptoms = client_data.get("Symptoms", [])
                if isinstance(symptoms, list):
                    symptoms = ", ".join(symptoms)
                self.edit_symptoms.setText(symptoms)
                self.edit_notes.setPlainText(client_data.get("Notes", ""))
                QtWidgets.QMessageBox.information(self, "Loaded", "Client data loaded successfully!")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Load Error", f"Could not load file:\n{e}")

    def save_edited_client(self):
        """Collect edited data and save as a PDF."""
        name = self.edit_name.text().strip()
        age = self.edit_age.text().strip()
        symptoms = self.edit_symptoms.text().strip()
        notes = self.edit_notes.toPlainText().strip()

        if not name:
            QtWidgets.QMessageBox.warning(self, "Input Error", "Please enter the client's name.")
            return

        # Build the client data dictionary
        client_data = {
            "Name": name,
            "Age": age if age else "N/A",
            "Symptoms": [s.strip() for s in symptoms.split(",")] if symptoms else [],
            "Notes": notes if notes else ""
        }

        # Sanitize the client name for file naming
        client_name_sanitized = "".join(c for c in name if c.isalnum() or c in (' ', '_')).strip().replace(" ", "_")
        if not client_name_sanitized:
            client_name_sanitized = "client"
        default_file_name = f"{client_name_sanitized}.pdf"

        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Edited Client Data as PDF", default_file_name, "PDF Files (*.pdf);;All Files (*)",
            options=options)
        if file_path:
            try:
                doc = SimpleDocTemplate(file_path, pagesize=letter)
                elements = []
                styles = getSampleStyleSheet()

                title = Paragraph("Edited Client Data", styles['Title'])
                elements.append(title)
                elements.append(Spacer(1, 12))

                table_data = [["Field", "Value"]]
                for field, value in client_data.items():
                    if isinstance(value, list):
                        value = ", ".join(value)
                    table_data.append([field, str(value)])

                t = Table(table_data, colWidths=[150, 350])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ]))
                elements.append(t)
                doc.build(elements)
                QtWidgets.QMessageBox.information(self, "Success", "PDF saved successfully!")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Save Error", f"An error occurred: {e}")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MediNote AI: Expert Table")
        self.resize(800, 800)
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        # Create a QTabWidget as the central widget
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create and add the Extraction tab
        self.extraction_tab = ExtractionTab()
        self.tabs.addTab(self.extraction_tab, "Data Extraction")

        # Create and add the New Client tab
        self.new_client_tab = NewClientTab()
        self.tabs.addTab(self.new_client_tab, "Add New Client")

        # Create and add the Edit Client tab
        self.edit_client_tab = EditClientTab()
        self.tabs.addTab(self.edit_client_tab, "Load/Edit Client")

    def apply_styles(self):
        """
        Apply an expert design color scheme using Qt Style Sheets (QSS).
        This style uses a dark background with blue and light grey accents.
        """
        style = """
        QMainWindow {
            background-color: #1F1F2E;  /* Dark background */
        }
        QWidget {
            color: #E0E0E0;  /* Light grey text */
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 14px;
        }
        QLabel {
            color: #E0E0E0;
        }
        QTextEdit, QLineEdit {
            background-color: #2B2B3A;  /* Slightly lighter than main background */
            color: #E0E0E0;
            border: 1px solid #44475a;
            border-radius: 5px;
            padding: 5px;
        }
        QPushButton {
            background-color: #005F73;  /* Deep blue accent */
            color: #E0E0E0;
            border: none;
            border-radius: 5px;
            padding: 8px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #0A9396;  /* Lighter blue accent on hover */
        }
        QTableWidget {
            background-color: #2B2B3A;
            color: #E0E0E0;
            border: 1px solid #44475a;
            border-radius: 5px;
        }
        QHeaderView::section {
            background-color: #005F73;
            padding: 6px;
            border: none;
        }
        QTabBar::tab {
            background: #2B2B3A;
            padding: 10px;
            margin: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        QTabBar::tab:selected {
            background: #005F73;
        }
        """
        self.setStyleSheet(style)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()