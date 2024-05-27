#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include "yieldcurvewindow.h"
#include <QMainWindow>

QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE

class MainWindow : public QMainWindow {
  Q_OBJECT

public:
  MainWindow(QWidget *parent = nullptr);
  ~MainWindow();
  void showYieldCurve();
  void importYieldCurveData();

private:
  Ui::MainWindow *ui;
  YieldCurveWindow *m_yieldCurveWindow;
};
#endif // MAINWINDOW_H
