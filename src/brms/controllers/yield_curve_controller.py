from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from PySide6.QtCore import QFile, Qt, QTextStream

from brms.models import YieldCurveModel
from brms.views import YieldCurveWidget


class YieldCurveController:

    def __init__(self, model: YieldCurveModel, view: YieldCurveWidget):
        self.model = model
        self.view = view

        self.view.set_model(self.model)

        # Connect the selection changed signal to the slot
        self.view.table_view.selectionModel().selectionChanged.connect(self.update_plot)
        self.view.plot_widget.rescale_checkbox.stateChanged.connect(self.update_plot)
        self.view.plot_widget.grid_checkbox.stateChanged.connect(self.update_plot)

    def load_yield_data_from_qrc(self, resource_path: str):
        """
        Load yield curve data from a CSV file embedded in QRC and update the model.

        :param resource_path: Path to the resource in QRC.
        """
        file = QFile(resource_path)
        if not file.open(QFile.ReadOnly | QFile.Text):
            raise FileNotFoundError(f"Resource {resource_path} not found")

        stream = QTextStream(file)
        headers = stream.readLine().split(",")
        maturities = headers[1:]  # Assuming the first column is the date

        yield_data = {}

        while not stream.atEnd():
            line = stream.readLine()
            row = line.split(",")
            query_date = date.fromisoformat(row[0])
            yields = [
                (maturities[i], float(row[i + 1])) for i in range(len(maturities))
            ]
            yield_data[query_date] = yields

        file.close()

        # Update the model with the new yield data
        self.model.update_yield_data(yield_data)

        if self.model.rowCount() > 0:
            self.view.table_view.setCurrentIndex(self.model.index(0, 0))

    def update_plot(self):
        indexes = self.view.table_view.selectionModel().selectedRows()
        if not indexes:
            return

        row = indexes[0].row()
        model = self.model

        # Retrieve the date from the vertical header
        date_str = model.headerData(row, Qt.Vertical)
        date = datetime.strptime(date_str, "%Y-%m-%d")

        # Retrieve the maturities from the horizontal header
        maturities = [
            model.headerData(col, Qt.Horizontal) for col in range(model.columnCount())
        ]

        # Construct the x-axis values as "date+maturity"
        x_values = []
        for m in maturities:
            match m:
                case "1M" | "1 Mo":
                    new_date = date + relativedelta(months=1)
                case "2M" | "2 Mo":
                    new_date = date + relativedelta(months=2)
                case "3M" | "3 Mo":
                    new_date = date + relativedelta(months=3)
                case "4M" | "4 Mo":
                    new_date = date + relativedelta(months=4)
                case "6M" | "6 Mo":
                    new_date = date + relativedelta(months=6)
                case "1Y" | "1 Yr":
                    new_date = date + relativedelta(years=1)
                case "2Y" | "2 Yr":
                    new_date = date + relativedelta(years=2)
                case "3Y" | "3 Yr":
                    new_date = date + relativedelta(years=3)
                case "5Y" | "5 Yr":
                    new_date = date + relativedelta(years=5)
                case "7Y" | "7 Yr":
                    new_date = date + relativedelta(years=7)
                case "10Y" | "10 Yr":
                    new_date = date + relativedelta(years=10)
                case "20Y" | "20 Yr":
                    new_date = date + relativedelta(years=20)
                case "30Y" | "30 Yr":
                    new_date = date + relativedelta(years=30)
                case _:
                    new_date = date
            x_values.append(new_date)

        # Retrieve the yields for the selected row
        yields = [model.index(row, col).data() for col in range(model.columnCount())]

        # Update the plot with the new x and y values
        date_str = date.strftime("%B %d, %Y")  # Example: "January 01, 2023"
        title = f"Yield Curve as at {date_str}"
        rescale_y = self.view.plot_widget.rescale_checkbox.isChecked()
        show_grid = self.view.plot_widget.grid_checkbox.isChecked()
        self.view.plot_widget.update_plot(x_values, yields, title, rescale_y, show_grid)
