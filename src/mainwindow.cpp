#include "brms/mainwindow.h"
#include "ui_mainwindow.h"
#include <QFileDialog>
#include <QMessageBox>
#include <qDebug>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), ui(new Ui::MainWindow) {
  setupUi();
  setupConnection();
}

void MainWindow::setupUi() {
  ui->setupUi(this);
  m_yieldCurveWindow = new YieldCurveWindow();
  m_yieldCurveWindow->importYieldCurveData(":/resources/par_yields.csv");

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
  m_equityChart->addSeries(m_equitySeries);

  m_axisX = new QDateTimeAxis();
  m_axisY = new QValueAxis();
  m_axisX->setTickCount(5);
  m_axisX->setFormat("dd MMM yyyy");

  m_equityChart->addAxis(m_axisX, Qt::AlignBottom);
  m_equityChart->addAxis(m_axisY, Qt::AlignLeft);
  m_equityChart->legend()->hide();

  m_equitySeries->attachAxis(m_axisX);
  m_equitySeries->attachAxis(m_axisY);

  m_equityChart->setTitle("Bank Equity Value");
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
  // connect(ui->buyTreasuryPushButton, &QPushButton::clicked, this,
  //         &MainWindow::buyTreasury);
}

MainWindow::~MainWindow() {
  delete ui;
  delete m_bank;
  delete m_equitySeries;
  delete m_equityChart;
  delete m_chartView;
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
}

void MainWindow::setTodaysDateLabel() {
  ui->dateInSimulationLabel->setText(
      QString("Today's date in simulation: %1")
          .arg(m_todayInSimulation.toString("MMM dd, yyyy")));
}

void MainWindow::showYieldCurve() {
  m_yieldCurveWindow->show();
  m_yieldCurveWindow->raise();
  m_yieldCurveWindow->setWindowState(Qt::WindowState::WindowActive);
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
