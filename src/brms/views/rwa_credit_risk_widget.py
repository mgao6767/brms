from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class BRMSRWACreditRiskWidget(QWidget):
    def __init__(self):
        super().__init__()

        # Control panel
        ctrl_panel = QSplitter()
        ctrl_panel.setOrientation(Qt.Orientation.Vertical)
        self.ctrl_group = QGroupBox("Exposures && Computation Approaches")
        ctrl_panel.addWidget(self.ctrl_group)

        layout_ctrl = QVBoxLayout()
        layout_ctrl.setAlignment(Qt.AlignmentFlag.AlignTop)

        lbl_banking = QLabel("Banking Book Exposures")
        font_banking = lbl_banking.font()
        font_banking.setBold(True)
        lbl_banking.setFont(font_banking)
        layout_ctrl.addWidget(lbl_banking)

        bg_banking = QButtonGroup(self)
        rb_banking_std = QRadioButton("Standardised Approach")
        rb_banking_irb = QRadioButton("Internal Ratings Based (IRB) Approach")
        rb_banking_irb.setEnabled(False)
        rb_banking_std.setChecked(True)
        bg_banking.addButton(rb_banking_std)
        bg_banking.addButton(rb_banking_irb)
        layout_ctrl.addWidget(rb_banking_std)
        layout_ctrl.addWidget(rb_banking_irb)

        rb_banking_std.toggled.connect(self.on_banking_std_clicked)
        rb_banking_irb.toggled.connect(self.on_banking_irb_clicked)

        lbl_counterparty = QLabel("Counterparty Credit Risk")
        font_cp = lbl_counterparty.font()
        font_cp.setBold(True)
        lbl_counterparty.setFont(font_cp)
        layout_ctrl.addWidget(lbl_counterparty)

        bg_counterparty = QButtonGroup(self)
        rb_counterparty = QRadioButton("Default Approach")
        rb_counterparty.setChecked(True)
        bg_counterparty.addButton(rb_counterparty)
        layout_ctrl.addWidget(rb_counterparty)

        rb_counterparty.toggled.connect(self.on_counterparty_clicked)

        lbl_equity = QLabel("Equity Investments in Funds")
        font_equity = lbl_equity.font()
        font_equity.setBold(True)
        lbl_equity.setFont(font_equity)
        layout_ctrl.addWidget(lbl_equity)

        bg_equity = QButtonGroup(self)
        rb_equity_lta = QRadioButton("Look Through Approach")
        rb_equity_mba = QRadioButton("Mandate Based Approach")
        rb_equity_fba = QRadioButton("Fall Back Approach")
        rb_equity_mba.setEnabled(False)
        rb_equity_fba.setEnabled(False)
        rb_equity_lta.setChecked(True)
        for rb in (rb_equity_lta, rb_equity_mba, rb_equity_fba):
            bg_equity.addButton(rb)
            layout_ctrl.addWidget(rb)

        rb_equity_lta.toggled.connect(self.on_equity_lta_clicked)
        rb_equity_mba.toggled.connect(self.on_equity_mba_clicked)
        rb_equity_fba.toggled.connect(self.on_equity_fba_clicked)

        lbl_securitisation = QLabel("Securitisation Exposures")
        font_sec = lbl_securitisation.font()
        font_sec.setBold(True)
        lbl_securitisation.setFont(font_sec)
        layout_ctrl.addWidget(lbl_securitisation)

        bg_securitisation = QButtonGroup(self)
        rb_securitisation_std = QRadioButton("Standardised Approach (SEC-SA)")
        rb_securitisation_ext = QRadioButton("External Ratings Based Approach (SEC-ERBA)")
        rb_securitisation_iaa = QRadioButton("Internal Assessment Approach (IAA)")
        rb_securitisation_irb = QRadioButton("Internal Ratings Based Approach (SEC-IRBA)")
        rb_securitisation_ext.setEnabled(False)
        rb_securitisation_iaa.setEnabled(False)
        rb_securitisation_irb.setEnabled(False)
        rb_securitisation_std.setChecked(True)
        for rb in (rb_securitisation_std, rb_securitisation_ext, rb_securitisation_irb, rb_securitisation_iaa):
            bg_securitisation.addButton(rb)
            layout_ctrl.addWidget(rb)

        rb_securitisation_std.toggled.connect(self.on_securitisation_std_clicked)
        rb_securitisation_ext.toggled.connect(self.on_securitisation_ext_clicked)
        rb_securitisation_iaa.toggled.connect(self.on_securitisation_iaa_clicked)
        rb_securitisation_irb.toggled.connect(self.on_securitisation_irb_clicked)

        lbl_central = QLabel("Exposures to Central Counterparties")
        font_central = lbl_central.font()
        font_central.setBold(True)
        lbl_central.setFont(font_central)
        layout_ctrl.addWidget(lbl_central)

        bg_central = QButtonGroup(self)
        rb_central = QRadioButton("Default Approach")
        rb_central.setChecked(True)
        bg_central.addButton(rb_central)
        layout_ctrl.addWidget(rb_central)

        rb_central.toggled.connect(self.on_central_clicked)

        lbl_unsettled = QLabel("Unsettled Transactions & Failed Trades")
        font_unsettled = lbl_unsettled.font()
        font_unsettled.setBold(True)
        lbl_unsettled.setFont(font_unsettled)
        layout_ctrl.addWidget(lbl_unsettled)

        bg_unsettled = QButtonGroup(self)
        rb_unsettled = QRadioButton("Default Approach")
        rb_unsettled.setChecked(True)
        bg_unsettled.addButton(rb_unsettled)
        layout_ctrl.addWidget(rb_unsettled)

        rb_unsettled.toggled.connect(self.on_unsettled_clicked)

        self.ctrl_group.setLayout(layout_ctrl)

        # Data display
        self.data_display = QTextBrowser()

        # Create a layout for the control panel and data display
        layout = QHBoxLayout()
        layout.addWidget(ctrl_panel)
        layout.addWidget(self.data_display)
        self.setLayout(layout)

        placeholder_text = """
        """
        self.update_data_display(placeholder_text)

    def update_data_display(self, text):
        self.data_display.setText(text)

    def on_banking_std_clicked(self, checked):
        pass

    def on_banking_irb_clicked(self, checked):
        pass

    def on_counterparty_clicked(self, checked):
        pass

    def on_equity_lta_clicked(self, checked):
        pass

    def on_equity_mba_clicked(self, checked):
        pass

    def on_equity_fba_clicked(self, checked):
        pass

    def on_securitisation_std_clicked(self, checked):
        pass

    def on_securitisation_ext_clicked(self, checked):
        pass

    def on_securitisation_iaa_clicked(self, checked):
        pass

    def on_securitisation_irb_clicked(self, checked):
        pass

    def on_central_clicked(self, checked):
        pass

    def on_unsettled_clicked(self, checked):
        pass
