#include "brms/treasuryfutures.h"
#include "brms/utils.h"

using namespace QuantLib;

TreasuryFuturesModel::TreasuryFuturesModel(QObject *parent)
    : QAbstractTableModel{parent} {
  m_locale = QLocale::system();
}

int TreasuryFuturesModel::rowCount(const QModelIndex &parent) const {
  Q_UNUSED(parent);
  //   return m_treasuryFutures.size();
  return 6 * 4;
}

int TreasuryFuturesModel::columnCount(const QModelIndex &parent) const {
  Q_UNUSED(parent);
  return 4;
}

QVariant TreasuryFuturesModel::headerData(int section,
                                          Qt::Orientation orientation,
                                          int role) const {
  if (role != Qt::DisplayRole)
    return QVariant();
  if (orientation == Qt::Horizontal) {
    switch (section) {
    case 0:
      return "Contract";
      break;
    case 1:
      return "Maturity";
      break;
    case 2:
      return "Face Value";
      break;
    case 3:
      return "Price";
      break;
    }
  }
  return QVariant();
}

/**
 * @brief Computes the next quarter-end date given a QDate.
 * @param date The input date.
 * @return The next quarter-end date.
 */
inline QDate nextQuarterEnd(const QDate &date) {
    int month = date.month();
    int year = date.year();

    if (month <= 3) {
        // Q1 ends on March 31
        return QDate(year, 3, 31);
    } else if (month <= 6) {
        // Q2 ends on June 30
        return QDate(year, 6, 30);
    } else if (month <= 9) {
        // Q3 ends on September 30
        return QDate(year, 9, 30);
    } else {
        // Q4 ends on December 31
        return QDate(year, 12, 31);
    }
}

/**
 * @brief Computes the next quarter-end date given a QDate,
 *        accounting for the case where the date is already a quarter-end.
 * @param date The input date.
 * @return The next quarter-end date.
 */
inline QDate nextQuarterEndInclusive(const QDate &date) {
    QDate nextEnd = nextQuarterEnd(date);

    // If the date is exactly on the quarter-end, compute the next quarter-end
    if (date == nextEnd) {
        int month = nextEnd.month();
        int year = nextEnd.year();

        if (month == 3) {
            return QDate(year, 6, 30);
        } else if (month == 6) {
            return QDate(year, 9, 30);
        } else if (month == 9) {
            return QDate(year, 12, 31);
        } else {
            // month == 12
            return QDate(year + 1, 3, 31);
        }
    }

    return nextEnd;
}

QVariant TreasuryFuturesModel::data(const QModelIndex &index, int role) const {
  if (role != Qt::DisplayRole)
    return QVariant();
  QuantLib::Date todayQL = QuantLib::Settings::instance().evaluationDate();
  QDate today = qlDateToQDate(todayQL);
  QDate tp1qtr = nextQuarterEnd(today);
  QDate tp2qtr = nextQuarterEndInclusive(tp1qtr);
  QDate tp3qtr = nextQuarterEndInclusive(tp2qtr);
  QDate tp4qtr = nextQuarterEndInclusive(tp3qtr);

  switch (index.column()) {
  case 0: // contract underlying
    if (index.row() < 4)
      return "2-Year T-Note";
    else if (index.row() < 8)
      return "3-Year T-Note";
    else if (index.row() < 12)
      return "5-Year T-Note";
    else if (index.row() < 16)
      return "10-Year T-Note";
    else if (index.row() < 20)
      return "20-Year T-Bond";
    else if (index.row() < 24)
      return "30-Year T-Bond";
    break;
  case 1: // maturity
    // today's Q1, Mar, Jun, Sep, Dec
    // today's Q2, Jun, Sep, Dec, Mar
    // today's Q3, Sep, Dec, Mar, Jun
    // today's Q4, Dec, Mar, Jun, Sep
    switch (index.row() % 4 + 1) {
    case 1:
      return tp1qtr.toString("MMM yyyy");
      break;
    case 2:
      return tp2qtr.toString("MMM yyyy");
      break;
    case 3:
      return tp3qtr.toString("MMM yyyy");
      break;
    case 4:
      return tp4qtr.toString("MMM yyyy");
      break;
    }
    break;
  case 2: // face amount
    if (index.row() < 4 * 2)
      return m_locale.toString(200000.0, 'f', 2);
    else
      return m_locale.toString(100000.0, 'f', 2);
    break;
  case 3: // price
    return m_locale.toString(100.0, 'f', 2);
    break;
  }
  return QVariant();
}

TreasuryFutures::TreasuryFutures() {
  m_model = new TreasuryFuturesModel();
  m_lastRepricingDate = QuantLib::Settings::instance().evaluationDate();
}

TreasuryFutures::~TreasuryFutures() { delete m_model; }

TreasuryFuturesModel *TreasuryFutures::model() { return m_model; }

void TreasuryFutures::reprice() {
  // TODO
  m_lastRepricingDate = QuantLib::Settings::instance().evaluationDate();
}
