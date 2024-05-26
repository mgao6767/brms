#include "brms/yieldcurvedatamodel.h"
#include <QColor>
#include <QList>
#include <QRandomGenerator>
#include <QRect>
#include <limits>

void YieldCurveDataModel::loadYieldsData() {
  // Official daily par yield data from the US Treasury
  // Only month-end yields are kept here
  const double nan = std::numeric_limits<double>::quiet_NaN();
  const int nDatesOfficialYields = 64;
  const int nOfficialYields = 13;
  // clang-format off
  double officialParYields[nDatesOfficialYields][nOfficialYields] = {
    {2.42, 2.43, 2.41, nan, 2.46, 2.55, 2.45, 2.43, 2.43, 2.51, 2.63, 2.83, 2.99},
    {2.44, 2.47, 2.45, nan, 2.50, 2.54, 2.52, 2.50, 2.52, 2.63, 2.73, 2.94, 3.09},
    {2.43, 2.44, 2.40, nan, 2.44, 2.40, 2.27, 2.21, 2.23, 2.31, 2.41, 2.63, 2.81},
    {2.43, 2.44, 2.43, nan, 2.46, 2.39, 2.27, 2.24, 2.28, 2.39, 2.51, 2.75, 2.93},
    {2.35, 2.38, 2.35, nan, 2.35, 2.21, 1.95, 1.90, 1.93, 2.03, 2.14, 2.39, 2.58},
    {2.18, 2.15, 2.12, nan, 2.09, 1.92, 1.75, 1.71, 1.76, 1.87, 2.00, 2.31, 2.52},
    {2.01, 2.07, 2.08, nan, 2.10, 2.00, 1.89, 1.84, 1.84, 1.92, 2.02, 2.31, 2.53},
    {2.10, 2.04, 1.99, nan, 1.89, 1.76, 1.50, 1.42, 1.39, 1.45, 1.50, 1.78, 1.96},
    {1.91, 1.87, 1.88, nan, 1.83, 1.75, 1.63, 1.56, 1.55, 1.62, 1.68, 1.94, 2.12},
    {1.59, 1.59, 1.54, nan, 1.57, 1.53, 1.52, 1.52, 1.51, 1.60, 1.69, 2.00, 2.17},
    {1.62, 1.60, 1.59, nan, 1.63, 1.60, 1.61, 1.61, 1.62, 1.73, 1.78, 2.07, 2.21},
    {1.48, 1.51, 1.55, nan, 1.60, 1.59, 1.58, 1.62, 1.69, 1.83, 1.92, 2.25, 2.39},
    {1.56, 1.57, 1.55, nan, 1.54, 1.45, 1.33, 1.30, 1.32, 1.42, 1.51, 1.83, 1.99},
    {1.45, 1.37, 1.27, nan, 1.11, 0.97, 0.86, 0.85, 0.89, 1.03, 1.13, 1.46, 1.65},
    {0.05, 0.12, 0.11, nan, 0.15, 0.17, 0.23, 0.29, 0.37, 0.55, 0.70, 1.15, 1.35},
    {0.10, 0.10, 0.09, nan, 0.11, 0.16, 0.20, 0.24, 0.36, 0.53, 0.64, 1.05, 1.28},
    {0.13, 0.14, 0.14, nan, 0.18, 0.17, 0.16, 0.19, 0.30, 0.50, 0.65, 1.18, 1.41},
    {0.13, 0.14, 0.16, nan, 0.18, 0.16, 0.16, 0.18, 0.29, 0.49, 0.66, 1.18, 1.41},
    {0.09, 0.09, 0.09, nan, 0.10, 0.11, 0.11, 0.11, 0.21, 0.39, 0.55, 0.98, 1.20},
    {0.08, 0.10, 0.11, nan, 0.13, 0.12, 0.14, 0.15, 0.28, 0.50, 0.72, 1.26, 1.49},
    {0.08, 0.08, 0.10, nan, 0.11, 0.12, 0.13, 0.16, 0.28, 0.47, 0.69, 1.23, 1.46},
    {0.08, 0.09, 0.09, nan, 0.11, 0.13, 0.14, 0.19, 0.38, 0.64, 0.88, 1.43, 1.65},
    {0.08, 0.08, 0.08, nan, 0.09, 0.11, 0.16, 0.19, 0.36, 0.62, 0.84, 1.37, 1.58},
    {0.08, 0.08, 0.09, nan, 0.09, 0.10, 0.13, 0.17, 0.36, 0.65, 0.93, 1.45, 1.65},
    {0.07, 0.07, 0.06, nan, 0.07, 0.10, 0.11, 0.19, 0.45, 0.79, 1.11, 1.68, 1.87},
    {0.04, 0.04, 0.04, nan, 0.05, 0.08, 0.14, 0.30, 0.75, 1.15, 1.44, 2.08, 2.17},
    {0.01, 0.01, 0.03, nan, 0.05, 0.07, 0.16, 0.35, 0.92, 1.40, 1.74, 2.31, 2.41},
    {0.01, 0.02, 0.01, nan, 0.03, 0.05, 0.16, 0.35, 0.86, 1.32, 1.65, 2.19, 2.30},
    {0.01, 0.01, 0.01, nan, 0.03, 0.05, 0.14, 0.30, 0.79, 1.24, 1.58, 2.18, 2.26},
    {0.05, 0.05, 0.05, nan, 0.06, 0.07, 0.25, 0.46, 0.87, 1.21, 1.45, 2.00, 2.06},
    {0.05, 0.05, 0.06, nan, 0.05, 0.07, 0.19, 0.35, 0.69, 1.00, 1.24, 1.81, 1.89},
    {0.03, 0.05, 0.04, nan, 0.06, 0.07, 0.20, 0.40, 0.77, 1.08, 1.30, 1.85, 1.92},
    {0.07, 0.05, 0.04, nan, 0.05, 0.09, 0.28, 0.53, 0.98, 1.32, 1.52, 2.02, 2.08},
    {0.06, 0.08, 0.05, nan, 0.07, 0.15, 0.48, 0.75, 1.18, 1.44, 1.55, 1.98, 1.93},
    {0.11, 0.05, 0.05, nan, 0.10, 0.24, 0.52, 0.81, 1.14, 1.36, 1.43, 1.85, 1.78},
    {0.06, 0.05, 0.06, nan, 0.19, 0.39, 0.73, 0.97, 1.26, 1.44, 1.52, 1.94, 1.90},
    {0.03, 0.13, 0.22, nan, 0.49, 0.78, 1.18, 1.39, 1.62, 1.75, 1.79, 2.17, 2.11},
    {0.06, 0.20, 0.35, nan, 0.69, 1.01, 1.44, 1.62, 1.71, 1.81, 1.83, 2.25, 2.17},
    {0.17, 0.35, 0.52, nan, 1.06, 1.63, 2.28, 2.45, 2.42, 2.40, 2.32, 2.59, 2.44},
    {0.37, 0.73, 0.85, nan, 1.41, 2.10, 2.70, 2.87, 2.92, 2.94, 2.89, 3.14, 2.96},
    {0.73, 0.89, 1.16, nan, 1.64, 2.08, 2.53, 2.71, 2.81, 2.87, 2.85, 3.28, 3.07},
    {1.28, 1.68, 1.72, nan, 2.51, 2.80, 2.92, 2.99, 3.01, 3.04, 2.98, 3.38, 3.14},
    {2.22, 2.28, 2.41, nan, 2.91, 2.98, 2.89, 2.83, 2.70, 2.70, 2.67, 3.20, 3.00},
    {2.40, 2.72, 2.96, nan, 3.32, 3.50, 3.45, 3.46, 3.30, 3.25, 3.15, 3.53, 3.27},
    {2.79, 3.20, 3.33, nan, 3.92, 4.05, 4.22, 4.25, 4.06, 3.97, 3.83, 4.08, 3.79},
    {3.73, 4.00, 4.22, 4.33, 4.57, 4.66, 4.51, 4.45, 4.27, 4.18, 4.10, 4.44, 4.22},
    {4.07, 4.25, 4.37, 4.55, 4.70, 4.74, 4.38, 4.13, 3.82, 3.76, 3.68, 4.00, 3.80},
    {4.12, 4.41, 4.42, 4.69, 4.76, 4.73, 4.41, 4.22, 3.99, 3.96, 3.88, 4.14, 3.97},
    {4.58, 4.64, 4.70, 4.74, 4.80, 4.68, 4.21, 3.90, 3.63, 3.59, 3.52, 3.78, 3.65},
    {4.65, 4.81, 4.88, 5.00, 5.17, 5.02, 4.81, 4.51, 4.18, 4.07, 3.92, 4.10, 3.93},
    {4.74, 4.79, 4.85, 4.97, 4.94, 4.64, 4.06, 3.81, 3.60, 3.55, 3.48, 3.81, 3.67},
    {4.35, 5.14, 5.10, 5.20, 5.06, 4.80, 4.04, 3.75, 3.51, 3.49, 3.44, 3.80, 3.67},
    {5.28, 5.37, 5.52, 5.53, 5.46, 5.18, 4.40, 4.04, 3.74, 3.69, 3.64, 4.01, 3.85},
    {5.24, 5.39, 5.43, 5.50, 5.47, 5.40, 4.87, 4.49, 4.13, 3.97, 3.81, 4.06, 3.85},
    {5.48, 5.54, 5.55, 5.56, 5.53, 5.37, 4.88, 4.51, 4.18, 4.08, 3.97, 4.22, 4.02},
    {5.52, 5.55, 5.56, 5.61, 5.48, 5.37, 4.85, 4.54, 4.23, 4.19, 4.09, 4.39, 4.20},
    {5.55, 5.60, 5.55, 5.61, 5.53, 5.46, 5.03, 4.80, 4.60, 4.61, 4.59, 4.92, 4.73},
    {5.56, 5.57, 5.59, 5.61, 5.54, 5.44, 5.07, 4.90, 4.82, 4.89, 4.88, 5.21, 5.04},
    {5.56, 5.54, 5.45, 5.49, 5.38, 5.16, 4.73, 4.48, 4.31, 4.38, 4.37, 4.72, 4.54},
    {5.60, 5.59, 5.40, 5.41, 5.26, 4.79, 4.23, 4.01, 3.84, 3.88, 3.88, 4.20, 4.03},
    {5.53, 5.46, 5.42, 5.40, 5.18, 4.73, 4.27, 4.05, 3.91, 3.95, 3.99, 4.34, 4.22},
    {5.53, 5.50, 5.45, 5.43, 5.30, 5.01, 4.64, 4.43, 4.26, 4.28, 4.25, 4.51, 4.38},
    {5.49, 5.48, 5.46, 5.42, 5.38, 5.03, 4.59, 4.40, 4.21, 4.20, 4.20, 4.45, 4.34},
    {5.48, 5.51, 5.46, 5.45, 5.44, 5.25, 5.04, 4.87, 4.72, 4.71, 4.69, 4.90, 4.79}};

  QDate officialParYieldDates[nDatesOfficialYields] = {
    QDate(2019, 1, 31), QDate(2019, 2, 28),  QDate(2019, 3, 31),  QDate(2019, 4, 30),
    QDate(2019, 5, 31), QDate(2019, 6, 30),  QDate(2019, 7, 31),  QDate(2019, 8, 31),
    QDate(2019, 9, 30), QDate(2019, 10, 31), QDate(2019, 11, 30), QDate(2019, 12, 31),
    QDate(2020, 1, 31), QDate(2020, 2, 29),  QDate(2020, 3, 31),  QDate(2020, 4, 30),
    QDate(2020, 5, 31), QDate(2020, 6, 30),  QDate(2020, 7, 31),  QDate(2020, 8, 31),
    QDate(2020, 9, 30), QDate(2020, 10, 31), QDate(2020, 11, 30), QDate(2020, 12, 31),
    QDate(2021, 1, 31), QDate(2021, 2, 28),  QDate(2021, 3, 31),  QDate(2021, 4, 30),
    QDate(2021, 5, 31), QDate(2021, 6, 30),  QDate(2021, 7, 31),  QDate(2021, 8, 31),
    QDate(2021, 9, 30), QDate(2021, 10, 31), QDate(2021, 11, 30), QDate(2021, 12, 31),
    QDate(2022, 1, 31), QDate(2022, 2, 28),  QDate(2022, 3, 31),  QDate(2022, 4, 30),
    QDate(2022, 5, 31), QDate(2022, 6, 30),  QDate(2022, 7, 31),  QDate(2022, 8, 31),
    QDate(2022, 9, 30), QDate(2022, 10, 31), QDate(2022, 11, 30), QDate(2022, 12, 31),
    QDate(2023, 1, 31), QDate(2023, 2, 28),  QDate(2023, 3, 31),  QDate(2023, 4, 30),
    QDate(2023, 5, 31), QDate(2023, 6, 30),  QDate(2023, 7, 31),  QDate(2023, 8, 31),
    QDate(2023, 9, 30), QDate(2023, 10, 31), QDate(2023, 11, 30), QDate(2023, 12, 31),
    QDate(2024, 1, 31), QDate(2024, 2, 29),  QDate(2024, 3, 31),  QDate(2024, 4, 30)};
  // clang-format on

  // Copy the data into the vector storing yields
  for (int d = 0; d < nDatesOfficialYields; ++d) {
    std::vector<double> dailyYields;
    for (int y = 0; y < nOfficialYields; ++y) {
      dailyYields.push_back(officialParYields[d][y]);
    }
    m_yields.push_back(dailyYields);
    m_dates.push_back(officialParYieldDates[d]);
  }

  m_columnCount = nOfficialYields;
  m_rowCount = nDatesOfficialYields * 2; // to store hidden rows of mature dates
}

YieldCurveDataModel::YieldCurveDataModel(QObject *parent)
    : QAbstractTableModel{parent} {

  loadYieldsData();

  // m_data repeats:
  // row of mature dates
  // row of corresponding par yield
  for (int i = 0; i < m_rowCount / 2; i++) {
    auto date = m_dates[i];

    // hidden dates = date + maturity
    auto maturityDatesList = new QList<qreal>(m_columnCount);
    for (int k = 0; k < m_columnCount; k++) {
      QDate maturityDate;
      QDateTime maturityDateTime;
      switch (k + 1) {
      case 1:
        maturityDate = date.addMonths(1);
        break;
      case 2:
        maturityDate = date.addMonths(2);
        break;
      case 3:
        maturityDate = date.addMonths(3);
        break;
      case 4:
        maturityDate = date.addMonths(4);
        break;
      case 5:
        maturityDate = date.addMonths(6);
        break;
      case 6:
        maturityDate = date.addYears(1);
        break;
      case 7:
        maturityDate = date.addYears(2);
        break;
      case 8:
        maturityDate = date.addYears(3);
        break;
      case 9:
        maturityDate = date.addYears(5);
        break;
      case 10:
        maturityDate = date.addYears(7);
        break;
      case 11:
        maturityDate = date.addYears(10);
        break;
      case 12:
        maturityDate = date.addYears(20);
        break;
      case 13:
        maturityDate = date.addYears(30);
        break;
      }
      maturityDateTime.setDate(maturityDate);
      maturityDatesList->replace(k, maturityDateTime.toMSecsSinceEpoch());
    }
    m_data.append(maturityDatesList);

    // yield data
    auto dataList = new QList<qreal>(m_columnCount);
    for (int k = 0; k < m_columnCount; k++) {
      dataList->replace(k, m_yields[i][k]);
    }
    m_data.append(dataList);
  }
}

int YieldCurveDataModel::rowCount(const QModelIndex &parent) const {
  Q_UNUSED(parent);
  return m_rowCount;
}

int YieldCurveDataModel::columnCount(const QModelIndex &parent) const {
  Q_UNUSED(parent);
  return m_columnCount;
}

QVariant YieldCurveDataModel::headerData(int section,
                                         Qt::Orientation orientation,
                                         int role) const {
  if (role != Qt::DisplayRole)
    return QVariant();
  if (orientation == Qt::Horizontal) {
    switch (section + 1) {
    case 1:
      return "1M";
      break;
    case 2:
      return "2M";
      break;
    case 3:
      return "3M";
      break;
    case 4:
      return "4M";
      break;
    case 5:
      return "6M";
      break;
    case 6:
      return "1Y";
      break;
    case 7:
      return "2Y";
      break;
    case 8:
      return "3Y";
      break;
    case 9:
      return "5Y";
      break;
    case 10:
      return "7Y";
      break;
    case 11:
      return "10Y";
      break;
    case 12:
      return "20Y";
      break;
    case 13:
      return "30Y";
      break;
    default:
      return "Unknown";
      break;
    }
  } else if (orientation == Qt::Vertical) {
    // vertical header
    return m_dates[section / 2].toString("yyyy-MM-dd");
  }
  return QVariant();
}

QVariant YieldCurveDataModel::data(const QModelIndex &index, int role) const {
  if ((role == Qt::DisplayRole) | (role == Qt::EditRole)) {
    return m_data[index.row()]->at(index.column());
  }
  if (role == Qt::TextAlignmentRole) {
    return int(Qt::AlignRight | Qt::AlignVCenter);
  }
  return QVariant();
}

bool YieldCurveDataModel::setData(const QModelIndex &index,
                                  const QVariant &value, int role) {
  if (index.isValid() && role == Qt::EditRole) {
    m_data[index.row()]->replace(index.column(), value.toDouble());
    emit dataChanged(index, index);
    return true;
  }
  return false;
}

Qt::ItemFlags YieldCurveDataModel::flags(const QModelIndex &index) const {
  return QAbstractItemModel::flags(index) | Qt::ItemIsEditable;
}

std::vector<double> YieldCurveDataModel::yields(const QDate &date) {
  for (int d = 0; d < m_rowCount / 2; ++d) {
    if (m_dates[d] == date) {
      return m_yields[d];
    }
  };
  // Should never be here
  const double nan = std::numeric_limits<double>::quiet_NaN();
  return std::vector<double>(m_columnCount, nan);
}
