#include "brms/treemodel.h"
#include "brms/treeitem.h"

#include <QDebug>
#include <QStringList>

using namespace Qt::StringLiterals;

TreeModel::TreeModel(QObject *parent)
    : QAbstractItemModel(parent),
      rootItem(std::make_unique<TreeItem>(
          QVariantList{tr("Assets"), tr("Amount")})) {
  setupModelData(rootItem.get());
}

TreeModel::~TreeModel() = default;

int TreeModel::columnCount(const QModelIndex &parent) const {
  if (parent.isValid())
    return static_cast<TreeItem *>(parent.internalPointer())->columnCount();
  return rootItem->columnCount();
}

QVariant TreeModel::data(const QModelIndex &index, int role) const {
  if (!index.isValid() || role != Qt::DisplayRole)
    return {};

  const auto *item = static_cast<const TreeItem *>(index.internalPointer());
  return item->data(index.column());
}

Qt::ItemFlags TreeModel::flags(const QModelIndex &index) const {
  return index.isValid() ? QAbstractItemModel::flags(index)
                         : Qt::ItemFlags(Qt::NoItemFlags);
}

QVariant TreeModel::headerData(int section, Qt::Orientation orientation,
                               int role) const {
  return orientation == Qt::Horizontal && role == Qt::DisplayRole
             ? rootItem->data(section)
             : QVariant{};
}

QModelIndex TreeModel::index(int row, int column,
                             const QModelIndex &parent) const {
  if (!hasIndex(row, column, parent))
    return {};

  TreeItem *parentItem = parent.isValid()
                             ? static_cast<TreeItem *>(parent.internalPointer())
                             : rootItem.get();

  if (auto *childItem = parentItem->child(row))
    return createIndex(row, column, childItem);
  return {};
}

QModelIndex TreeModel::parent(const QModelIndex &index) const {
  if (!index.isValid())
    return {};

  auto *childItem = static_cast<TreeItem *>(index.internalPointer());
  TreeItem *parentItem = childItem->parentItem();

  return parentItem != rootItem.get()
             ? createIndex(parentItem->row(), 0, parentItem)
             : QModelIndex{};
}

int TreeModel::rowCount(const QModelIndex &parent) const {
  if (parent.column() > 0)
    return 0;

  const TreeItem *parentItem =
      parent.isValid() ? static_cast<const TreeItem *>(parent.internalPointer())
                       : rootItem.get();

  return parentItem->childCount();
}

void TreeModel::setupModelData(TreeItem *parent) {
  // placeholder
  QVariantList columnData;
  columnData.reserve(2);
  columnData << "Cash" << 10000;
  parent->appendChild(std::make_unique<TreeItem>(columnData, parent));

  columnData.clear();
  columnData.reserve(2);
  columnData << "Reserves" << 1000;
  parent->appendChild(std::make_unique<TreeItem>(columnData, parent));

  columnData.clear();
  columnData.reserve(2);
  columnData << "Treasury Securities" << 3000;
  auto treasuries = std::make_unique<TreeItem>(columnData, parent);

  columnData.clear();
  columnData.reserve(2);
  columnData << "3.75% Treasury Bill 04/05/2022" << 1000;
  treasuries->appendChild(
      std::make_unique<TreeItem>(columnData, treasuries.get()));

  columnData.clear();
  columnData.reserve(2);
  columnData << "4.75% Treasury Note 04/05/2025" << 1000;
  treasuries->appendChild(
      std::make_unique<TreeItem>(columnData, treasuries.get()));

  columnData.clear();
  columnData.reserve(2);
  columnData << "5.135% Treasury Bill 04/05/2026" << 1000;
  treasuries->appendChild(
      std::make_unique<TreeItem>(columnData, treasuries.get()));

  parent->appendChild(std::move(treasuries));
}
