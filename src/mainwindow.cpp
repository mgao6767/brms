#include "brms/mainwindow.h"
#include "ui_mainwindow.h"
#include <QMessageBox>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), ui(new Ui::MainWindow) {
  ui->setupUi(this);

  this->yieldCurveWindow = new YieldCurveWindow();

  connect(ui->actionAbout_Qt, &QAction::triggered, this,
          [&]() { QMessageBox::aboutQt(this, "About Qt"); });
  connect(ui->actionYield_Curve, &QAction::triggered, this,
          &MainWindow::showYieldCurve);
}

MainWindow::~MainWindow() { delete ui; }

void MainWindow::showYieldCurve() {
  yieldCurveWindow->show();
  yieldCurveWindow->raise();
  yieldCurveWindow->setWindowState(Qt::WindowState::WindowActive);
}
