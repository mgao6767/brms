#include "brms/managementwindow.h"
#include "ui_managementwindow.h"

ManagementWindow::ManagementWindow(QWidget *parent)
    : QWidget(parent)
    , ui(new Ui::ManagementWindow)
{
    ui->setupUi(this);
}

ManagementWindow::~ManagementWindow()
{
    delete ui;
}
