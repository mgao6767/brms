#include "brms/bankassets.h"
#include "brms/utils.h"

BankAssets::BankAssets(QStringList header) {
  m_model = new TreeModel(header);
  m_model->appendRow(QModelIndex(), {CASH, 1000000.0});
  m_model->appendRow(QModelIndex(), {TREASURY_SECURITIES, 0.0});
  m_model->appendRow(QModelIndex(), {LOANS, 0.0});
}

BankAssets::~BankAssets() { delete m_model; }

TreeModel *BankAssets::model() { return m_model; }

double BankAssets::getCash() const {
  QModelIndex index = m_model->find(TreeColumn::Name, CASH);
  TreeItem *cashItem = m_model->getItem(index);
  return cashItem->data(TreeColumn::Value).toDouble();
}

bool BankAssets::setCash(double amount) {
  QModelIndex index = m_model->find(TreeColumn::Name, CASH);
  TreeItem *cashItem = m_model->getItem(index);
  return cashItem->setData(TreeColumn::Value, amount);
}

bool BankAssets::addTreasuryBill(QuantLib::ZeroCouponBond &bill) {
  QString name = QString("%1% Treasury Bill %2");
  QDate maturityDate = qlDateToQDate(bill.maturityDate());
  name = name.arg(bill.nextCouponRate() * 100);
  name = name.arg(maturityDate.toString("dd/MM/yyyy"));
  return addTreasurySecurity(bill, name);
}

bool BankAssets::addTreasuryNote(QuantLib::FixedRateBond &note) {
  QString name = QString("%1% Treasury Note %2");
  QDate maturityDate = qlDateToQDate(note.maturityDate());
  name = name.arg(note.nextCouponRate() * 100);
  name = name.arg(maturityDate.toString("dd/MM/yyyy"));
  return addTreasurySecurity(note, name);
}

bool BankAssets::addTreasuryBond(QuantLib::FixedRateBond &bond) {
  QString name = QString("%1% Treasury Bond %2");
  QDate maturityDate = qlDateToQDate(bond.maturityDate());
  name = name.arg(bond.nextCouponRate() * 100);
  name = name.arg(maturityDate.toString("dd/MM/yyyy"));
  return addTreasurySecurity(bond, name);
}

bool BankAssets::addTreasurySecurity(QuantLib::Bond &bond, QString name) {
  // must first have a pricing engine to get NPV
  bond.setPricingEngine(m_treasuryPricingEngine);
  // must have enough cash
  double cash = getCash();
  if (cash < bond.NPV())
    return false;
  m_treasurySecurities.push_back(bond);
  // ref is the index of the bond in the vector
  QVariant ref =
      QVariant::fromValue<unsigned long>(m_treasurySecurities.size() - 1);
  // add to tree model
  QModelIndex index = m_model->find(TreeColumn::Name, TREASURY_SECURITIES);
  TreeItem *treasuryItem = m_model->getItem(index);
  TreeItem *item = new TreeItem({name, bond.NPV(), ref}, treasuryItem);
  treasuryItem->appendChild(item);
  // update total value of Treasury securities
  updateTotalValue();
  return setCash(cash - bond.NPV());
}

void BankAssets::setTreasuryPricingEngine(
    const QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine> &engine) {
  m_treasuryPricingEngine = engine;
}

void BankAssets::reprice() {
  QModelIndex index = m_model->find(TreeColumn::Name, TREASURY_SECURITIES);
  TreeItem *treasuryItem = m_model->getItem(index);
  for (size_t i = 0; i < treasuryItem->childCount(); i++) {
    auto bond = treasuryItem->child(i);
    // get the pointer to the original bond object
    auto j = bond->data(TreeColumn::Ref).toInt();
    auto npv = m_treasurySecurities[j].NPV();
    auto valueIdx = m_model->index(i, TreeColumn::Value, index);
    m_model->setData(valueIdx, npv);
  }
  updateTotalValue();
}

void BankAssets::updateTotalValue() {
  QModelIndex index = m_model->find(TreeColumn::Name, TREASURY_SECURITIES);
  TreeItem *treasuryItem = m_model->getItem(index);
  double totalValue = 0.0;
  for (size_t i = 0; i < treasuryItem->childCount(); i++) {
    auto bond = treasuryItem->child(i);
    totalValue += bond->data(TreeColumn::Value).toDouble();
  }
  m_model->setData(index.siblingAtColumn(TreeColumn::Value), totalValue);
}
