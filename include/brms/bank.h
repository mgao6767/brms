#ifndef BANK_H
#define BANK_H

#include "brms/bankassets.h"
#include "brms/bankequity.h"
#include "brms/bankliabilities.h"
#include <ql/qldefines.hpp>
#if !defined(BOOST_ALL_NO_LIB) && defined(BOOST_MSVC)
#include <ql/auto_link.hpp>
#endif
#include <ql/cashflows/couponpricer.hpp>
#include <ql/indexes/ibor/euribor.hpp>
#include <ql/indexes/ibor/usdlibor.hpp>
#include <ql/instruments/bonds/zerocouponbond.hpp>
#include <ql/pricingengines/bond/discountingbondengine.hpp>
#include <ql/termstructures/yield/bondhelpers.hpp>
#include <ql/termstructures/yield/piecewiseyieldcurve.hpp>
#include <ql/time/calendars/unitedstates.hpp>
#include <ql/time/daycounters/actual360.hpp>
#include <ql/time/daycounters/actualactual.hpp>

#include <QObject>

class Bank : public QObject {
  Q_OBJECT
public:
  explicit Bank(QObject *parent = nullptr);
  ~Bank();

  BankAssets *assets();
  BankLiabilities *liabilities();
  BankEquity *equity();

  void init(QDate today); // init with fake data

private:
  BankAssets *m_assets;
  BankLiabilities *m_liabilities;
  BankEquity *m_equity;
  int receivedRepricingSignals; // number of repricing signals received

private slots:
  void updateEquity(bool force = false);
};

#endif // BANK_H
