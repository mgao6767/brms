#include "brms/mainwindow.h"
#include "QtWidgets/qgraphicslayout.h"
#include "ui_mainwindow.h"
#include <QFileDialog>
#include <QMessageBox>
#include <QScrollBar>
#include <QStyleHints>
#include <qDebug>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), ui(new Ui::MainWindow) {
  m_locale = QLocale::system();
  setupUi();
  setupConnection();
}

void MainWindow::setupUi() {
  ui->setupUi(this);
  m_yieldCurveWindow = new YieldCurveWindow();
  m_yieldCurveWindow->importYieldCurveData(":/resources/par_yields.csv");
  ui->gridLayout_YieldCurve->replaceWidget(ui->placeholderYieldCurveWindow,
                                           m_yieldCurveWindow);

  // by default, simulation starts from the first day
  m_todayInSimulation = m_yieldCurveWindow->dates()[0];
  setTodaysDateLabel();

  // setup the bank
  m_bank = new Bank();
  m_bank->assets()->setTreasuryPricingEngine(m_yieldCurveWindow->bondEngine());
  m_bank->init(m_todayInSimulation); // init with fake data

  // tree view
  ui->assetsTreeView->setModel(m_bank->assets()->model());
  ui->liabilitiesTreeView->setModel(m_bank->liabilities()->model());
  ui->equityTreeView->setModel(m_bank->equity()->model());
  auto views = {ui->assetsTreeView, ui->liabilitiesTreeView,
                ui->equityTreeView};
  for (auto &view : views) {
    view->hideColumn(TreeColumn::Ref);
    view->hideColumn(TreeColumn::BackgroundColor);
    view->expandAll();
    view->setAlternatingRowColors(true);
    for (int c = 0; c < TreeColumn::Value; ++c) {
      view->resizeColumnToContents(c);
    }
  }

  // equity evolution
  m_equityChart = new QChart();
  m_equitySeries = new QLineSeries();
  m_chartView = new QChartView(m_equityChart);
  // check if the system is using dark theme?
  if (QGuiApplication::styleHints()->colorScheme() == Qt::ColorScheme::Dark) {
    m_chartView->chart()->setTheme(QChart::ChartThemeDark);
  }
  m_equityChart->addSeries(m_equitySeries);

  m_axisX = new QDateTimeAxis();
  m_axisY = new QValueAxis();
  m_axisX->setTickCount(5);
  m_axisX->setFormat("dd MMM yyyy");
  m_axisY->setLabelFormat("%.0f");

  m_equityChart->addAxis(m_axisX, Qt::AlignBottom);
  m_equityChart->addAxis(m_axisY, Qt::AlignLeft);
  m_equityChart->legend()->hide();

  m_equitySeries->attachAxis(m_axisX);
  m_equitySeries->attachAxis(m_axisY);

  QFont titleFont = QFont();
  titleFont.setWeight(QFont::Weight::Bold);
  m_equityChart->setTitleFont(titleFont);
  m_equityChart->layout()->setContentsMargins(0, 0, 0, 0);
  m_equityChart->setTitle("Bank Equity Value");
  m_equityChart->setAnimationOptions(QChart::SeriesAnimations);
  m_chartView->setRenderHint(QPainter::Antialiasing);

  QDateTime dt;
  dt.setDate(m_todayInSimulation);
  m_axisX->setMin(dt); // starting date
  updateEquityEvolutionChart();

  ui->gridLayout->replaceWidget(ui->placeholderChartView, m_chartView);
}

void MainWindow::setupConnection() {

  connect(ui->actionAbout_Qt, &QAction::triggered, this,
          [&]() { QMessageBox::aboutQt(this, "About Qt"); });
  connect(ui->actionYield_Curve, &QAction::triggered, this,
          &MainWindow::showYieldCurve);
  connect(ui->actionImport_yield_curve_data, &QAction::triggered, this,
          &MainWindow::importYieldCurveData);
  connect(ui->nextPeriodPushButton, &QPushButton::clicked, this,
          &MainWindow::advanceToNextPeriodInSimulation);

  // views
  connect(ui->actionYield_Curve, &QAction::triggered, this,
          &MainWindow::toggleYieldCurveWindow);
  connect(ui->dockWidget_YieldCurve, &QDockWidget::visibilityChanged, this,
          [&]() {
            ui->actionYield_Curve->setChecked(
                ui->dockWidget_YieldCurve->isVisible());
          });
  connect(ui->actionBalance_Sheet, &QAction::triggered, this,
          &MainWindow::toggleBalanceSheet);
  connect(ui->dockWidget_BalanceSheet, &QDockWidget::visibilityChanged, this,
          [&]() {
            ui->actionBalance_Sheet->setChecked(
                ui->dockWidget_BalanceSheet->isVisible());
          });
  connect(ui->actionHistory, &QAction::triggered, this,
          &MainWindow::toggleHistory);
  connect(ui->dockWidget_History, &QDockWidget::visibilityChanged, this, [&]() {
    ui->actionHistory->setChecked(ui->dockWidget_History->isVisible());
  });
  connect(ui->actionRestore, &QAction::triggered, this,
          &MainWindow::restoreAllViews);

  // history
  connect(m_bank->liabilities(), &BankLiabilities::interestPaymentToMake,
          ui->textBrowser, [this](double amount) {
            QString text("[%1] Interest payment or withdrawal on deposits. "
                         "Cash <font style=\"color:#A6192E\">-%2</font><br>");
            text = text.arg(m_todayInSimulation.toString("dd MMM yyyy"));
            text = text.arg(m_locale.toString(amount, 'f', 2));
            ui->textBrowser->insertHtml(text);
          });
  connect(m_bank->assets(), &BankAssets::treasurySecurityMatured,
          ui->textBrowser, [this](QString name, double amount) {
            QString text(
                "[%1] <span style=\"text-decoration:underline\">%2</span> "
                "matured. Cash <font style=\"color:#009174\">+%3</font><br>");
            text = text.arg(m_todayInSimulation.toString("dd MMM yyyy"));
            text = text.arg(name);
            text = text.arg(m_locale.toString(amount, 'f', 2));
            ui->textBrowser->insertHtml(text);
          });
  connect(m_bank->assets(), &BankAssets::loanAmortizingPaymentReceived,
          ui->textBrowser, [this](QString name, double amount) {
            QString text(
                "[%1] <span style=\"text-decoration:underline\">%2</span> "
                "amortizing payment received. Cash <font "
                "style=\"color:#009174\">+%3</font><br>");
            text = text.arg(m_todayInSimulation.toString("dd MMM yyyy"));
            text = text.arg(name);
            text = text.arg(m_locale.toString(amount, 'f', 2));
            ui->textBrowser->insertHtml(text);
          });
}

MainWindow::~MainWindow() {
  delete ui;
  delete m_bank;
  delete m_equitySeries;
  // delete m_equityChart;
  // delete m_chartView; // will be deleted by ui
  delete m_axisX;
  delete m_axisY;
}

void MainWindow::updateEquityEvolutionChart() {
  QDateTime dt;
  dt.setDate(m_todayInSimulation);
  m_equitySeries->append(dt.toMSecsSinceEpoch(),
                         m_bank->equity()->totalEquity());
  dt.setDate(m_todayInSimulation.addDays(10));
  m_axisX->setMax(dt);
  // update y axis?
  qreal maxY = -100;
  for (auto &p : m_equitySeries->points()) {
    maxY = maxY < p.y() ? p.y() : maxY;
  }
  m_axisY->setRange(0, maxY * 1.05);
}

void MainWindow::advanceToNextPeriodInSimulation() {
  auto dates = m_yieldCurveWindow->dates();
  auto it = std::find(dates.begin(), dates.end(), m_todayInSimulation);
  // simulation should end
  if (it == dates.end())
    return;
  // advance to next date
  m_todayInSimulation = dates[std::distance(dates.begin(), it) + 1];
  m_yieldCurveWindow->advanceToDate(m_todayInSimulation);
  setTodaysDateLabel();

  m_bank->reprice();
  updateEquityEvolutionChart();

  // always showing the latest
  QScrollBar *sb = ui->textBrowser->verticalScrollBar();
  sb->setValue(sb->maximum());
}

void MainWindow::setTodaysDateLabel() {
  QString text = QString("Today's date in simulation: %1")
                     .arg(m_todayInSimulation.toString("MMM dd, yyyy"));
  ui->statusbar->showMessage(text);
}

void MainWindow::showYieldCurve() {
  ui->dockWidget_YieldCurve->show();
  addDockWidget(Qt::DockWidgetArea::TopDockWidgetArea,
                ui->dockWidget_YieldCurve);
}

void MainWindow::importYieldCurveData() {
  QFileDialog dialog(this);
  dialog.setFileMode(QFileDialog::AnyFile);
  dialog.setViewMode(QFileDialog::Detail);
  QStringList fileNames;
  if (dialog.exec())
    fileNames = dialog.selectedFiles();
  if (fileNames.isEmpty())
    return;
  m_yieldCurveWindow->importYieldCurveData(fileNames[0]);
}

void MainWindow::closeEvent(QCloseEvent *event) {
  foreach (QWidget *widget, QApplication::topLevelWidgets()) {
    if (widget == this)
      continue;
    widget->close();
  }
  event->accept();
  QMainWindow::closeEvent(event);
}

void MainWindow::toggleYieldCurveWindow() {
  if (ui->actionYield_Curve->isChecked()) {
    ui->dockWidget_YieldCurve->show();
  } else {
    ui->dockWidget_YieldCurve->hide();
  }
}

void MainWindow::toggleBalanceSheet() {
  if (ui->actionBalance_Sheet->isChecked()) {
    ui->dockWidget_BalanceSheet->show();
  } else {
    ui->dockWidget_BalanceSheet->hide();
  }
}

void MainWindow::toggleHistory() {
  if (ui->actionHistory->isChecked()) {
    ui->dockWidget_History->show();
  } else {
    ui->dockWidget_History->hide();
  }
}

void MainWindow::restoreAllViews() {
  auto widgets = {ui->dockWidget_BalanceSheet, ui->dockWidget_History,
                  ui->dockWidget_YieldCurve};
  for (auto &w : widgets) {
    w->show();
    w->setFloating(false);
  }
  addDockWidget(Qt::DockWidgetArea::LeftDockWidgetArea,
                ui->dockWidget_BalanceSheet);
  addDockWidget(Qt::DockWidgetArea::LeftDockWidgetArea, ui->dockWidget_History);
  addDockWidget(Qt::DockWidgetArea::TopDockWidgetArea,
                ui->dockWidget_YieldCurve);
}
