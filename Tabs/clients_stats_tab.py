# client_stats_tab.py
# Readable charts on dark UI + clean layout
# - Global Matplotlib text/tick/axes colors set to light tones
# - Pie labels/percentages/legend in light color
# - Histogram ticks/labels/edges in light color
# - No change to your app's color palette

import os
import sys
from PyQt5 import QtWidgets, QtCore
from data.data import load_all_clients

from matplotlib import rcParams
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ---- Make all Matplotlib text readable on dark backgrounds ----
rcParams.update({
    "text.color":        "#E5E7EB",  # near-white
    "axes.labelcolor":   "#E5E7EB",
    "axes.titlecolor":   "#E5E7EB",
    "xtick.color":       "#E5E7EB",
    "ytick.color":       "#E5E7EB",
    "axes.edgecolor":    "#374151",  # subtle dark gray for spines
    "grid.color":        "#374151",
})

def _polish(*widgets):
    """Re-apply QSS after setting dynamic properties."""
    for w in widgets:
        w.style().unpolish(w)
        w.style().polish(w)
        w.update()

class ClientStatsTab(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_data()

    # Optional translation helper hook
    def tr(self, text):
        try:
            from translation_helper import tr as _tr
            return _tr(text)
        except Exception:
            return text

    def _setup_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ===== Header card =====
        header = QtWidgets.QFrame()
        header.setProperty("modernCard", True)
        hly = QtWidgets.QHBoxLayout(header)
        hly.setContentsMargins(12, 12, 12, 12)
        hly.setSpacing(8)

        title = QtWidgets.QLabel(self.tr("Client Statistics"))
        title.setStyleSheet("font-size: 16pt; font-weight: 700;")
        hly.addWidget(title)
        hly.addStretch(1)

        self.refresh_btn = QtWidgets.QPushButton(self.tr("Refresh Statistics"))
        self.refresh_btn.setProperty("variant", "ghost")
        self.refresh_btn.setProperty("accent", "violet")
        self.refresh_btn.clicked.connect(self.refresh_data)
        hly.addWidget(self.refresh_btn)
        _polish(self.refresh_btn)

        root.addWidget(header)

        # ===== Summary card =====
        summary_card = QtWidgets.QFrame()
        summary_card.setProperty("modernCard", True)
        sc_ly = QtWidgets.QVBoxLayout(summary_card)
        sc_ly.setContentsMargins(12, 12, 12, 12)
        sc_ly.setSpacing(6)

        self.summary_label = QtWidgets.QLabel(self.tr("Loading client summary..."))
        self.summary_label.setStyleSheet("font-weight: 600;")
        sc_ly.addWidget(self.summary_label)

        root.addWidget(summary_card)

        # ===== Charts row (pie + histogram) =====
        charts_row = QtWidgets.QHBoxLayout()
        charts_row.setSpacing(12)

        # -- Payment Status (Pie) card
        payment_card = QtWidgets.QFrame()
        payment_card.setProperty("modernCard", True)
        pc_ly = QtWidgets.QVBoxLayout(payment_card)
        pc_ly.setContentsMargins(12, 12, 12, 12)
        pc_ly.setSpacing(6)

        lbl_payment = QtWidgets.QLabel(self.tr("Payment Status"))
        lbl_payment.setStyleSheet("font-weight: 600;")
        pc_ly.addWidget(lbl_payment)

        self.payment_fig = Figure(figsize=(4, 4), tight_layout=True)
        self.payment_fig.set_facecolor("none")
        self.payment_canvas = FigureCanvas(self.payment_fig)
        self.payment_canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        pc_ly.addWidget(self.payment_canvas)

        charts_row.addWidget(payment_card, 1)

        # -- Age Distribution (Histogram) card
        age_card = QtWidgets.QFrame()
        age_card.setProperty("modernCard", True)
        ac_ly = QtWidgets.QVBoxLayout(age_card)
        ac_ly.setContentsMargins(12, 12, 12, 12)
        ac_ly.setSpacing(6)

        lbl_age = QtWidgets.QLabel(self.tr("Age Distribution"))
        lbl_age.setStyleSheet("font-weight: 600;")
        ac_ly.addWidget(lbl_age)

        self.age_fig = Figure(figsize=(4, 3), tight_layout=True)
        self.age_fig.set_facecolor("none")
        self.age_canvas = FigureCanvas(self.age_fig)
        self.age_canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        ac_ly.addWidget(self.age_canvas)

        charts_row.addWidget(age_card, 1)

        root.addLayout(charts_row)
        root.addStretch(1)

    def refresh_data(self):
        clients = load_all_clients() or []
        total_clients = len(clients)

        ages = []
        total_age = 0.0
        count_age = 0
        total_revenue = 0.0
        total_outstanding = 0.0
        fully_paid = 0
        not_fully_paid = 0

        for client in clients:
            # Age
            try:
                age = float(client.get("Age", 0))
                ages.append(age)
                total_age += age
                count_age += 1
            except (ValueError, TypeError):
                pass

            # Payments
            try:
                tp = float(client.get("Total Paid", 0))
                ta = float(client.get("Total Amount", 0))
            except (ValueError, TypeError):
                tp = ta = 0.0

            total_revenue += tp
            if tp >= ta:
                fully_paid += 1
            else:
                not_fully_paid += 1
                total_outstanding += max(0.0, ta - tp)

        avg_age = (total_age / count_age) if count_age else 0.0

        self.summary_label.setText(
            f"{self.tr('Total Clients:')} {total_clients} | "
            f"{self.tr('Average Age:')} {avg_age:.1f} | "
            f"{self.tr('Total Revenue:')} {total_revenue:,.2f} | "
            f"{self.tr('Outstanding:')} {total_outstanding:,.2f}"
        )

        # ---- Payment Status Pie ----
        self.payment_fig.clear()
        ax = self.payment_fig.add_subplot(111)
        ax.set_facecolor("none")

        total_cases = fully_paid + not_fully_paid
        if total_cases > 0:
            labels = [self.tr("Fully Paid"), self.tr("Not Fully Paid")]
            sizes = [fully_paid, not_fully_paid]

            # startangle+counterclockwise keep label order matching the legend
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                autopct=lambda pct: f"{pct:.1f}% ({int(round(pct/100*total_cases))})",
                startangle=90,
                counterclock=False,
            )
            ax.axis("equal")

            # Ensure label/percent text is readable
            for t in texts:
                t.set_color("#E5E7EB")
            for t in autotexts:
                t.set_color("#E5E7EB")

            # Legend that uses wedge colors
            leg = ax.legend(
                wedges,
                labels,
                title=self.tr("Status"),
                loc="center left",
                bbox_to_anchor=(1.0, 0.5),
                frameon=False,
            )
            leg.get_title().set_color("#E5E7EB")
            for t in leg.get_texts():
                t.set_color("#E5E7EB")
        else:
            ax.text(
                0.5, 0.5, self.tr("No payment data"),
                ha="center", va="center", transform=ax.transAxes, color="#E5E7EB"
            )

        self.payment_canvas.draw()

        # ---- Age Distribution Histogram ----
        self.age_fig.clear()
        ax2 = self.age_fig.add_subplot(111)
        ax2.set_facecolor("none")

        if ages:
            lo, hi = int(min(ages)), int(max(ages))
            bins = range(lo, hi + 2)
            ax2.hist(ages, bins=bins, edgecolor="#E5E7EB")  # light edge on dark bg
            ax2.set_xlabel(self.tr("Age"), color="#E5E7EB")
            ax2.set_ylabel(self.tr("Number of Clients"), color="#E5E7EB")
            ax2.set_title(self.tr("Age Distribution"), color="#E5E7EB")
            ax2.tick_params(colors="#E5E7EB")
            for sp in ax2.spines.values():
                sp.set_color("#374151")
        else:
            ax2.text(
                0.5, 0.5, self.tr("No age data"),
                ha="center", va="center", transform=ax2.transAxes, color="#E5E7EB"
            )

        self.age_canvas.draw()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    # Apply the modern theme automatically if available
    try:
        from modern_theme import ModernTheme
        ModernTheme.apply(app, mode="dark", base_point_size=11, rtl=False)
    except Exception:
        pass
    stats_tab = ClientStatsTab()
    stats_tab.resize(1000, 600)
    stats_tab.show()
    sys.exit(app.exec_())
