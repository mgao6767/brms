#include "brms/treemodel.h"
#include "brms/treeitem.h"

TreeModel::TreeModel(const QStringList &headers, QObject *parent)
    : QAbstractItemModel(parent) {
  QVector<QVariant> rootData;
  foreach (const QString &header, headers)
    rootData << header;

  rootItem = new TreeItem(rootData);
  m_locale = QLocale::system();
}

TreeModel::~TreeModel() { delete rootItem; }

QVariant TreeModel::data(const QModelIndex &index, int role) const {
  if (!index.isValid())
    return QVariant();

  TreeItem *item = static_cast<TreeItem *>(index.internalPointer());

  if (role == Qt::BackgroundRole)
    if (index.column() == TreeColumn::Value |
        index.column() == TreeColumn::BackgroundColor)
      return item->data(TreeColumn::BackgroundColor);

  if (role == Qt::DisplayRole) {
    auto v = item->data(index.column());
    if (index.column() == TreeColumn::Value) {
      return m_locale.toString(v.toDouble(), 'f', 4);
    }
    return v;
  }

  return QVariant();
}

QVariant TreeModel::headerData(int section, Qt::Orientation orientation,
                               int role) const {
  if (orientation == Qt::Horizontal && role == Qt::DisplayRole)
    return rootItem->data(section);

  return QVariant();
}

QModelIndex TreeModel::index(int row, int column,
                             const QModelIndex &parent) const {
  if (!hasIndex(row, column, parent))
    return QModelIndex();

  TreeItem *parentItem;

  if (!parent.isValid())
    parentItem = rootItem;
  else
    parentItem = static_cast<TreeItem *>(parent.internalPointer());

  TreeItem *childItem = parentItem->child(row);
  if (childItem)
    return createIndex(row, column, childItem);
  else
    return QModelIndex();
}

QModelIndex TreeModel::parent(const QModelIndex &index) const {
  if (!index.isValid())
    return QModelIndex();

  TreeItem *childItem = static_cast<TreeItem *>(index.internalPointer());
  TreeItem *parentItem = childItem->parentItem();

  if (parentItem == rootItem)
    return QModelIndex();

  return createIndex(parentItem->row(), 0, parentItem);
}

int TreeModel::rowCount(const QModelIndex &parent) const {
  TreeItem *parentItem;
  if (parent.column() > 0)
    return 0;

  if (!parent.isValid())
    parentItem = rootItem;
  else
    parentItem = static_cast<TreeItem *>(parent.internalPointer());

  return parentItem->childCount();
}

int TreeModel::columnCount(const QModelIndex &parent) const {
  if (parent.isValid())
    return static_cast<TreeItem *>(parent.internalPointer())->columnCount();
  else
    return rootItem->columnCount();
}

QModelIndex TreeModel::find(int column, const QVariant &value) const {
  TreeItem *foundItem = rootItem->find(column, value);
  if (foundItem) {
    return createIndex(foundItem->row(), column, foundItem);
  } else {
    return QModelIndex();
  }
}

TreeItem *TreeModel::getItem(const QModelIndex &index) const {
  if (index.isValid()) {
    TreeItem *item = static_cast<TreeItem *>(index.internalPointer());
    if (item)
      return item;
  }
  return rootItem;
}

bool TreeModel::appendRow(const QModelIndex &parent,
                          const QVector<QVariant> &data) {
  TreeItem *parentItem;

  if (!parent.isValid())
    parentItem = rootItem;
  else
    parentItem = static_cast<TreeItem *>(parent.internalPointer());

  int newRow = parentItem->childCount();

  beginInsertRows(parent, newRow, newRow);
  TreeItem *newItem = new TreeItem(data, parentItem);
  parentItem->appendChild(newItem);
  endInsertRows();

  return true;
}

bool TreeModel::removeRow(int row, const QModelIndex &parent) {
  TreeItem *parentItem;

  if (!parent.isValid())
    parentItem = rootItem;
  else
    parentItem = static_cast<TreeItem *>(parent.internalPointer());

  if (row < 0 || row >= parentItem->childCount())
    return false;

  beginRemoveRows(parent, row, row);
  delete parentItem->child(row);
  endRemoveRows();

  return true;
}

bool TreeModel::setData(const QModelIndex &index, const QVariant &value,
                        int role) {
  if (role != Qt::EditRole && role != Qt::BackgroundRole)
    return false;

  TreeItem *item = getItem(index);
  if (item && item->setData(index.column(), value)) {
    if (index.column() == TreeColumn::BackgroundColor) {
      emit dataChanged(index.siblingAtColumn(TreeColumn::Value), index, {role});
    } else {
      emit dataChanged(index, index, {role});
    }
    return true;
  }
  return false;
}
