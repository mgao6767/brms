#ifndef BANKASSETS_H
#define BANKASSETS_H

#include "instruments.h"
#include "treemodel.h"
#include <QObject>
#include <ql/pricingengines/bond/discountingbondengine.hpp>

class BankAssets : public QObject {
  Q_OBJECT
public:
  BankAssets(QStringList header = {"Asset", "Value"});
  ~BankAssets();

  /**
   * @brief Returns the model.
   *
   * @return TreeModel* The model used for views.
   */
  TreeModel *model();

  /**
   * @brief Gets the amount of cash available.
   *
   * @return double
   */
  double getCash() const;

  /**
   * @brief Sets the amount of cash.
   *
   * @param amount new cash amount
   * @return true if successful
   * @return false if unsuccessful
   */
  bool setCash(double amount);

  /**
   * @brief Gets the amount of total Treasury securities.
   *
   * @return double
   */
  double getTotalValueOfTreasurySecurities() const;

  /**
   * @brief Gets the amount of total loans.
   *
   * @return double
   */
  double getTotalValueOfLoans() const;

  /**
   * @brief Adds Treasury Bill to assets.
   * Cash is deducted by the amount of the instrument's NPV.
   *
   * @param bill
   * @return true if successful
   * @return false if unsuccessful
   */
  bool addTreasuryBill(QuantLib::ZeroCouponBond &bill);

  /**
   * @brief Adds Treasury Note to assets.
   * Cash is deducted by the amount of the instrument's NPV.
   *
   * @param note
   * @return true if successful
   * @return false if unsuccessful
   */
  bool addTreasuryNote(QuantLib::FixedRateBond &note);

  /**
   * @brief Adds Treasury Bond to assets.
   * Cash is deducted by the amount of the instrument's NPV.
   *
   * @param bond
   * @return true if successful
   * @return false if unsuccessful
   */
  bool addTreasuryBond(QuantLib::FixedRateBond &bond);

  /**
   * @brief Sets the Treasury Pricing Engine
   * Used for repricing the treasury securities.
   * @param engine
   */
  void setTreasuryPricingEngine(
      const QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine> &engine);

  /**
   * @brief Returns the total assets.
   *
   * @return double The value of total assets.
   */
  double totalAssets() const;

private:
  const QString CASH{"Cash and reserves"};
  const QString TREASURY_SECURITIES{"Treasury Securities"};
  const QString LOANS{"Loans and other receivables"};

  TreeModel *m_model;
  std::vector<QuantLib::Bond> m_treasurySecurities;
  QuantLib::ext::shared_ptr<QuantLib::DiscountingBondEngine>
      m_treasuryPricingEngine;

  /**
   * @brief Adds a Treasury instrument to assets.
   * @param instrument
   * @param name Name to be displayed.
   * @return true if successful
   * @return false if unsuccessful
   */
  bool addTreasurySecurity(QuantLib::Bond &instrument, QString name);

  /**
   * @brief Updates the total value.
   */
  void updateTotalValue();

  void repriceTreasurySecurities();

public slots:
  void reprice();

signals:
  void totalAssetsChanged(double totalAssets);
};

#endif // BANKASSETS_H
