#include "brms/bank.h"
#include "brms/instruments.h"
#include "brms/utils.h"
#include <qDebug>

Bank::Bank(QObject *parent) : QObject{parent} {
  m_assets = new BankAssets({"Asset", "Value"});
  m_liabilities = new BankLiabilities({"Liability", "Value"});
  m_equity = new BankEquity({"Equity", "Value"});

  // set the initial equity
  reprice();

  connect(m_liabilities, SIGNAL(newDepositsTaken(double)), m_assets,
          SLOT(addCash(double)));
  connect(m_liabilities, SIGNAL(interestAndWithdrawPaymentMade(double)),
          m_assets, SLOT(deductCash(double)));
}

Bank::~Bank() {
  delete m_assets;
  delete m_liabilities;
  delete m_equity;
}

BankAssets *Bank::assets() { return m_assets; }

BankLiabilities *Bank::liabilities() { return m_liabilities; }

BankEquity *Bank::equity() { return m_equity; }

void Bank::reprice() {
  m_assets->reprice();
  m_liabilities->reprice();
  double totalAssets = m_assets->totalAssets();
  double totalLiabilities = m_liabilities->totalLiabilities();
  m_equity->reprice(totalAssets, totalLiabilities);
}

void Bank::init(QDate today) {

  QuantLib::Date todaysDate = qDateToQLDate(today);
  auto factory = Instruments();

  auto deposit = factory.makeTermDeposits(todaysDate - 1 * QuantLib::Years,
                                          QuantLib::Period(5, QuantLib::Years),
                                          0.05, 300000);
  liabilities()->addTermDeposits(deposit);

  auto deposit2 = factory.makeTermDeposits(todaysDate - 6 * QuantLib::Months,
                                           QuantLib::Period(3, QuantLib::Years),
                                           0.032, 100000);
  liabilities()->addTermDeposits(deposit2);

  auto deposit3 = factory.makeTermDeposits(todaysDate - 103 * QuantLib::Weeks,
                                           QuantLib::Period(2, QuantLib::Years),
                                           0.02, 50000);
  liabilities()->addTermDeposits(deposit3);

  auto deposit4 = factory.makeTermDeposits(todaysDate - 88 * QuantLib::Weeks,
                                           QuantLib::Period(5, QuantLib::Years),
                                           0.052, 200000);
  liabilities()->addTermDeposits(deposit4);

  // let the bank has some treasury bonds
  for (size_t i = 0; i < 5; i++) {
    auto issueDate = todaysDate - 4 * QuantLib::Years;
    auto matureDate = todaysDate + 1 * QuantLib::Weeks;
    auto bond = factory.makeFixedRateTresuryBond(issueDate, matureDate,
                                                 0.0125 * (i + 1), 10000);
    assets()->addTreasuryNote(bond);
  }
  for (size_t i = 0; i < 1; i++) {
    auto issueDate = todaysDate - 1 * QuantLib::Years;
    auto matureDate = issueDate + 10 * QuantLib::Years;
    auto bond = factory.makeFixedRateTresuryBond(issueDate, matureDate, 0.015,
                                                 100 * 200);
    assets()->addTreasuryNote(bond);
  }

  auto issueDate = todaysDate - 1 * QuantLib::Years;
  auto matureDate = issueDate + 20 * QuantLib::Years;
  auto bond =
      factory.makeFixedRateTresuryBond(issueDate, matureDate, 0.02, 200000);
  assets()->addTreasuryBond(bond);

  auto loan = factory.makeAmortizingFixedRateBond(
      todaysDate, QuantLib::Period(30, QuantLib::Years), 0.07, 100000);
  assets()->addAmortizingFixedRateLoan(loan);

  auto loan2 = factory.makeAmortizingFixedRateBond(
      issueDate - 10 * QuantLib::Years, QuantLib::Period(30, QuantLib::Years),
      0.05, 200000);
  assets()->addAmortizingFixedRateLoan(loan2);

  auto loan3 = factory.makeAmortizingFixedRateBond(
      QuantLib::Date(11, QuantLib::Oct, today.year() - 5),
      QuantLib::Period(20, QuantLib::Years), 0.04, 300000);
  assets()->addAmortizingFixedRateLoan(loan3);

  // force refresh to remove inital coloring
  assets()->reprice();
  liabilities()->reprice();
  liabilities()->reprice();
  equity()->reprice(assets()->totalAssets(), liabilities()->totalLiabilities());
}
