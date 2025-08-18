from PyQt5 import QtWidgets, QtCore, QtGui
import os
import json

class CustomizedTemplateTab(QtWidgets.QWidget):
    """
    This widget provides a UI for selecting and previewing customizable PDF templates.
    """
    def __init__(self, templates_folder="templates", parent=None):
        super().__init__(parent)
        self.templates_folder = templates_folder
        self.setup_ui()
        self.load_templates()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header label
        header = QtWidgets.QLabel("Customized Template")
        header.setAlignment(QtCore.Qt.AlignCenter)
        header.setFont(QtGui.QFont("Arial", 18, QtGui.QFont.Bold))
        main_layout.addWidget(header)

        # Instruction label
        instruct_label = QtWidgets.QLabel("Select a template from the list below:")
        instruct_label.setWordWrap(True)
        main_layout.addWidget(instruct_label)

        # Horizontal layout for list and preview
        h_layout = QtWidgets.QHBoxLayout()
        h_layout.setSpacing(10)

        # List widget for template names
        self.template_list = QtWidgets.QListWidget()
        self.template_list.setMinimumWidth(200)
        self.template_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.template_list.itemSelectionChanged.connect(self.display_template_preview)
        h_layout.addWidget(self.template_list, 1)

        # Preview area (read-only) for template details
        self.preview_edit = QtWidgets.QTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setStyleSheet("background-color: #2B2B3A; color: #E0E0E0;")
        h_layout.addWidget(self.preview_edit, 2)

        main_layout.addLayout(h_layout)
        main_layout.addStretch()

    def load_templates(self):
        """
        Loads available template JSON files from the templates folder.
        """
        self.template_list.clear()
        if not os.path.exists(self.templates_folder):
            self.preview_edit.setPlainText("Templates folder not found.")
            return

        template_files = [f for f in os.listdir(self.templates_folder) if f.lower().endswith(".json")]
        if not template_files:
            self.preview_edit.setPlainText("No templates found in the folder.")
            return

        for file_name in template_files:
            full_path = os.path.join(self.templates_folder, file_name)
            display_name = os.path.splitext(file_name)[0]
            item = QtWidgets.QListWidgetItem(display_name)
            item.setData(QtCore.Qt.UserRole, full_path)
            self.template_list.addItem(item)

    def display_template_preview(self):
        selected_items = self.template_list.selectedItems()
        if not selected_items:
            self.preview_edit.clear()
            return

        item = selected_items[0]
        file_path = item.data(QtCore.Qt.UserRole)
        try:
            with open(file_path, "r") as f:
                template_config = json.load(f)
            preview_text = json.dumps(template_config, indent=4)
            self.preview_edit.setPlainText(preview_text)
        except Exception as e:
            self.preview_edit.setPlainText(f"Error loading template: {e}")
