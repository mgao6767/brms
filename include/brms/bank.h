#ifndef BANK_H
#define BANK_H

#include "brms/treemodel.h"
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

  TreeModel *m_assets;
  void addBond(QuantLib::FixedRateBond bond);
  const std::vector<QuantLib::FixedRateBond> &bonds();
  void setBondPricingEngine(
      const QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine> &engine);
  void init(QDate today); // init with fake data
  void printBonds();

private:
  std::vector<QuantLib::FixedRateBond> m_fixedRateBonds;
  QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine>
      m_bondPricingEngine;
};

#endif // BANK_H
