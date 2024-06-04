#ifndef BANKLIABILITIES_H
#define BANKLIABILITIES_H

#include "instruments.h"
#include "treemodel.h"
#include <QStringList>
#include <QColor>

class BankLiabilities {
public:
  BankLiabilities(QStringList header = {"Liability", "Value"});
  ~BankLiabilities();

  /**
   * @brief Returns the model.
   *
   * @return TreeModel* The model used for views.
   */
  TreeModel *model();

private:
  const QString DEPOSITS{"Deposits"};
  const QColor GREEN{0, 255, 0, 127};
  const QColor RED{255, 0, 0, 127};
  const QColor TRANSPARENT{Qt::transparent};

  TreeModel *m_model;

public slots:
  void reprice();
};

#endif // BANKLIABILITIES_H
