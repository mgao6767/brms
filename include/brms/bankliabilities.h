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

private:
  const QString DEPOSITS{"Deposits"};

  TreeModel *m_model;

public slots:
  void reprice();

signals:
  void totalLiabilitiesChanged(double totalLiabilities);
};

#endif // BANKLIABILITIES_H
