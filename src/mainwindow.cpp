#include "brms/mainwindow.h"
#include "QtWidgets/qgraphicslayout.h"
#include "ui_mainwindow.h"
#include <QFileDialog>
#include <QMessageBox>
#include <QScrollBar>
#include <QStyleFactory>
#include <QStyleHints>
#include <qDebug>

#include <QBarCategoryAxis>
#include <QBarSeries>
#include <QBarSet>
#include <QChart>
#include <QLegend>
#include <QStackedBarSeries>
#include <QValueAxis>

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

  // simulation progress bar
  // ui->progressBar->setStyle(QStyleFactory::create("Fusion"));
  ui->progressBar->setRange(0, m_yieldCurveWindow->dates().size());
  ui->progressBar->setValue(0);

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

  setupUiEquityEvolutionChart();
  setupUiCashFlowChart();
}

void MainWindow::setupUiEquityEvolutionChart() {
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

void MainWindow::setupUiCashFlowChart() {
  m_inflow = new QBarSet("Inflow");
  m_outflow = new QBarSet("Outflow");
  m_outflow->setColor(BRMS::RED);
  m_cf_series = new QStackedBarSeries;
  m_cf_series->append(m_inflow);
  m_cf_series->append(m_outflow);
  auto zeroLine = new QLineSeries(this);
  zeroLine->setName("Reference Line");
  zeroLine->setColor(QColor(Qt::gray));
  for (int t = 0; t < 30; ++t) {
    zeroLine->append(QPoint(t, 0));
  }

  m_cashflowChart = new QChart;
  m_cashflowChart->addSeries(m_cf_series);
  m_cashflowChart->addSeries(zeroLine);
  QFont titleFont = QFont();
  titleFont.setWeight(QFont::Weight::Bold);
  m_cashflowChart->setTitleFont(titleFont);
  m_cashflowChart->layout()->setContentsMargins(0, 0, 0, 0);
  m_cashflowChart->setTitle("30-Day Cashflow Projection");
  m_cashflowChart->setAnimationOptions(QChart::NoAnimation);
  m_cashflowChart->legend()->hide();

  m_cashflowAxisX = new QBarCategoryAxis;
  m_cashflowAxisY = new QValueAxis;
  m_cashflowAxisY->setTickAnchor(0.0);
  m_cashflowAxisY->setGridLineVisible(true);
  m_cashflowChart->addAxis(m_cashflowAxisX, Qt::AlignBottom);
  m_cashflowChart->addAxis(m_cashflowAxisY, Qt::AlignLeft);
  m_cf_series->attachAxis(m_cashflowAxisX);
  m_cf_series->attachAxis(m_cashflowAxisY);
  zeroLine->attachAxis(m_cashflowAxisX);
  zeroLine->attachAxis(m_cashflowAxisY);

  m_cashflowChartView = new QChartView(m_cashflowChart);

  updateCashFlowChart();
  ui->gridLayout->replaceWidget(ui->placeholderCashFlowChartView,
                                m_cashflowChartView);
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

  connect(ui->checkBoxHideMatured, &QCheckBox::checkStateChanged, this,
          &MainWindow::updateUi);

  // history
  connect(m_bank->liabilities(), &BankLiabilities::withdrawPaymentMade,
          ui->textBrowser, [this](QString name, double amount) {
            QString text(
                "[%1] <span style=\"text-decoration:underline\">%2</span> "
                "matured. Cash <font "
                "style=\"color:#A6192E\">-%3</font><br>");
            text = text.arg(m_todayInSimulation.toString("dd MMM yyyy"));
            text = text.arg(name);
            text = text.arg(m_locale.toString(amount, 'f', 2));
            ui->textBrowser->insertHtml(text);
          });
  connect(m_bank->liabilities(), &BankLiabilities::interestPaymentMade,
          ui->textBrowser, [this](QString name, double amount) {
            QString text(
                "[%1] <span style=\"text-decoration:underline\">%2</span> "
                "interest payment made. Cash <font "
                "style=\"color:#A6192E\">-%3</font><br>");
            text = text.arg(m_todayInSimulation.toString("dd MMM yyyy"));
            text = text.arg(name);
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
  connect(m_bank->assets(), &BankAssets::treasurySecurityPaymentReceived,
          ui->textBrowser, [this](QString name, double amount) {
            QString text(
                "[%1] <span style=\"text-decoration:underline\">%2</span> "
                "interest payment received. Cash <font "
                "style=\"color:#009174\">+%3</font><br>");
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
  delete m_cf_series;
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

void MainWindow::updateCashFlowChart() {
  QStringList m_categories;
  m_inflow->remove(0, m_inflow->count());
  m_outflow->remove(0, m_outflow->count());
  auto dates = m_yieldCurveWindow->dates();
  auto inflows = m_bank->assets()->cashflows(dates);
  auto outflows = m_bank->liabilities()->cashflows(dates);
  qreal maxY = -100, minY = 100;
  int days = 0, maxDays = 30;
  for (size_t i = 0; i < dates.size(); i++) {
    if ((dates[i] < m_todayInSimulation) | (days >= maxDays))
      continue;
    // m_categories.append(QString::number(m_todayInSimulation.daysTo(dates[i])));
    // m_categories.append(dates[i].toString("dd MMM"));
    m_categories.append(QString::number(days));
    *m_inflow << inflows[i];
    *m_outflow << -outflows[i];
    maxY = maxY < inflows[i] ? inflows[i] : maxY;
    minY = minY > -outflows[i] ? -outflows[i] : minY;
    days++;
  }
  auto maxVal = maxY > -minY ? maxY : -minY;
  m_cashflowAxisX->clear();
  m_cashflowAxisX->append(m_categories);
  m_cashflowAxisY->setRange(-maxVal, maxVal);
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
  // updateCashflowChart();
  updateCashFlowChart();
  updateUi();

  // always showing the latest
  QScrollBar *sb = ui->textBrowser->verticalScrollBar();
  sb->setValue(sb->maximum());

  // update progress bar
  ui->progressBar->setValue(ui->progressBar->value() + 1);
}

void MainWindow::updateUi() {
  // hide matured instruments
  bool hideMatured = ui->checkBoxHideMatured->isChecked();
  auto treeviews = {ui->assetsTreeView, ui->liabilitiesTreeView};
  for (auto &v : treeviews) {
    TreeModel *model = static_cast<TreeModel *>(v->model());
    for (int i = 0; i < model->rowCount(); ++i) {
      auto index = model->index(i, 0);
      auto item = model->getItem(index);
      for (int j = 0; j < item->childCount(); ++j) {
        auto instrument = item->child(j);
        if (instrument->data(TreeColumn::Value) == 0)
          v->setRowHidden(j, index, hideMatured);
      }
    }
  }
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
