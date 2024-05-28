#include "brms/instruments.h"

Instruments::Instruments() {}

QuantLib::FixedRateBond Instruments::makeFixedRateTresuryBond(
    QuantLib::Date issueDate, QuantLib::Date matureDate,
    QuantLib::Real interestRate, QuantLib::Real faceAmount,
    QuantLib::Period frequency, QuantLib::Real redemption,
    QuantLib::Natural settlementDays,
    const QuantLib::ext::shared_ptr<QuantLib::PricingEngine> &pricingEngine) {

  QuantLib::Schedule fixedBondSchedule(
      issueDate, matureDate, frequency,
      QuantLib::UnitedStates(QuantLib::UnitedStates::GovernmentBond),
      QuantLib::Following, QuantLib::Following,
      QuantLib::DateGeneration::Backward, false);

  QuantLib::FixedRateBond fixedRateBond(
      settlementDays, faceAmount, fixedBondSchedule,
      std::vector<QuantLib::Rate>(1, interestRate),
      QuantLib::ActualActual(QuantLib::ActualActual::Bond), QuantLib::Following,
      100.0, issueDate);

  if (pricingEngine)
    fixedRateBond.setPricingEngine(pricingEngine);

  return fixedRateBond;
}