#ifndef UTILS_H
#define UTILS_H

#include <QDate>
#include <ql/time/date.hpp>

const QuantLib::Month monthMap_[] = {
    QuantLib::Jan, QuantLib::Feb, QuantLib::Mar, QuantLib::Apr,
    QuantLib::May, QuantLib::Jun, QuantLib::Jul, QuantLib::Aug,
    QuantLib::Sep, QuantLib::Oct, QuantLib::Nov, QuantLib::Dec,
};

inline QDate qlDateToQDate(QuantLib::Date date) {
  return QDate(date.year(), date.month(), date.dayOfMonth());
}

inline QuantLib::Date qDateToQLDate(QDate date) {
  // QuantLib at work
  QuantLib::Date qlDate(date.day(), monthMap_[date.month() - 1], date.year());
  return qlDate;
}

#endif // UTILS_H
