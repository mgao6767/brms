#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include "bank.h"
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
  void setTodaysDateLabel();
  void showYieldCurve();
  void importYieldCurveData();

signals:
  void simulationDateChanged();

private:
  Ui::MainWindow *ui;
  QDate m_todayInSimulation;
  Bank *m_bank;
  YieldCurveWindow *m_yieldCurveWindow;

  void advanceToNextPeriodInSimulation();
  void buyTreasury();
};
#endif // MAINWINDOW_H
