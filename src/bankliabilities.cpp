#include "brms/bankliabilities.h"

BankLiabilities::BankLiabilities(QStringList header) {
  m_model = new TreeModel(header);
  m_model->appendRow(QModelIndex(), {DEPOSITS, 800000});
}

BankLiabilities::~BankLiabilities() { delete m_model; }

TreeModel *BankLiabilities::model() { return m_model; }

void BankLiabilities::reprice() {

  emit totalLiabilitiesChanged(totalLiabilities());
}

double BankLiabilities::totalLiabilities() const { return 800000; }