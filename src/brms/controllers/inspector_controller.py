from brms.controllers.base import BRMSController
from brms.instruments.base import Instrument
from brms.instruments.visitors.inspection import InspectionVisitor
from brms.views.inspector_widget import BRMSInspectorWidget


class InspectorController(BRMSController):
    def __init__(self, inspector_widget: BRMSInspectorWidget):
        super().__init__()
        self.view = inspector_widget
        self.inspector = InspectionVisitor()

    def show_instrument_details(self, instrument: Instrument) -> None:
        """Show the details of the given instrument in the inspector view."""
        instrument.accept(self.inspector)
        details = self.inspector.get_result()
        data = self.format_instrument_details_for_inspector_tree_view(details)
        self.view.populate_data(data)

    def format_instrument_details_for_inspector_tree_view(self, data: dict) -> list[dict]:
        """Convert a dictionary to a list of dictionaries with keys 0 and 1.

        Example usage:
        data = {"Property1": "Value1", "Property2": "Value2"}
        Output: [{0: 'Property1', 1: 'Value1'}, {0: 'Property2', 1: 'Value2'}]

        data = {"Property1": "Value1", "PropertyGroup": {"Sub-property": "Sub-value"}}
        Output: [{0: 'Property1', 1: 'Value1'}, {0: 'PropertyGroup', 1: '', '_children': [{0: 'Sub-property', 1: 'Sub-value'}]}]
        """
        result = []
        for k, v in data.items():
            if isinstance(v, dict):
                result.append({0: k, 1: "", "_children": self.format_instrument_details_for_inspector_tree_view(v)})
            else:
                result.append({0: k, 1: v})
        return result

    def connect_signals(self) -> None:
        pass
