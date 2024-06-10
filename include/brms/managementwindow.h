#ifndef MANAGEMENTWINDOW_H
#define MANAGEMENTWINDOW_H

#include <QWidget>

namespace Ui {
class ManagementWindow;
}

class ManagementWindow : public QWidget
{
    Q_OBJECT

public:
    explicit ManagementWindow(QWidget *parent = nullptr);
    ~ManagementWindow();

private:
    Ui::ManagementWindow *ui;
};

#endif // MANAGEMENTWINDOW_H
