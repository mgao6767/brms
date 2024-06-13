#ifndef TREASURYFUTURES_H
#define TREASURYFUTURES_H

#include "instruments.h"
#include <QAbstractTableModel>
#include <QLocale>

class TreasuryFuturesModel : public QAbstractTableModel {
public:
  explicit TreasuryFuturesModel(QObject *parent = nullptr);

  int rowCount(const QModelIndex &parent = QModelIndex()) const;
  int columnCount(const QModelIndex &parent = QModelIndex()) const;
  QVariant headerData(int section, Qt::Orientation orientation,
                      int role = Qt::DisplayRole) const;
  QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const;

private:
  std::vector<QuantLib::BondForward> m_treasuryFutures;
  QLocale m_locale;
};

class TreasuryFutures : public QObject {
  Q_OBJECT
public:
  TreasuryFutures();
  ~TreasuryFutures();

  TreasuryFuturesModel *model();

  // void addTreasuryFutures(QuantLib::FixedRateBondForward &f);
  //
private:
  TreasuryFuturesModel *m_model;
  QuantLib::Date m_lastRepricingDate;

public slots:
  void reprice();
};

#endif // TREASURYFUTURES_H
