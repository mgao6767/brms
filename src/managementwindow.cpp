#include "brms/managementwindow.h"
#include "ui_managementwindow.h"
#include <QDebug>
#include <QUrl>

ManagementWindow::ManagementWindow(QWidget *parent)
    : QWidget(parent), ui(new Ui::ManagementWindow) {
  ui->setupUi(this);
  auto src = QUrl::fromLocalFile(":/resources/treasury_futures.html");
  ui->treasuryFuturesTextBrowser->setSource(src, QTextDocument::HtmlResource);
  ui->treasuryFuturesTextBrowser->viewport()->setAutoFillBackground(false);
}

ManagementWindow::~ManagementWindow() { delete ui; }
