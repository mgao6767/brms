#include "brms/yieldcurvewindow.h"
#include "brms/utils.h"
#include "ui_yieldcurvewindow.h"
#include <QDateTime>
#include <QDebug>
#include <QGraphicsLayout>
#include <QGridLayout>
#include <QHeaderView>
#include <QTableView>

using namespace QuantLib;

void YieldCurveWindow::importYieldCurveData(QString filePath) {
  qDebug() << filePath;
  m_model->loadYieldsData(filePath);
  // hide all even rows, which store the maturity dates for plotting purpose
  for (int i = 0; i < m_model->rowCount(); i += 2)
    ui->tableView->hideRow(i);
  ui->tableView->selectRow(1);
}

YieldCurveWindow::YieldCurveWindow(QWidget *parent)
    : QWidget(parent), ui(new Ui::YieldCurveWindow) {
  qDebug() << "Init Yield Curve Window";
  ui->setupUi(this);

  m_model = new YieldCurveDataModel();
  m_chart = new QChart();
  m_series = new QLineSeries();
  m_mapper = new QHXYModelMapper(this);
  m_axisX = new QDateTimeAxis();
  m_axisY = new QValueAxis();
  m_chartView = new QChartView(m_chart, this);
  m_seriesZeroRates = new QLineSeries();
  // Pricing engine
  m_bondEngine =
      ext::make_shared<DiscountingBondEngine>(m_discountingTermStructure);

  // setup table view
  ui->tableView->setModel(m_model);
  ui->tableView->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
  ui->tableView->horizontalHeader()->setDefaultAlignment(Qt::AlignRight);
  ui->tableView->verticalHeader()->setSectionResizeMode(QHeaderView::Stretch);
  ui->tableView->setSelectionMode(QAbstractItemView::SingleSelection);
  ui->tableView->setSelectionBehavior(QAbstractItemView::SelectRows);
  ui->tableView->setEditTriggers(QAbstractItemView::NoEditTriggers);

  // hide all even rows, which store the maturity dates for plotting purpose
  for (int i = 0; i < m_model->rowCount(); i += 2)
    ui->tableView->hideRow(i);

  // axes
  m_axisX->setTickCount(10);
  m_axisX->setFormat("MMM yyyy");
  m_axisX->setTitleText("Maturity Date");
  m_axisY->setRange(0, 7); // 0% to 7%
  m_axisY->setLabelFormat("%.2f%");
  // m_axisY->setTitleText("Rate");

  // mapper from model to view
  m_mapper->setXRow(0);
  m_mapper->setYRow(1);
  m_mapper->setSeries(m_series);
  m_mapper->setModel(m_model);

  // setup chart
  m_chart->addSeries(m_series);
  m_chart->addSeries(m_seriesZeroRates);

  m_chart->addAxis(m_axisX, Qt::AlignBottom);
  m_chart->addAxis(m_axisY, Qt::AlignLeft);
  m_chart->setAnimationOptions(QChart::SeriesAnimations);

  // series of official par yields
  // attach axes after they are added to the chart
  m_series->setName("Par Yield Curve");
  m_series->attachAxis(m_axisX);
  m_series->attachAxis(m_axisY);

  m_seriesZeroRates->setName("Interpolated Zero Rate");
  m_seriesZeroRates->attachAxis(m_axisX);
  m_seriesZeroRates->attachAxis(m_axisY);

  // aesthetics
  QFont titleFont = QFont();
  titleFont.setWeight(QFont::Weight::Bold);
  m_chart->setTitleFont(titleFont);
  m_chart->layout()->setContentsMargins(0, 0, 0, 0);
  m_chartView->setRenderHint(QPainter::Antialiasing);

  // add the chart to the window
  ui->chartGridLayout->replaceWidget(ui->chartPlaceholderWidget, m_chartView);

  // connect signals
  connect(ui->tableView->selectionModel(),
          &QItemSelectionModel::selectionChanged, this,
          &YieldCurveWindow::changeYieldCurvePlot);

  qDebug() << "Done init Yield Curve Window";
}

YieldCurveWindow::~YieldCurveWindow() {
  delete ui;
  delete m_model;
  delete m_axisX;
  delete m_axisY;
  delete m_seriesZeroRates;
}

std::vector<QDate> &YieldCurveWindow::dates() { return m_model->dates(); }

void YieldCurveWindow::changeYieldCurvePlot() {
  // get selected row(s) but only single row selection is allowed
  QModelIndexList selection = ui->tableView->selectionModel()->selectedRows();
  QModelIndex index = selection[0];
  // change mapper to update the chart of official par yields
  m_mapper->setXRow(index.row() - 1);
  m_mapper->setYRow(index.row());
  // update chart title
  QDate date = m_model->headerData(index.row(), Qt::Vertical).toDate();
  QString dateString = date.toString("MMM dd, yyyy");
  QString title = "Yield Curve as at %1";
  m_chart->setTitle(title.arg(dateString));
  // update x axis
  QDateTime minDateTime, maxDateTime;
  minDateTime.setDate(date);
  maxDateTime.setDate(date.addYears(30)); // max is 30yr
  m_axisX->setRange(minDateTime, maxDateTime);
  // update y axis?
  if (ui->checkBox_AdjustYaxis->isChecked()) {
    qreal maxY = -100;
    for (auto &p : m_series->points()) {
      maxY = maxY < p.y() ? p.y() : maxY;
    }
    m_axisY->setRange(0, maxY + 1);
  }
  interpolateYieldCurve();
  m_today = date;
  emit yieldCurveChanged(date);
}

void YieldCurveWindow::advanceToDate(QDate date) {
  auto dates = this->dates();
  for (int i = 0; i < dates.size(); ++i) {
    if (date == dates[i]) {
      ui->tableView->selectRow(i * 2 + 1);
      break;
    }
  }
}

void YieldCurveWindow::interpolateYieldCurve() {

  // get the selected row
  QModelIndexList selection = ui->tableView->selectionModel()->selectedRows();
  QModelIndex index = selection[0];
  QDate today = m_model->headerData(index.row(), Qt::Vertical).toDate();

  // QuantLib at work
  Date todaysDate = qDateToQLDate(today);
  Integer fixingDays = 0;
  Integer settlementDays = 0;
  Date settlementDate = todaysDate + settlementDays * Days;

  // set evaluation date
  Settings::instance().evaluationDate() = todaysDate;

  m_bondInstruments.clear();

  // ZCB
  for (int col = 0; col < 6; ++col) {
    QModelIndex i = index.siblingAtColumn(col);
    QVariant d = m_model->data(i);
    if (qIsNaN(d.toDouble()))
      continue;
    auto rate = ext::make_shared<SimpleQuote>(d.toDouble() / 100);
    Period mat;
    switch (col + 1) {
    case 1:
      mat = 1 * Months;
      break;
    case 2:
      mat = 2 * Months;
      break;
    case 3:
      mat = 3 * Months;
      break;
    case 4:
      mat = 4 * Months;
      break;
    case 5:
      mat = 6 * Months;
      break;
    case 6:
      mat = 1 * Years;
      break;
    }
    auto helper = ext::make_shared<DepositRateHelper>(
        Handle<Quote>(rate), mat, fixingDays, m_calendar, ModifiedFollowing,
        true, m_zcBondsDayCounter);

    m_bondInstruments.push_back(helper);
  };

  // Coupon bonds
  // std::vector<RelinkableHandle<Quote>> quoteHandle;
  for (int col = 6; col < 13; ++col) {
    QModelIndex i = index.siblingAtColumn(col);
    QVariant d = m_model->data(i);
    if (qIsNaN(d.toDouble()))
      continue;
    Period mat;
    switch (col + 1) {
    case 7:
      mat = 2 * Years;
      break;
    case 8:
      mat = 3 * Years;
      break;
    case 9:
      mat = 5 * Years;
      break;
    case 10:
      mat = 7 * Years;
      break;
    case 11:
      mat = 10 * Years;
      break;
    case 12:
      mat = 20 * Years;
      break;
    case 13:
      mat = 30 * Years;
      break;
    }
    // Coupon bonds
    Real marketQuote = 100.0, redemption = 100.0;

    // RelinkableHandle<Quote> handle;
    // quoteHandle.push_back(handle);
    // quoteHandle.back().linkTo(ext::make_shared<SimpleQuote>(marketQuote));

    Schedule schedule(settlementDate, settlementDate + mat, Period(Semiannual),
                      UnitedStates(UnitedStates::GovernmentBond), Unadjusted,
                      Unadjusted, DateGeneration::Backward, false);

    auto bondHelper = ext::make_shared<FixedRateBondHelper>(
        // quoteHandle.back()
        Handle<Quote>(ext::make_shared<SimpleQuote>(marketQuote)),
        settlementDays, 100.0, schedule,
        std::vector<Rate>(1, d.toDouble() / 100),
        ActualActual(ActualActual::ISMA), Unadjusted, redemption,
        settlementDate);

    m_bondInstruments.push_back(bondHelper);
  };

  // curve building
  m_yieldCurve = ext::make_shared<PiecewiseYieldCurve<Discount, LogLinear>>(
      settlementDate, m_bondInstruments, m_termStructureDayCounter);

  // interpolated zero curve
  m_seriesZeroRates->clear();
  for (int d = 0; d < 30 * 12; ++d) {
    auto date = settlementDate + d * Months;
    // effective annual rate
    if (date > m_yieldCurve->maxDate())
      continue;
    auto r = m_yieldCurve->zeroRate(date, m_termStructureDayCounter, Compounded,
                                    Annual);
    // qDebug() << d << date.year() << date.month() << date.dayOfMonth() << r;
    QDate maturityDate(date.year(), date.month(), date.dayOfMonth());
    QDateTime maturityDateTime;
    maturityDateTime.setDate(maturityDate);
    m_seriesZeroRates->append(maturityDateTime.toMSecsSinceEpoch(), r * 100);
  }

  m_discountingTermStructure.linkTo(m_yieldCurve);
}

const QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine> &
YieldCurveWindow::bondEngine() {
  return m_bondEngine;
};
