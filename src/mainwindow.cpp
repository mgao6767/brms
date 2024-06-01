#include "brms/mainwindow.h"
#include "brms/treemodel.h"
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

  // placeholder
  QTreeView *view = ui->treeView;
  view->setModel(m_bank->assets()->model());
  view->expandAll();
  view->setAlternatingRowColors(true);
  for (int c = 0; c < m_bank->assets()->model()->columnCount(); ++c) {
    view->resizeColumnToContents(c);
  }

  // connect(this, SIGNAL(simulationDateChanged()), m_bank->m_assets,
  // SLOT(reprice()));
  connect(this, &MainWindow::simulationDateChanged, this, [&]() {
    this->m_bank->assets()->reprice();
    // this->ui->treeView->expandAll();
  });
}

MainWindow::~MainWindow() {
  delete ui;
  delete m_bank;
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
  emit simulationDateChanged();
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
