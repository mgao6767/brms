import re
from PySide6.QtWidgets import QTextBrowser


class BRMSStatementBrowser(QTextBrowser):
    def setHtml(self, html: str) -> None:
        # Remove <code> tags - not supported by QTextBrowser
        html = re.sub(r"<code.*?>(.*?)</code>", r"\1", html, flags=re.DOTALL)
        super().setHtml(html)
