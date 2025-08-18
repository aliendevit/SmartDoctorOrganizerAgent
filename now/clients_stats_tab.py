import os
import sys
from collections import Counter
from PyQt5 import QtWidgets, QtCore
from data.data import load_all_clients
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ClientStatsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Summary label: displays total clients, average age, total revenue, and outstanding.
        self.summary_label = QtWidgets.QLabel("Loading client summary...")
        layout.addWidget(self.summary_label)

        # Payment Status Pie Chart (Fully Paid vs. Not Fully Paid)
        self.payment_fig = Figure(figsize=(4, 4))
        self.payment_canvas = FigureCanvas(self.payment_fig)
        layout.addWidget(self.payment_canvas)

        # Age Distribution Bar Chart
        self.age_fig = Figure(figsize=(4, 3))
        self.age_canvas = FigureCanvas(self.age_fig)
        layout.addWidget(self.age_canvas)

        # Refresh button for statistics
        refresh_btn = QtWidgets.QPushButton("Refresh Statistics")
        refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(refresh_btn)

        layout.addStretch()
        self.setLayout(layout)

    def refresh_data(self):
        clients = load_all_clients()
        total_clients = len(clients)

        total_age = 0
        count_age = 0
        total_revenue = 0
        total_outstanding = 0
        fully_paid = 0
        not_fully_paid = 0
        ages = []

        # Loop through each client and calculate summary statistics.
        for client in clients:
            # Age extraction.
            try:
                age = float(client.get("Age", 0))
                ages.append(age)
                total_age += age
                count_age += 1
            except (ValueError, TypeError):
                pass
            # Payment data.
            try:
                tp = float(client.get("Total Paid", 0))
                ta = float(client.get("Total Amount", 0))
            except (ValueError, TypeError):
                tp = ta = 0
            total_revenue += tp
            if tp >= ta:
                fully_paid += 1
            else:
                not_fully_paid += 1
                total_outstanding += (ta - tp)

        avg_age = total_age / count_age if count_age > 0 else 0

        self.summary_label.setText(
            f"Total Clients: {total_clients} | Average Age: {avg_age:.1f} | "
            f"Total Revenue: {total_revenue:,.2f} | Outstanding: {total_outstanding:,.2f}"
        )

        # --- Payment Status Pie Chart ---
        self.payment_fig.clear()
        ax = self.payment_fig.add_subplot(111)
        if (fully_paid + not_fully_paid) > 0:
            labels = ["Fully Paid", "Not Fully Paid"]
            sizes = [fully_paid, not_fully_paid]
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
            ax.axis('equal')
            ax.set_title("Payment Status")
        else:
            ax.text(0.5, 0.5, "No payment data", horizontalalignment='center', verticalalignment='center')
        self.payment_canvas.draw()

        # --- Age Distribution Bar Chart ---
        self.age_fig.clear()
        ax2 = self.age_fig.add_subplot(111)
        if ages:
            bins = range(int(min(ages)), int(max(ages)) + 2)
            ax2.hist(ages, bins=bins, edgecolor='black', color='#008080')
            ax2.set_title("Age Distribution")
            ax2.set_xlabel("Age")
            ax2.set_ylabel("Number of Clients")
        else:
            ax2.text(0.5, 0.5, "No age data", horizontalalignment='center', verticalalignment='center')
        self.age_canvas.draw()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    stats_tab = ClientStatsTab()
    stats_tab.show()
    sys.exit(app.exec_())
