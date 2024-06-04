#include "brms/mainwindow.h"

#include <QApplication>
#include <QDebug>
#include <QDir>

const auto appName = "BRMS - Bank Risk Management Simulation";

int main(int argc, char *argv[]) {
  QApplication a(argc, argv);
  QDir::setCurrent(qApp->applicationDirPath());
  qDebug() << a.applicationDirPath();

  MainWindow w;
  w.setWindowTitle(appName);
  w.show();
  return a.exec();
}
