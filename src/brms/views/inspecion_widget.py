"""Provides a tree-view-based widget to inspect details of an instrument and more."""

from brms.views.tree_widget import BRMSTreeWidget


class BRMSInspectionWidget(BRMSTreeWidget):
    """BRMSInspectionWidget extends BRMSTreeWidget to display a tree structure with inspection-related data."""


if __name__ == "__main__":
    import sys

    import QuantLib as ql
    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

    from brms.instruments.base import BookType, CreditRating, Issuer, IssuerType
    from brms.instruments.cash import Cash
    from brms.instruments.fixed_rate_bond import FixedRateBond
    from brms.instruments.visitors.inspection import InspectionVisitor

    class MainWindow(QWidget):
        """MainWindow class for testing."""

        def __init__(self) -> None:
            """Initialize the MainWindow."""
            super().__init__()
            self.setWindowTitle("BRMS Inspection Widget Example")
            self.resize(400, 600)
            self.tree = BRMSInspectionWidget(["Property", "Value"])
            layout = QVBoxLayout(self)
            layout.addWidget(self.tree)
            self.setLayout(layout)

            self.btn_cash = QPushButton("Inspect Cash")
            self.btn_cash.clicked.connect(self.inspect_cash)
            self.btn_bond1 = QPushButton("Inspect Fixed Rate Bond")
            self.btn_bond1.clicked.connect(self.inspect_fixed_rate_bond)
            self.btn_bond2 = QPushButton("Inspect Another Fixed Rate Bond")
            self.btn_bond2.clicked.connect(self.inspect_another_fixed_rate_bond)
            layout.addWidget(self.btn_cash)
            layout.addWidget(self.btn_bond1)
            layout.addWidget(self.btn_bond2)

        def inspect_cash(self) -> None:
            cash = Cash("Cash")
            inspector = InspectionVisitor()
            cash.accept(inspector)
            self.tree.populate_data(inspector.get_result())

        def inspect_fixed_rate_bond(self) -> None:
            face_value = 1000.0
            coupon_rate = 0.05
            issue_date = ql.Date(1, 1, 2020)
            maturity_date = ql.Date(1, 1, 2030)
            bond = FixedRateBond(
                face_value=face_value,
                coupon_rate=coupon_rate,
                issue_date=issue_date,
                maturity_date=maturity_date,
                book_type=BookType.TRADING_BOOK,
                credit_rating=CreditRating.AA_MINUS,
                issuer=Issuer(
                    name="Asian Development Bank",
                    issuer_type=IssuerType.MDB,
                    credit_rating=CreditRating.AA,
                ),
            )
            inspector = InspectionVisitor()
            bond.accept(inspector)
            self.tree.populate_data(inspector.get_result())

        def inspect_another_fixed_rate_bond(self) -> None:
            face_value = 1_000_000.0
            coupon_rate = 0.082
            issue_date = ql.Date(1, 1, 2025)
            maturity_date = ql.Date(1, 1, 2030)
            bond = FixedRateBond(
                face_value=face_value,
                coupon_rate=coupon_rate,
                issue_date=issue_date,
                maturity_date=maturity_date,
                book_type=BookType.TRADING_BOOK,
                credit_rating=CreditRating.BBB,
                issuer=Issuer(
                    name="AAA Pty Ltd.",
                    issuer_type=IssuerType.SME | IssuerType.CORPORATE,
                    credit_rating=CreditRating.AA_MINUS,
                ),
            )
            inspector = InspectionVisitor()
            bond.accept(inspector)
            self.tree.populate_data(inspector.get_result())

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
