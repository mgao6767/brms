#include "brms/instruments.h"

using namespace QuantLib;

Instruments::Instruments() {}

FixedRateBond Instruments::makeFixedRateTresuryBond(
    Date issueDate, Date matureDate, Real interestRate, Real faceAmount,
    Period frequency, Real redemption, Natural settlementDays,
    const ext::shared_ptr<PricingEngine> &pricingEngine) {

  Schedule fixedBondSchedule(issueDate, matureDate, frequency,
                             UnitedStates(UnitedStates::GovernmentBond),
                             Following, Following, DateGeneration::Backward,
                             false);

  FixedRateBond fixedRateBond(settlementDays, faceAmount, fixedBondSchedule,
                              std::vector<Rate>(1, interestRate),
                              ActualActual(ActualActual::Bond), Following,
                              100.0, issueDate);

  if (pricingEngine)
    fixedRateBond.setPricingEngine(pricingEngine);

  return fixedRateBond;
}

AmortizingFixedRateBond Instruments::makeAmortizingFixedRateBond(
    const Date &issueDate, const Period &maturity, const Rate &interestRate,
    const Real &faceAmount, const Frequency frequency,
    const ext::shared_ptr<PricingEngine> &pricingEngine) {

  auto calendar = NullCalendar();

  Schedule schedule = sinkingSchedule(issueDate, maturity, frequency, calendar);

  std::vector<Real> notionals =
      sinkingNotionals(maturity, frequency, interestRate, faceAmount);

  Natural settlementDays = 0;
  auto convention = ActualActual(ActualActual::ISMA);

  AmortizingFixedRateBond loan = AmortizingFixedRateBond(
      settlementDays, notionals, schedule, std::vector<Real>(1, interestRate),
      convention, Following, issueDate);

  if (pricingEngine)
    loan.setPricingEngine(pricingEngine);

  return loan;
}
