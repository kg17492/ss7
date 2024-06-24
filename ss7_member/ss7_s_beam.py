from .ss7_member_between_columns import SS7_Member_Between_Columns
from .ss7_axis_and_floor import SS7_Axis_and_Floor
from .. import ss7_material


class SS7_S_Beam(SS7_Member_Between_Columns):
    """S梁
        - 梁部材断面情報
        - 梁剛性表
    """
    floor: str
    frame: str
    l_axis: str
    r_axis: str
    name: str

    beam_length: float
    steel_left: ss7_material.Steel_Section
    steel_center: ss7_material.Steel_Section
    steel_right: ss7_material.Steel_Section

    steel_shape_left: str
    steel_shape_center: str
    steel_shape_right: str
    steel_type_left: str
    steel_type_center: str
    steel_type_right: str

    def __init__(self, dictionary: dict, axis_and_floor: SS7_Axis_and_Floor) -> None:
        super().__init__(dictionary, axis_and_floor)
        self.steel_left = ss7_material.Steel_Section(self.steel_shape_left, self.steel_type_left)
        self.steel_center = ss7_material.Steel_Section(self.steel_shape_center, self.steel_type_center)
        self.steel_right = ss7_material.Steel_Section(self.steel_shape_right, self.steel_type_right)
