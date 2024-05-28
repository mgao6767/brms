#ifndef TREEMODEL_H
#define TREEMODEL_H

#include <QAbstractItemModel>
#include <QModelIndex>
#include <QVariant>
#include <ql/instruments/bonds/all.hpp>

class TreeItem;

class TreeModel : public QAbstractItemModel {
  Q_OBJECT

public:
  Q_DISABLE_COPY_MOVE(TreeModel)

  explicit TreeModel(const std::vector<QuantLib::FixedRateBond> &bonds,
                     QObject *parent = nullptr);
  ~TreeModel() override;

  QVariant data(const QModelIndex &index, int role) const override;
  Qt::ItemFlags flags(const QModelIndex &index) const override;
  QVariant headerData(int section, Qt::Orientation orientation,
                      int role = Qt::DisplayRole) const override;
  QModelIndex index(int row, int column,
                    const QModelIndex &parent = {}) const override;
  QModelIndex parent(const QModelIndex &index) const override;
  int rowCount(const QModelIndex &parent = {}) const override;
  int columnCount(const QModelIndex &parent = {}) const override;
  bool setData(const QModelIndex &index, const QVariant &value,
               int role = Qt::EditRole) override;
  TreeItem *getItem(const QModelIndex &index) const;

  void update();

public slots:
  void reprice();

private:
  std::unique_ptr<TreeItem> rootItem;
  const std::vector<QuantLib::FixedRateBond> *m_bonds;
};

#endif // TREEMODEL_H
