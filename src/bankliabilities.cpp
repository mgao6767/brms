#include "brms/bankliabilities.h"

BankLiabilities::BankLiabilities(QStringList header) {
  m_model = new TreeModel(header);
  m_model->appendRow(QModelIndex(), {DEPOSITS, 100000.0});
}

BankLiabilities::~BankLiabilities() { delete m_model; }

TreeModel *BankLiabilities::model() { return m_model; }

void BankLiabilities::reprice() {}
