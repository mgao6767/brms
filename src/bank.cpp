#include "brms/bank.h"
#include "brms/instruments.h"
#include "brms/utils.h"
#include <qDebug>

Bank::Bank(QObject *parent) : QObject{parent} {
  m_assets = new BankAssets({"Asset", "Value"});
  m_liabilities = new BankLiabilities({"Liability", "Value"});
  m_equity = new BankEquity({"Equity", "Value"});
}

Bank::~Bank() {
  delete m_assets;
  delete m_liabilities;
  delete m_equity;
}

BankAssets *Bank::assets() { return m_assets; }
BankLiabilities *Bank::liabilities() { return m_liabilities; }
BankEquity *Bank::equity() { return m_equity; }

void Bank::init(QDate today) {

  QuantLib::Date todaysDate = qDateToQLDate(today);
  auto factory = Instruments();

  // let the bank has some treasury bonds
  for (size_t i = 0; i < 5; i++) {
    auto issueDate = todaysDate - 4 * QuantLib::Years;
    auto matureDate = todaysDate + 1 * QuantLib::Weeks;
    auto bond = factory.makeFixedRateTresuryBond(issueDate, matureDate,
                                                 0.0125 * (i + 1), 100);
    assets()->addTreasuryNote(bond);
  }
  for (size_t i = 0; i < 1; i++) {
    auto issueDate = todaysDate - 1 * QuantLib::Years;
    auto matureDate = issueDate + 10 * QuantLib::Years;
    auto bond = factory.makeFixedRateTresuryBond(issueDate, matureDate, 0.015,
                                                 100 * 50);
    assets()->addTreasuryNote(bond);
  }

  auto issueDate = todaysDate - 1 * QuantLib::Years;
  auto matureDate = issueDate + 20 * QuantLib::Years;
  auto bond =
      factory.makeFixedRateTresuryBond(issueDate, matureDate, 0.02, 100 * 100);
  assets()->addTreasuryBond(bond);
}
