from .ss7_axis_and_floor import SS7_Axis_and_Floor
from .. import ss7_tool


class SS7_Member_Base(ss7_tool.BaseClass):
    floor: str
    name: str
    ss7_axis_and_floor: SS7_Axis_and_Floor

    def __init__(self, dictionary: dict, axis_and_floor: SS7_Axis_and_Floor) -> None:
        super().__init__(dictionary)
        self.ss7_axis_and_floor = axis_and_floor

    def in_int(self, key: str) -> str:
        return f"{self.ss7_axis_and_floor.get_axis_index(key):02}"
