#include "brms/mainwindow.h"

#include <QApplication>

const auto appName = "BRMS - Bank Risk Management Simulation";

int main(int argc, char *argv[]) {
  QApplication a(argc, argv);
  MainWindow w;
  w.setWindowTitle(appName);
  w.show();
  w.showYieldCurve();
  return a.exec();
}
