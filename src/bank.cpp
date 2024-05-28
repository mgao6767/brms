#include "brms/bank.h"
#include "brms/instruments.h"
#include "brms/utils.h"
#include <qDebug>

Bank::Bank(QObject *parent) : QObject{parent} {
  m_assets = new TreeModel(bonds());
}

Bank::~Bank() { delete m_assets; }

void Bank::addBond(QuantLib::FixedRateBond bond) {
  m_fixedRateBonds.push_back(bond);
}
const std::vector<QuantLib::FixedRateBond> &Bank::bonds() {
  return m_fixedRateBonds;
}

void Bank::printBonds() {
  for (auto &b : bonds()) {
    QDate matureDate = qlDateToQDate(b.maturityDate());
    qDebug() << matureDate << b.NPV();
  }
}

void Bank::setBondPricingEngine(
    const QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine> &engine) {
  m_bondPricingEngine = engine;
}

void Bank::init(QDate today) {

  QuantLib::Date todaysDate = qDateToQLDate(today);
  auto factory = Instruments();

  // let the bank has some treasury bonds
  for (size_t i = 0; i < 5; i++) {
    auto issueDate = todaysDate - i * QuantLib::Years;
    auto matureDate = issueDate + 5 * QuantLib::Years;
    auto bond = factory.makeFixedRateTresuryBond(issueDate, matureDate,
                                                 0.0125 * (i + 1));
    bond.setPricingEngine(m_bondPricingEngine);
    addBond(bond);
  }
  for (size_t i = 0; i < 1; i++) {
    auto issueDate = todaysDate - 1 * QuantLib::Years;
    auto matureDate = issueDate + 10 * QuantLib::Years;
    auto bond = factory.makeFixedRateTresuryBond(issueDate, matureDate, 0.015,
                                                 100 * 50);
    bond.setPricingEngine(m_bondPricingEngine);
    addBond(bond);
  }

  auto issueDate = todaysDate - 1 * QuantLib::Years;
  auto matureDate = issueDate + 20 * QuantLib::Years;
  auto bond =
      factory.makeFixedRateTresuryBond(issueDate, matureDate, 0.02, 100 * 100);
  bond.setPricingEngine(m_bondPricingEngine);
  addBond(bond);
}
