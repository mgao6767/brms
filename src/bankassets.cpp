#include "brms/bankassets.h"
#include "brms/utils.h"

BankAssets::BankAssets(QStringList header) {
  m_model = new TreeModel(header);
  m_model->appendRow(QModelIndex(),
                     {CASH, 100000.0}); // This is the initial common equity
  m_model->appendRow(QModelIndex(), {TREASURY_SECURITIES, 0.0});
  m_model->appendRow(QModelIndex(), {LOANS, 0.0});
  m_lastRepricingDate = QuantLib::Settings::instance().evaluationDate();
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
  QModelIndex cashAmountIdx = m_model->index(index.row(), TreeColumn::Value);
  return m_model->setData(cashAmountIdx, amount);
}

void BankAssets::addCash(double amount) { setCash(getCash() + amount); }

void BankAssets::deductCash(double amount) { addCash(-amount); }

bool BankAssets::addTreasuryBill(QuantLib::ZeroCouponBond &bill) {
  QString name = QString("%1% Treasury Bill %2");
  QDate maturityDate = qlDateToQDate(bill.maturityDate());
  name = name.arg(QString::number(bill.nextCouponRate() * 100, 'f', 3));
  name = name.arg(maturityDate.toString("dd/MM/yyyy"));
  return addTreasurySecurity(bill, name);
}

bool BankAssets::addTreasuryNote(QuantLib::FixedRateBond &note) {
  QString name = QString("%1% Treasury Note %2");
  QDate maturityDate = qlDateToQDate(note.maturityDate());
  name = name.arg(QString::number(note.nextCouponRate() * 100, 'f', 3));
  name = name.arg(maturityDate.toString("dd/MM/yyyy"));
  return addTreasurySecurity(note, name);
}

bool BankAssets::addTreasuryBond(QuantLib::FixedRateBond &bond) {
  QString name = QString("%1% Treasury Bond %2");
  QDate maturityDate = qlDateToQDate(bond.maturityDate());
  name = name.arg(QString::number(bond.nextCouponRate() * 100, 'f', 3));
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
  updateTotalValue();
  return setCash(cash - bond.NPV());
}

void BankAssets::setTreasuryPricingEngine(
    const QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine> &engine) {
  m_treasuryPricingEngine = engine;
}

bool BankAssets::addAmortizingFixedRateLoan(
    QuantLib::AmortizingFixedRateBond &loan) {
  QString name = QString("%1% %2-year mortgage %3");
  QDate maturityDate = qlDateToQDate(loan.maturityDate());
  int mat = (loan.maturityDate() - loan.issueDate()) / 365;
  name = name.arg(QString::number(loan.nextCouponRate() * 100, 'f', 3));
  name = name.arg(mat);
  name = name.arg(maturityDate.toString("dd/MM/yyyy"));

  double cash = getCash();
  if (cash < loan.notional())
    return false;
  m_loans.push_back(loan);
  // ref is the index of the bond in the vector
  QVariant ref = QVariant::fromValue<unsigned long>(m_loans.size() - 1);
  // add to tree model
  QModelIndex index = m_model->find(TreeColumn::Name, LOANS);
  TreeItem *loanItem = m_model->getItem(index);
  TreeItem *item = new TreeItem({name, loan.notional(), ref}, loanItem);
  loanItem->appendChild(item);
  updateTotalValue();
  return setCash(cash - loan.notional());
}

void BankAssets::reprice() {
  double startingCash = getCash();
  repriceTreasurySecurities();
  repriceLoans();
  double endingCash = getCash();

  updateTotalValue();
  setCash(endingCash);
  updateCashColor(startingCash, endingCash);

  emit totalAssetsChanged(totalAssets());
  m_lastRepricingDate = QuantLib::Settings::instance().evaluationDate();
}

void BankAssets::updateCashColor(double startingCash, double endingCash) {
  QModelIndex index = m_model->find(TreeColumn::Name, CASH);
  if (endingCash > startingCash) {
    m_model->setData(index.siblingAtColumn(TreeColumn::BackgroundColor),
                     BRMS::GREEN);
  } else if (endingCash < startingCash) {
    m_model->setData(index.siblingAtColumn(TreeColumn::BackgroundColor),
                     BRMS::RED);
  } else {
    m_model->setData(index.siblingAtColumn(TreeColumn::BackgroundColor),
                     BRMS::TRANSPARENT);
  }
}

void BankAssets::repriceTreasurySecurities() {
  QModelIndex index = m_model->find(TreeColumn::Name, TREASURY_SECURITIES);
  TreeItem *treasuryItem = m_model->getItem(index);
  for (size_t i = 0; i < treasuryItem->childCount(); i++) {
    auto bond = treasuryItem->child(i);
    // j is the location of the bond in the vector
    auto j = bond->data(TreeColumn::Ref).toInt();
    QuantLib::Bond &instrument = m_treasurySecurities[j];
    if (instrument.isExpired()) {
      continue;
    }
    // if today is maturity date
    auto colorIdx = m_model->index(i, TreeColumn::BackgroundColor, index);
    auto valueIdx = m_model->index(i, TreeColumn::Value, index);
    if (instrument.valuationDate() == instrument.maturityDate()) {
      double totalPaymentAtMaturity = 0.0;
      for (auto &c : instrument.cashflows()) {
        totalPaymentAtMaturity +=
            c->date() == instrument.maturityDate() ? c->amount() : 0.0;
      }
      // update cash
      setCash(getCash() + totalPaymentAtMaturity);
      // set the instrument to "matured"
      m_model->setData(valueIdx, "Matured");
      m_model->setData(colorIdx, BRMS::TRANSPARENT);
      QString name = m_model
                         ->data(valueIdx.siblingAtColumn(TreeColumn::Name),
                                Qt::DisplayRole)
                         .toString();
      emit treasurySecurityMatured(name, totalPaymentAtMaturity);
    } else {
      // not yet matured
      auto npv = instrument.NPV();
      m_model->setData(valueIdx, npv);
    }
  }
}

void BankAssets::repriceLoans() {
  QModelIndex index = m_model->find(TreeColumn::Name, LOANS);
  TreeItem *item = m_model->getItem(index);
  QuantLib::Date today = QuantLib::Settings::instance().evaluationDate();
  double totalPayment = 0.0;
  for (size_t i = 0; i < item->childCount(); i++) {
    auto bond = item->child(i);
    // j is the location of the bond in the vector
    auto j = bond->data(TreeColumn::Ref).toInt();
    QuantLib::Bond &instrument = m_loans[j];
    if (instrument.isExpired()) {
      continue;
    }
    double singleLoanPayment = 0.0;
    for (auto &c : instrument.cashflows()) {
      // today in the simulation may not coincide with the cash flow day
      if (m_lastRepricingDate < c->date() && c->date() <= today)
        singleLoanPayment += c->amount();
    }
    auto valueIdx = m_model->index(i, TreeColumn::Value, index);
    m_model->setData(valueIdx, instrument.notional());
    totalPayment += singleLoanPayment;
    if (singleLoanPayment > 0) {
      QString name = m_model
                         ->data(valueIdx.siblingAtColumn(TreeColumn::Name),
                                Qt::DisplayRole)
                         .toString();
      emit loanAmortizingPaymentReceived(name, singleLoanPayment);
    }
  }
  if (totalPayment > 0) {
    setCash(getCash() + totalPayment);
  }
}

void BankAssets::updateTotalValue() {
  // Treasuries
  QModelIndex indexTreasury =
      m_model->find(TreeColumn::Name, TREASURY_SECURITIES);
  double totalValue = getTotalValueOfTreasurySecurities();
  m_model->setData(indexTreasury.siblingAtColumn(TreeColumn::Value),
                   totalValue);

  // loans
  QModelIndex indexLoans = m_model->find(TreeColumn::Name, LOANS);
  double loanValue = getTotalValueOfLoans();
  m_model->setData(indexLoans.siblingAtColumn(TreeColumn::Value), loanValue);
}

double BankAssets::totalAssets() const {
  double cash = getCash();
  double treasuries = getTotalValueOfTreasurySecurities();
  double loans = getTotalValueOfLoans();

  return cash + treasuries + loans;
}

double BankAssets::getTotalValueOfTreasurySecurities() const {
  QModelIndex index = m_model->find(TreeColumn::Name, TREASURY_SECURITIES);
  TreeItem *treasuryItem = m_model->getItem(index);
  double totalValue = 0.0;
  for (size_t i = 0; i < treasuryItem->childCount(); i++) {
    auto bond = treasuryItem->child(i);
    totalValue += bond->data(TreeColumn::Value).toDouble();
  }
  return totalValue;
}

double BankAssets::getTotalValueOfLoans() const {
  QModelIndex index = m_model->find(TreeColumn::Name, LOANS);
  TreeItem *item = m_model->getItem(index);
  double totalValue = 0.0;
  for (size_t i = 0; i < item->childCount(); i++) {
    auto bond = item->child(i);
    totalValue += bond->data(TreeColumn::Value).toDouble();
  }
  return totalValue;
}
