import re

from PySide6.QtWidgets import QTabWidget, QTextBrowser, QWidget


class BRMSStatementBrowser(QTextBrowser):
    def setHtml(self, html: str) -> None:
        # Remove <code> tags - not supported by QTextBrowser
        html = re.sub(r"<code.*?>(.*?)</code>", r"\1", html, flags=re.DOTALL)
        super().setHtml(html)


class BRMSStatementViewer(QTabWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Create statement browsers for each tab
        self.trial_balance_browser = BRMSStatementBrowser()
        self.income_statement_browser = BRMSStatementBrowser()
        self.balance_sheet_browser = BRMSStatementBrowser()

        # Add tabs to the tab widget
        self.addTab(self.trial_balance_browser, "Trial Balance")
        self.addTab(self.income_statement_browser, "Income Statement")
        self.addTab(self.balance_sheet_browser, "Balance Sheet")
