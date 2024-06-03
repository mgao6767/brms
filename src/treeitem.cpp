#include "brms/treeitem.h"

TreeItem::TreeItem(const QVector<QVariant> &data, TreeItem *parent)
    : m_parentItem(parent) {
    m_itemData = QVector<QVariant>(TreeColumn::TREECOLUMN_SIZE, QVariant());
    for (int i = 0; i < data.size(); ++i)
        m_itemData[i] = data[i];
    m_itemData[TreeColumn::BackgroundColor] = QColor(Qt::transparent);
}

TreeItem::~TreeItem() { qDeleteAll(m_childItems); }

void TreeItem::appendChild(TreeItem *child) { m_childItems.append(child); }

TreeItem *TreeItem::child(int row) { return m_childItems.value(row); }

int TreeItem::childCount() const { return m_childItems.count(); }

int TreeItem::columnCount() const { return m_itemData.count(); }

QVariant TreeItem::data(int column) const { return m_itemData.value(column); }

bool TreeItem::setData(int column, const QVariant &value) {
  if (column < 0 || column >= m_itemData.size())
    return false;

  m_itemData[column] = value;
  return true;
}

int TreeItem::row() const {
  if (m_parentItem)
    return m_parentItem->m_childItems.indexOf(const_cast<TreeItem *>(this));
  return 0;
}

TreeItem *TreeItem::parentItem() { return m_parentItem; }

TreeItem *TreeItem::find(int column, const QVariant &value) {
  // Check if the current item matches the search criteria
  if (data(column) == value)
    return this;

  // Recursively search through the children
  for (TreeItem *child : std::as_const(m_childItems)) {
    TreeItem *result = child->find(column, value);
    if (result)
      return result;
  }

  // Return nullptr if no match is found
  return nullptr;
}
