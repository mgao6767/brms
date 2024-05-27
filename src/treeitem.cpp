#include "brms/treeitem.h"

TreeItem::TreeItem(QVariantList data, TreeItem *parent)
    : m_itemData(std::move(data)), m_parentItem(parent) {}

void TreeItem::appendChild(std::unique_ptr<TreeItem> &&child) {
  m_childItems.push_back(std::move(child));
}

TreeItem *TreeItem::child(int row) {
  return row >= 0 && row < childCount() ? m_childItems.at(row).get() : nullptr;
}

int TreeItem::childCount() const { return int(m_childItems.size()); }

int TreeItem::columnCount() const { return int(m_itemData.count()); }

QVariant TreeItem::data(int column) const { return m_itemData.value(column); }

TreeItem *TreeItem::parentItem() { return m_parentItem; }

int TreeItem::row() const {
  if (m_parentItem == nullptr)
    return 0;
  const auto it = std::find_if(
      m_parentItem->m_childItems.cbegin(), m_parentItem->m_childItems.cend(),
      [this](const std::unique_ptr<TreeItem> &treeItem) {
        return treeItem.get() == this;
      });

  if (it != m_parentItem->m_childItems.cend())
    return std::distance(m_parentItem->m_childItems.cbegin(), it);
  Q_ASSERT(false); // should not happen
  return -1;
}
