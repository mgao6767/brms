#include "brms/bankliabilities.h"
#include "brms/utils.h"

using namespace QuantLib;

BankLiabilities::BankLiabilities(QStringList header) {
  m_model = new TreeModel(header);
  m_model->appendRow(QModelIndex(), {DEPOSITS, 0});
  m_lastRepricingDate = QuantLib::Settings::instance().evaluationDate();
}

BankLiabilities::~BankLiabilities() { delete m_model; }

TreeModel *BankLiabilities::model() { return m_model; }

void BankLiabilities::reprice() {
  repriceDeposits();

  updateTotalValue();
  emit totalLiabilitiesChanged(totalLiabilities());
  m_lastRepricingDate = QuantLib::Settings::instance().evaluationDate();
}

void BankLiabilities::repriceDeposits() {
  QModelIndex index = m_model->find(TreeColumn::Name, DEPOSITS);
  TreeItem *item = m_model->getItem(index);
  QuantLib::Date today = QuantLib::Settings::instance().evaluationDate();
  double totalPayment = 0.0;
  for (size_t i = 0; i < item->childCount(); i++) {
    auto d = item->child(i);
    // j is the location of the bond in the vector
    auto j = d->data(TreeColumn::Ref).toInt();
    QuantLib::Bond &instrument = m_termDeposits[j];
    auto valueIdx = m_model->index(i, TreeColumn::Value, index);
    auto colorIdx = m_model->index(i, TreeColumn::BackgroundColor, index);
    QString name =
        m_model
            ->data(valueIdx.siblingAtColumn(TreeColumn::Name), Qt::DisplayRole)
            .toString();
    if (m_lastRepricingDate > instrument.maturityDate()) {
      continue;
    }
    double interestPayment = 0;
    double notional = instrument.cashflows().back()->amount();
    for (auto &c : instrument.cashflows()) {
      // today in the simulation may not coincide with the cash flow day
      if (m_lastRepricingDate < c->date() && c->date() <= today) {
        if (instrument.maturityDate() <= today && c->amount() == notional) {
          // just matured. total payment += withdrawal of the deposit
          totalPayment += notional;
          m_model->setData(valueIdx, instrument.notional());
          m_model->setData(colorIdx, BRMS::TRANSPARENT);
          emit withdrawPaymentMade(name, notional);
        } else {
          // not yet matured. add the interest payment
          interestPayment += c->amount();
        }
      }
    }
    totalPayment += interestPayment;
    m_model->setData(valueIdx, instrument.notional());
    if (interestPayment > 0)
      emit interestPaymentMade(name, interestPayment);
  }
  // this is for adjusting assets' cash
  if (totalPayment > 0) {
    emit interestAndWithdrawPaymentMade(totalPayment);
  }
}

double BankLiabilities::totalLiabilities() const {
  double termDeposits = getTotalValueOfTermDeposits();
  return termDeposits;
}

void BankLiabilities::addTermDeposits(FixedRateBond &deposit) {
  QString name = QString("%1% %2-year term deposit %3");
  QDate maturityDate = qlDateToQDate(deposit.maturityDate());
  int mat = (deposit.maturityDate() - deposit.issueDate()) / 365;
  name = name.arg(QString::number(deposit.nextCouponRate() * 100, 'f', 3));
  name = name.arg(mat);
  name = name.arg(maturityDate.toString("dd/MM/yyyy"));

  m_termDeposits.push_back(deposit);

  // ref is the index of the bond in the vector
  QVariant ref = QVariant::fromValue<unsigned long>(m_termDeposits.size() - 1);
  // add to tree model
  QModelIndex index = m_model->find(TreeColumn::Name, DEPOSITS);
  TreeItem *depositsItem = m_model->getItem(index);
  TreeItem *item = new TreeItem({name, deposit.notional(), ref}, depositsItem);
  depositsItem->appendChild(item);
  updateTotalValue();
  emit newDepositsTaken(deposit.notional());
}

void BankLiabilities::updateTotalValue() {
  // term deposits
  QModelIndex indexDeposits = m_model->find(TreeColumn::Name, DEPOSITS);
  double totalValue = getTotalValueOfTermDeposits();
  m_model->setData(indexDeposits.siblingAtColumn(TreeColumn::Value),
                   totalValue);
}

double BankLiabilities::getTotalValueOfTermDeposits() const {
  QModelIndex index = m_model->find(TreeColumn::Name, DEPOSITS);
  TreeItem *item = m_model->getItem(index);
  double totalValue = 0.0;
  for (size_t i = 0; i < item->childCount(); i++) {
    auto d = item->child(i);
    totalValue += d->data(TreeColumn::Value).toDouble();
  }
  return totalValue;
}
