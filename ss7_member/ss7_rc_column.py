from .ss7_member_on_column import SS7_Member_On_Column
from .ss7_axis_and_floor import SS7_Axis_and_Floor
from .. import ss7_material


class SS7_RC_Column(SS7_Member_On_Column):
    """RC, SRC柱
    """
    floor: str
    x_axis: str
    y_axis: str
    name: str
    direction: str

    sx_top: ss7_material.Steel_Section = ()
    sy_top: ss7_material.Steel_Section = ()
    sxy_top: ss7_material.Steel_Section = ()
    sx_bottom: ss7_material.Steel_Section = ()
    sy_bottom: ss7_material.Steel_Section = ()
    sxy_bottom: ss7_material.Steel_Section = ()
    dx: int
    dy: int
    concrete: ss7_material.Concrete
    x_top: ss7_material.Main_Reinforcement
    y_top: ss7_material.Main_Reinforcement
    x_top_dt: int
    y_top_dt: int
    x_bottom: ss7_material.Main_Reinforcement
    y_bottom: ss7_material.Main_Reinforcement
    x_bottom_dt: int
    y_bottom_dt: int
    x_hoop: ss7_material.Hoop_Reinforcement
    y_hoop: ss7_material.Hoop_Reinforcement

    gpp_n_bottom: float

    def __init__(self, dictionary: dict, axis_and_floor: SS7_Axis_and_Floor) -> None:
        super().__init__(dictionary, axis_and_floor)
        self.sx_top = ss7_material.Steel_Section(*self.sx_top)
        self.sy_top = ss7_material.Steel_Section(*self.sy_top)
        self.sxy_top = ss7_material.Steel_Section(*self.sxy_top)
        self.sx_bottom = ss7_material.Steel_Section(*self.sx_bottom)
        self.sy_bottom = ss7_material.Steel_Section(*self.sy_bottom)
        self.sxy_bottom = ss7_material.Steel_Section(*self.sxy_bottom)
        self.concrete = ss7_material.Concrete(self.concrete)
        self.x_top = ss7_material.Main_Reinforcement(*self.x_top)
        self.y_top = ss7_material.Main_Reinforcement(*self.y_top)
        self.x_bottom = ss7_material.Main_Reinforcement(*self.x_bottom)
        self.y_bottom = ss7_material.Main_Reinforcement(*self.y_bottom)
        self.x_hoop = ss7_material.Hoop_Reinforcement(*self.x_hoop)
        self.y_hoop = ss7_material.Hoop_Reinforcement(*self.y_hoop)

    def depth(self, direction: str) -> float:
        return self.dx if direction == "x" else self.dy

    def width(self, direction: str) -> float:
        return self.dy if direction == "x" else self.dx

    def area(self) -> float:
        return self.dx * self.dy

    def whole_steel_area(self) -> float:
        return sum([
            2 * self.x_bottom.area_for_whole(),
            2 * self.y_bottom.area_for_whole(),
            self.sx_bottom.calculated_area(),
            self.sy_bottom.calculated_area(),
            self.sxy_bottom.calculated_area(),
        ])

    def between_main_reinforcement(self, direction: str) -> float:
        return self.depth(direction) - 2 * (
            self.x_top_dt if direction == "x" else
            self.y_top_dt
        )

    def hoop_ratio(self, direction: str) -> float:
        return (
            self.x_hoop.ratio(self.dy) if direction == "x" else
            self.y_hoop.ratio(self.dx)
        )

    def hoop_ratio_by_strength(self, direction: str, key: str) -> float:
        return (
            self.x_hoop.ratio_by_strength(self.dy, key) if direction == "x" else
            self.y_hoop.ratio_by_strength(self.dx, key)
        )

    def axial_force(self, load: str) -> float:
        return getattr(self, f"{load}_n_bottom")
