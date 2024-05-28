#include "brms/treemodel.h"
#include "brms/treeitem.h"
#include "brms/utils.h"
#include <QDebug>
#include <QStringList>

using namespace Qt::StringLiterals;

TreeModel::TreeModel(const std::vector<QuantLib::FixedRateBond> &bonds,
                     QObject *parent)
    : QAbstractItemModel(parent),
      rootItem(
          std::make_unique<TreeItem>(QVariantList{tr("Assets"), tr("Amount")})),
      m_bonds(&bonds) {}

TreeModel::~TreeModel() = default;

int TreeModel::columnCount(const QModelIndex &parent) const {
  if (parent.isValid())
    return static_cast<TreeItem *>(parent.internalPointer())->columnCount();
  return rootItem->columnCount();
}

QVariant TreeModel::data(const QModelIndex &index, int role) const {

  if (index.column() == 1 && role == Qt::TextAlignmentRole)
    return int(Qt::AlignRight | Qt::AlignVCenter);
  if (!index.isValid() || role != Qt::DisplayRole)
    return {};
  const auto *item = static_cast<const TreeItem *>(index.internalPointer());
  auto data = item->data(index.column());
  if (index.column() == 1) {
    return QString::number(data.toDouble(), 'f', 4);
  }
  return data;
}

Qt::ItemFlags TreeModel::flags(const QModelIndex &index) const {
  return index.isValid() ? QAbstractItemModel::flags(index)
                         : Qt::ItemFlags(Qt::NoItemFlags);
}

QVariant TreeModel::headerData(int section, Qt::Orientation orientation,
                               int role) const {
  // if (section == 1 && role == Qt::TextAlignmentRole &&
  // orientation==Qt::Horizontal)
  //     return int(Qt::AlignRight | Qt::AlignVCenter);
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

void TreeModel::update() {

  auto parent = rootItem.get();

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
  columnData << "Treasury Securities" << 0.0;
  auto treasuries = std::make_unique<TreeItem>(columnData, parent);
  double totalAmount = 0.0;
  auto date = QuantLib::Settings::instance().evaluationDate();
  for (auto &b : *m_bonds) {
    columnData.clear();
    columnData.reserve(2);
    auto rate = b.nextCouponRate(date);
    QDate matureDate = qlDateToQDate(b.maturityDate());
    QString name(QString("%1% Treasury Security %2")
                     .arg(QString::number(rate * 100, 'f', 2),
                          matureDate.toString("dd/MM/yyyy")));
    columnData << name << b.NPV();
    treasuries->appendChild(
        std::make_unique<TreeItem>(columnData, treasuries.get()));
    totalAmount += b.NPV();
  }
  treasuries->setData(1, totalAmount);

  parent->appendChild(std::move(treasuries));
}

void TreeModel::reprice() {
  beginResetModel();
  auto date = QuantLib::Settings::instance().evaluationDate();
  auto p = rootItem.get();
  for (int row = 0; row < p->childCount(); ++row) {
    auto child = p->child(row);
    // qDebug() << child->data(0);
    if (child->data(0) == QString("Treasury Securities")) {
      auto treasuries = child;
      double totalAmount = 0.0;
      treasuries->removeChildren();
      QVariantList columnData;
      for (auto &b : *m_bonds) {
        columnData.clear();
        columnData.reserve(2);
        auto rate = b.nextCouponRate(date);
        QDate matureDate = qlDateToQDate(b.maturityDate());
        QString name(QString("%1% Treasury Security %2")
                         .arg(QString::number(rate * 100, 'f', 2),
                              matureDate.toString("dd/MM/yyyy")));
        columnData << name << b.NPV();
        treasuries->appendChild(
            std::make_unique<TreeItem>(columnData, treasuries));
        totalAmount += b.NPV();
      }
      treasuries->setData(1, totalAmount);
    }
  }
  endResetModel();
}

TreeItem *TreeModel::getItem(const QModelIndex &index) const {
  if (index.isValid()) {
    if (auto *item = static_cast<TreeItem *>(index.internalPointer()))
      return item;
  }
  return rootItem.get();
}

bool TreeModel::setData(const QModelIndex &index, const QVariant &value,
                        int role) {
  if (role != Qt::EditRole)
    return false;

  TreeItem *item = getItem(index);
  bool result = item->setData(index.column(), value);

  if (result)
    emit dataChanged(index, index, {Qt::DisplayRole, Qt::EditRole});

  return result;
}
