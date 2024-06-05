#include "brms/bankequity.h"

BankEquity::BankEquity(QStringList header) {
  m_model = new TreeModel(header);
  m_model->appendRow(QModelIndex(), {EQUITY, 50000.0});
}

BankEquity::~BankEquity() { delete m_model; }

TreeModel *BankEquity::model() { return m_model; }

void BankEquity::reprice() {}