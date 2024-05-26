#ifndef YIELDCURVEDATAMODEL_H
#define YIELDCURVEDATAMODEL_H

#include <QAbstractTableModel>
#include <QDate>
#include <QMultiHash>
#include <QRect>

class YieldCurveDataModel : public QAbstractTableModel {
public:
  explicit YieldCurveDataModel(QObject *parent = nullptr);

  int rowCount(const QModelIndex &parent = QModelIndex()) const;
  int columnCount(const QModelIndex &parent = QModelIndex()) const;
  QVariant headerData(int section, Qt::Orientation orientation,
                      int role = Qt::DisplayRole) const;
  QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const;
  bool setData(const QModelIndex &index, const QVariant &value,
               int role = Qt::EditRole);
  Qt::ItemFlags flags(const QModelIndex &index) const;

  std::vector<double> yields(const QDate &date);

private:
  QList<QList<qreal> *> m_data;
  QMultiHash<QString, QRect> m_mapping;
  int m_columnCount;
  int m_rowCount;
  void loadYieldsData();
  // to store yields date and data
  std::vector<QDate> m_dates;
  std::vector<std::vector<double>> m_yields;
};

#endif // YIELDCURVEDATAMODEL_H
