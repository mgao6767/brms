#ifndef INSTRUMENTS_H
#define INSTRUMENTS_H
#include <QMetaType>
#include <ql/instruments/bonds/all.hpp>
#include <ql/qldefines.hpp>
#include <ql/termstructures/yield/piecewiseyieldcurve.hpp>
#include <ql/time/calendars/unitedstates.hpp>
#include <ql/time/daycounters/actualactual.hpp>

class Instruments {
public:
  Instruments();

  QuantLib::FixedRateBond makeFixedRateTresuryBond(
      QuantLib::Date issueDate, QuantLib::Date matureDate,
      QuantLib::Real interestRate, QuantLib::Real faceAmount = 100.0,
      QuantLib::Period frequency = QuantLib::Period(QuantLib::Semiannual),
      QuantLib::Real redemption = 100.0, QuantLib::Natural settlementDays = 0,
      const QuantLib::ext::shared_ptr<QuantLib::PricingEngine> &pricingEngine =
          nullptr);

  QuantLib::AmortizingFixedRateBond makeAmortizingFixedRateBond(
      const QuantLib::Date &issueDate, const QuantLib::Period &maturity,
      const QuantLib::Rate &interestRate, const QuantLib::Real &faceAmount,
      const QuantLib::Frequency frequency = QuantLib::Monthly,
      const QuantLib::ext::shared_ptr<QuantLib::PricingEngine> &pricingEngine =
          nullptr);
};

#endif // INSTRUMENTS_H
