#ifndef BANKEQUITY_H
#define BANKEQUITY_H

#include "instruments.h"
#include "treemodel.h"
#include <QColor>
#include <QStringList>

class BankEquity {
public:
  BankEquity(QStringList header);
  ~BankEquity();

  /**
   * @brief Returns the model.
   *
   * @return TreeModel* The model used for views.
   */
  TreeModel *model();

private:
  const QString EQUITY{"Common equity"};
  const QColor GREEN{0, 255, 0, 127};
  const QColor RED{255, 0, 0, 127};
  const QColor TRANSPARENT{Qt::transparent};

  TreeModel *m_model;

public slots:
  void reprice();
};

#endif // BANKEQUITY_H
