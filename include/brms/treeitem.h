#ifndef TREEITEM_H
#define TREEITEM_H

#include <QList>
#include <QVariant>

class TreeItem {
public:
  explicit TreeItem(QVariantList data, TreeItem *parentItem = nullptr);

  void appendChild(std::unique_ptr<TreeItem> &&child);
  void removeChildren();

  TreeItem *child(int row);
  int childCount() const;
  int columnCount() const;
  QVariant data(int column) const;
  int row() const;
  TreeItem *parentItem();
  bool setData(int column, const QVariant &value);

private:
  std::vector<std::unique_ptr<TreeItem>> m_childItems;
  QVariantList m_itemData;
  TreeItem *m_parentItem;
};

#endif // TREEITEM_H
