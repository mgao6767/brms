#ifndef BANKEQUITY_H
#define BANKEQUITY_H

#include "instruments.h"
#include "treemodel.h"
#include <QObject>
#include <QStringList>

class BankEquity : public QObject {
  Q_OBJECT
public:
  BankEquity(QStringList header);
  ~BankEquity();

  /**
   * @brief Returns the model.
   *
   * @return TreeModel* The model used for views.
   */
  TreeModel *model();

  double totalEquity() const;

private:
  const QString EQUITY{"Common equity"};

  TreeModel *m_model;
  double m_commonEquity;

public slots:
  void reprice();
  void reprice(double totalAssets, double totalLiabilities);
};

#endif // BANKEQUITY_H
