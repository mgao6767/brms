#ifndef YIELDCURVEWINDOW_H
#define YIELDCURVEWINDOW_H

#include "brms/yieldcurvedatamodel.h"
#include <QChart>
#include <QChartView>
#include <QDateTimeAxis>
#include <QHXYModelMapper>
#include <QLineSeries>
#include <QVXYModelMapper>
#include <QValueAxis>
#include <QWidget>

#include <ql/qldefines.hpp>
#if !defined(BOOST_ALL_NO_LIB) && defined(BOOST_MSVC)
#include <ql/auto_link.hpp>
#endif
#include <ql/cashflows/couponpricer.hpp>
#include <ql/indexes/ibor/euribor.hpp>
#include <ql/indexes/ibor/usdlibor.hpp>
#include <ql/instruments/bonds/zerocouponbond.hpp>
#include <ql/pricingengines/bond/discountingbondengine.hpp>
#include <ql/termstructures/yield/bondhelpers.hpp>
#include <ql/termstructures/yield/piecewiseyieldcurve.hpp>
#include <ql/time/calendars/unitedstates.hpp>
#include <ql/time/daycounters/actual360.hpp>
#include <ql/time/daycounters/actualactual.hpp>

namespace Ui {
class YieldCurveWindow;
}

class YieldCurveWindow : public QWidget {
  Q_OBJECT

public:
  explicit YieldCurveWindow(QWidget *parent = nullptr);
  ~YieldCurveWindow();
  void importYieldCurveData(QString filePath);
  std::vector<QDate> &dates();
  void advanceToDate(QDate date);
  const QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine> &
  bondEngine();

private:
  Ui::YieldCurveWindow *ui;
  QDate m_today;
  YieldCurveDataModel *m_model;
  QChart *m_chart;
  QChartView *m_chartView;
  QValueAxis *m_axisY;
  QDateTimeAxis *m_axisX;
  QHXYModelMapper *m_mapper;
  QLineSeries *m_series;
  QLineSeries *m_seriesZeroRates;

  const QuantLib::DayCounter m_zcBondsDayCounter =
      QuantLib::ActualActual(QuantLib::ActualActual::ISMA);
  const QuantLib::DayCounter m_termStructureDayCounter =
      QuantLib::ActualActual(QuantLib::ActualActual::ISMA);
  const QuantLib::Calendar m_calendar =
      QuantLib::UnitedStates(QuantLib::UnitedStates::GovernmentBond);
  std::vector<QuantLib::ext::shared_ptr<QuantLib::RateHelper>>
      m_bondInstruments;
  QuantLib::ext::shared_ptr<
      QuantLib::PiecewiseYieldCurve<QuantLib::Discount, QuantLib::LogLinear>>
      m_yieldCurve;
  // Term structures that will be used for pricing:
  // the one used for discounting cash flows
  QuantLib::RelinkableHandle<QuantLib::YieldTermStructure>
      m_discountingTermStructure;
  QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine> m_bondEngine;

  void changeYieldCurvePlot();
  void interpolateYieldCurve();

signals:
  void yieldCurveChanged(QDate today);
};

#endif // YIELDCURVEWINDOW_H
