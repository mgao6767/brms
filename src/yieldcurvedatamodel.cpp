#include "brms/yieldcurvedatamodel.h"
#include <QColor>
#include <QFile>
#include <QList>
#include <QRandomGenerator>
#include <QRect>
#include <QStringList>
#include <QTextStream>
#include <limits>

bool readCSVRow(QTextStream &in, QStringList *row);

void YieldCurveDataModel::loadYieldsData(QString filePath) {

  QFile csv(filePath);
  csv.open(QFile::ReadOnly | QFile::Text);

  QTextStream in(&csv);
  QStringList row;

  beginResetModel();

  m_rowCount = 0;
  m_columnCount = 13;
  m_dates.clear();
  m_yields.clear();
  m_data.clear();

  while (readCSVRow(in, &row)) {
    // skip header row
    if (m_rowCount == 0) {
      m_rowCount++;
      continue;
    }

    QDate date = QDate::fromString(row[0], "yyyy-MM-dd");
    m_dates.push_back(date);
    row.pop_front();
    std::vector<double> dailyYields;
    dailyYields.reserve(m_columnCount);
    for (auto &r : row) {
      auto rate = r.toDouble();
      dailyYields.push_back(rate);
    }
    m_yields.push_back(dailyYields);
    m_rowCount++;
  }

  m_rowCount = (m_rowCount - 1) * 2; // to store hidden rows of mature dates

  // m_data repeats:
  // row of mature dates
  // row of corresponding par yield
  for (int i = 0; i < m_rowCount / 2; i++) {
    auto date = m_dates[i];

    // hidden dates = date + maturity
    // auto maturityDatesList = QList<qreal>(m_columnCount);
    auto maturityDatesList = std::vector<qreal>(13, 0.0);
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
      maturityDatesList[k] =maturityDateTime.toMSecsSinceEpoch();
    }
    m_data.push_back(maturityDatesList);

    // yield data
    // auto dataList = QList<qreal>(m_columnCount);
    auto dataList = std::vector<qreal>(13, 0.0);
    for (int k = 0; k < m_columnCount; k++) {
      // dataList.replace(k, m_yields[i][k]);
        dataList[k]=m_yields[i][k];
    }

    m_data.push_back(dataList);
  }

  endResetModel();
  // beginInsertRows(QModelIndex(), 0, m_rowCount-1);
  // endInsertRows();
  // beginInsertColumns(QModelIndex(), 0, m_columnCount-1);
  // endInsertColumns();
}

YieldCurveDataModel::YieldCurveDataModel(QObject *parent)
    : QAbstractTableModel{parent} {

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
        auto rate = m_data[index.row()].at(index.column());
    return QString::number(rate, 'f', 2);
  }
  if (role == Qt::TextAlignmentRole) {
    return int(Qt::AlignRight | Qt::AlignVCenter);
  }
  return QVariant();
}

bool YieldCurveDataModel::setData(const QModelIndex &index,
                                  const QVariant &value, int role) {
  if (index.isValid() && role == Qt::EditRole) {
    // m_data[index.row()].replace(index.column(), value.toDouble());
      m_data[index.row()].at(index.column()) = value.toDouble();

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

bool readCSVRow(QTextStream &in, QStringList *row) {
  // https://gist.github.com/JC3/4ec7f6f2883aec7087bff342494bd791
  static const int delta[][5] = {
      //  ,    "   \n    ?  eof
      {1, 2, -1, 0, -1}, // 0: parsing (store char)
      {1, 2, -1, 0, -1}, // 1: parsing (store column)
      {3, 4, 3, 3, -2},  // 2: quote entered (no-op)
      {3, 4, 3, 3, -2},  // 3: parsing inside quotes (store char)
      {1, 3, -1, 0, -1}, // 4: quote exited (no-op)
                         // -1: end of row, store column, success
                         // -2: eof inside quotes
  };

  row->clear();

  if (in.atEnd())
    return false;

  int state = 0, t;
  char ch;
  QString cell;

  while (state >= 0) {

    if (in.atEnd())
      t = 4;
    else {
      in >> ch;
      if (ch == ',')
        t = 0;
      else if (ch == '\"')
        t = 1;
      else if (ch == '\n')
        t = 2;
      else
        t = 3;
    }

    state = delta[state][t];

    if (state == 0 || state == 3) {
      cell += ch;
    } else if (state == -1 || state == 1) {
      row->append(cell);
      cell = "";
    }
  }

  if (state == -2)
    throw std::runtime_error("End-of-file found while inside quotes.");

  return true;
}
