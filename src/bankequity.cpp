#include "brms/bankequity.h"

BankEquity::BankEquity(QStringList header) {
  m_model = new TreeModel(header);
  m_model->appendRow(QModelIndex(), {EQUITY, 0});
}

BankEquity::~BankEquity() { delete m_model; }

TreeModel *BankEquity::model() { return m_model; }

void BankEquity::reprice() {}

void BankEquity::reprice(double totalAssets, double totalLiabilities) {
  QModelIndex index = m_model->find(TreeColumn::Name, EQUITY);
  QModelIndex equityAmountIdx = index.siblingAtColumn(TreeColumn::Value);
  m_commonEquity = totalAssets - totalLiabilities;
  m_model->setData(equityAmountIdx, m_commonEquity);
}

double BankEquity::totalEquity() const {
  return m_commonEquity;
}
