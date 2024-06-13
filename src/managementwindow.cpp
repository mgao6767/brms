#include "brms/managementwindow.h"
#include "brms/treasuryfutures.h"
#include "ui_managementwindow.h"
#include <QDebug>
#include <QUrl>

ManagementWindow::ManagementWindow(QWidget *parent)
    : QWidget(parent), ui(new Ui::ManagementWindow) {
  ui->setupUi(this);
  auto src = QUrl::fromLocalFile(":/resources/treasury_futures.html");
  ui->textBrowserTreasuryFutures->setSource(src, QTextDocument::HtmlResource);
  ui->textBrowserTreasuryFutures->viewport()->setAutoFillBackground(false);
  ui->comboBoxTreasuryFuturesPosition->addItems({"Long", "Short"});

  auto tf = new TreasuryFutures();
  auto view = ui->tableViewTreasuryFutures;
  view->setModel(tf->model());
  view->horizontalHeader()->setSectionResizeMode(QHeaderView::Stretch);
  view->horizontalHeader()->setDefaultAlignment(Qt::AlignLeft);
  view->verticalHeader()->setSectionResizeMode(QHeaderView::Stretch);
  view->setSelectionMode(QAbstractItemView::SingleSelection);
  view->setSelectionBehavior(QAbstractItemView::SelectRows);
  view->setEditTriggers(QAbstractItemView::NoEditTriggers);
}

ManagementWindow::~ManagementWindow() { delete ui; }
