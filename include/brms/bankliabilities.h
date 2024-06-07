#ifndef BANKLIABILITIES_H
#define BANKLIABILITIES_H

#include "instruments.h"
#include "treemodel.h"
#include <QObject>
#include <QStringList>

class BankLiabilities : public QObject {
  Q_OBJECT
public:
  BankLiabilities(QStringList header = {"Liability", "Value"});
  ~BankLiabilities();

  /**
   * @brief Returns the model.
   *
   * @return TreeModel* The model used for views.
   */
  TreeModel *model();

  /**
   * @brief Get the amount of total liabilities
   *
   * @return double
   */
  double totalLiabilities() const;

  /**
   * @brief Adds fixed rate term deposit.
   * It emits a signal for assets to add cash.
   *
   * @param deposit
   */
  void addTermDeposits(QuantLib::FixedRateBond &deposit);

private:
  const QString DEPOSITS{"Deposits"};

  TreeModel *m_model;
  QuantLib::Date m_lastRepricingDate;
  std::vector<QuantLib::FixedRateBond> m_termDeposits;

  void updateTotalValue();
  void repriceDeposits();
  double getTotalValueOfTermDeposits() const;

public slots:
  void reprice();

signals:
  void totalLiabilitiesChanged(double totalLiabilities);
  void newDepositsTaken(double deposits);
  void interestAndWithdrawPaymentMade(double payment);
  void interestPaymentMade(QString name, double payment);
  void withdrawPaymentMade(QString name, double payment);
};

#endif // BANKLIABILITIES_H
