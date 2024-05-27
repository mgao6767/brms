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


private:
  Ui::YieldCurveWindow *ui;
  std::shared_ptr<YieldCurveDataModel> m_model;
  std::shared_ptr<QChart> m_chart;
  std::shared_ptr<QChartView> m_chartView;
  std::shared_ptr<QValueAxis> m_axisY;
  std::shared_ptr<QDateTimeAxis> m_axisX;
  std::shared_ptr<QHXYModelMapper> m_mapper;
  std::shared_ptr<QLineSeries> m_series;
  std::shared_ptr<QLineSeries> m_seriesZeroRates;

  const QuantLib::DayCounter m_zcBondsDayCounter =
      QuantLib::ActualActual(QuantLib::ActualActual::ISMA);
  const QuantLib::DayCounter m_termStructureDayCounter =
      QuantLib::ActualActual(QuantLib::ActualActual::ISMA);
  const QuantLib::Calendar m_calendar =
      QuantLib::UnitedStates(QuantLib::UnitedStates::GovernmentBond);
  std::vector<QuantLib::ext::shared_ptr<QuantLib::RateHelper>>
      m_bondInstruments;
  std::shared_ptr<
      QuantLib::PiecewiseYieldCurve<QuantLib::Discount, QuantLib::LogLinear>>
      m_yieldCurve;

  void changeYieldCurvePlot();
  void interpolateYieldCurve();
};

#endif // YIELDCURVEWINDOW_H
