#ifndef TREEITEM_H
#define TREEITEM_H

#include <QVariant>
#include <QVector>

enum TreeColumn {
  Name,
  Value,
  Ref
};

/**
 * @brief The TreeItem class represents a single item in a tree model.
 */
class TreeItem {
public:
  /**
   * @brief Constructs a TreeItem with the given data and optional parent.
   * @param data The data to be stored in the item.
   * @param parent The parent item.
   */
  explicit TreeItem(const QVector<QVariant> &data, TreeItem *parent = nullptr);

  /**
   * @brief Destructor.
   */
  ~TreeItem();

  /**
   * @brief Adds a child item to this item.
   * @param child The child item to be added.
   */
  void appendChild(TreeItem *child);

  /**
   * @brief Returns the child item at the given row.
   * @param row The row of the child item.
   * @return The child item.
   */
  TreeItem *child(int row);

  /**
   * @brief Returns the number of child items.
   * @return The number of child items.
   */
  int childCount() const;

  /**
   * @brief Returns the number of columns in the item.
   * @return The number of columns.
   */
  int columnCount() const;

  /**
   * @brief Returns the data stored in the item for the given column.
   * @param column The column of the data.
   * @return The data.
   */
  QVariant data(int column) const;

  /**
   * @brief Sets the data for the given column.
   * @param column The column to set the data for.
   * @param value The data value to set.
   * @return True if the data was set successfully, false otherwise.
   */
  bool setData(int column, const QVariant &value);

  /**
   * @brief Returns the row number of this item in its parent.
   * @return The row number.
   */
  int row() const;

  /**
   * @brief Returns the parent item.
   * @return The parent item.
   */
  TreeItem *parentItem();

  /**
   * @brief Searches for a child item with the specified data.
   * @param column The column to search in.
   * @param value The value to search for.
   * @return The pointer to the found item, or nullptr if not found.
   */
  TreeItem *find(int column, const QVariant &value);

private:
  QVector<TreeItem *> m_childItems; ///< List of child items
  QVector<QVariant> m_itemData;     ///< Data stored in the item
  TreeItem *m_parentItem;           ///< Parent item
};

#endif // TREEITEM_H
