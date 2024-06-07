#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include "bank.h"
#include "yieldcurvewindow.h"
#include <QBarCategoryAxis>
#include <QBarSet>
#include <QMainWindow>
#include <QStackedBarSeries>

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

  /**
   * @brief Sets up UI
   */
  void setupUi();

  /**
   * @brief Connects signals and slots
   */
  void setupConnection();

  /**
   * @brief Set the Todays Date Label object
   */
  void setTodaysDateLabel();

  /**
   * @brief Shows the Yield Curve Window
   */
  void showYieldCurve();

  /**
   * @brief Imports yield curve data
   */
  void importYieldCurveData();

protected:
  void closeEvent(QCloseEvent *event) override;

private:
  Ui::MainWindow *ui;
  QDate m_todayInSimulation;
  Bank *m_bank;
  YieldCurveWindow *m_yieldCurveWindow;
  QLocale m_locale;

  // equity volution chart
  QLineSeries *m_equitySeries;
  QChart *m_equityChart;
  QChartView *m_chartView;
  QDateTimeAxis *m_axisX;
  QValueAxis *m_axisY;

  // cashflow chart
  QBarSet *m_inflow, *m_outflow;
  QStackedBarSeries *m_cf_series;
  QChart *m_cashflowChart;
  QChartView *m_cashflowChartView;
  QBarCategoryAxis *m_cashflowAxisX;
  QValueAxis *m_cashflowAxisY;

  void advanceToNextPeriodInSimulation();
  void setupUiEquityEvolutionChart();
  void setupUiCashFlowChart();
  void updateEquityEvolutionChart();
  void updateCashFlowChart();
  void updateUi();

  void toggleYieldCurveWindow();
  void toggleBalanceSheet();
  void toggleHistory();
  void restoreAllViews();
};

#endif // MAINWINDOW_H
