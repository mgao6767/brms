#ifndef TREEMODEL_H
#define TREEMODEL_H

#include "brms/treeitem.h"
#include <QAbstractItemModel>

/**
 * @brief The TreeModel class represents the model for a tree structure.
 */
class TreeModel : public QAbstractItemModel {
  Q_OBJECT

public:
  /**
   * @brief Constructs a TreeModel with the given headers and parent.
   * @param headers The headers for the columns.
   * @param parent The parent object.
   */
  explicit TreeModel(const QStringList &headers, QObject *parent = nullptr);

  /**
   * @brief Destructor.
   */
  ~TreeModel();

  /**
   * @brief Returns the data stored under the given role for the item referred
   * to by the index.
   * @param index The index of the item.
   * @param role The role of the data.
   * @return The data.
   */
  QVariant data(const QModelIndex &index, int role) const override;

  /**
   * @brief Returns the header data for the given section, orientation and role.
   * @param section The section of the header.
   * @param orientation The orientation of the header.
   * @param role The role of the data.
   * @return The header data.
   */
  QVariant headerData(int section, Qt::Orientation orientation,
                      int role) const override;

  /**
   * @brief Returns the index of the item in the model specified by the given
   * row, column, and parent index.
   * @param row The row of the item.
   * @param column The column of the item.
   * @param parent The parent index.
   * @return The index of the item.
   */
  QModelIndex index(int row, int column,
                    const QModelIndex &parent = QModelIndex()) const override;

  /**
   * @brief Returns the parent of the model item with the given index.
   * @param index The index of the item.
   * @return The parent index.
   */
  QModelIndex parent(const QModelIndex &index) const override;

  /**
   * @brief Returns the number of rows under the given parent.
   * @param parent The parent index.
   * @return The number of rows.
   */
  int rowCount(const QModelIndex &parent = QModelIndex()) const override;

  /**
   * @brief Returns the number of columns for the children of the given parent.
   * @param parent The parent index.
   * @return The number of columns.
   */
  int columnCount(const QModelIndex &parent = QModelIndex()) const override;

  /**
   * @brief Searches for an item with the specified data in the given column.
   * @param column The column to search in.
   * @param value The value to search for.
   * @return The index of the found item, or an invalid QModelIndex if not
   * found.
   */
  QModelIndex find(int column, const QVariant &value) const;

  /**
   * @brief Returns the TreeItem for the given QModelIndex.
   * @param index The index to find the item for.
   * @return The TreeItem corresponding to the index, or nullptr if the index is
   * invalid.
   */
  TreeItem *getItem(const QModelIndex &index) const;

  /**
   * @brief Appends a row to the given parent index.
   * @param parent The parent index.
   * @param data The data for the new row.
   * @return True if the row was appended successfully, false otherwise.
   */
  bool appendRow(const QModelIndex &parent, const QVector<QVariant> &data);

  /**
   * @brief Removes a row from the given parent index.
   * @param row The row to be removed.
   * @param parent The parent index.
   * @return True if the row was removed successfully, false otherwise.
   */
  bool removeRow(int row, const QModelIndex &parent = QModelIndex());

  /**
   * @brief Sets the data for the item at the given index.
   * @param index The index of the item.
   * @param value The value to set.
   * @param role The role of the data.
   * @return True if the data was set successfully, false otherwise.
   */
  bool setData(const QModelIndex &index, const QVariant &value,
               int role = Qt::EditRole) override;

private:
  TreeItem *rootItem; ///< Root item of the tree
};

#endif // TREEMODEL_H
