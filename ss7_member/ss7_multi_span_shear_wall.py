import numpy as np
from .ss7_member_between_columns import SS7_Member_Between_Columns
from .ss7_rc_wall import SS7_RC_Wall
from .ss7_rc_column import SS7_RC_Column
from .ss7_axis_and_floor import SS7_Axis_and_Floor
from .. import ss7_tool


class SS7_MultiSpanShearWall(SS7_Member_Between_Columns):
    """連スパン壁
    """
    floor: str
    frame: str
    l_axis: str
    r_axis: str

    gpp_m_bottom: float
    gpp_n_bottom: float
    gpp_q_bottom: float

    rc_wall_class: SS7_RC_Wall = SS7_RC_Wall
    rc_column_class: SS7_RC_Column = SS7_RC_Column
    walls: list[SS7_RC_Wall]
    l_column: SS7_RC_Column
    r_column: SS7_RC_Column

    def __init__(self, dictionary: dict, axis_and_floor: SS7_Axis_and_Floor) -> None:
        super().__init__(dictionary, axis_and_floor)

    def get_wall(self, walls: list[SS7_RC_Wall]) -> None:
        self.walls = sorted(
            filter(
                lambda wall: self.includes(wall),
                walls
            ),
            key=lambda wall: self.ss7_axis_and_floor.get_axis_index(wall.l_axis),
        )
        for i in range(len(self.walls)):
            self.walls[i].has_left_wall = (i > 0)
            self.walls[i].has_right_wall = (i < len(self.walls) - 1)

    def reduction_ratio(self) -> float:
        """各耐震壁の重みづけ平均を行った開口低減率
        """
        ri: np.ndarray = 1 - np.array([w.reduction_ratio for w in self.walls])
        li: np.ndarray = np.array([w.span_center() for w in self.walls])
        ti: np.ndarray = np.array([w.wall_thickness for w in self.walls])
        return 1 - np.sqrt(np.sum(ri ** 2 * li * ti) / np.sum(li * ti))

    def span_center(self) -> float:
        return sum([w.span_center() for w in self.walls])

    def whole_length(self) -> float:
        """連スパン耐震壁の全長
        """
        d: str = self.direction()
        return sum([w.wall_length + w.l_column.depth(d) for w in self.walls]) + self.r_column.depth(d)

    def whole_area(self) -> float:
        return sum([w.area() + w.l_column.area() for w in self.walls]) + self.r_column.area()

    def effective_thickness(self) -> float:
        return self.whole_area() / self.whole_length()

    def effective_length(self) -> float:
        d: str = self.direction()
        return self.whole_length() - self.compression_column().depth(d) / 2

    def lever_arm_length(self) -> float:
        return 7 / 8 * self.effective_length()

    def tensile_steel_ratio(self) -> float:
        return 100 * self.tensile_column().whole_steel_area() / self.effective_thickness() / self.effective_length()

    def axial_force(self) -> float:
        return getattr(self, f"{self.load_key()}_n_critical")

    def moment(self) -> float:
        return getattr(self, f"{self.load_key()}_m_critical")

    def shear_force(self) -> float:
        return getattr(self, f"{self.load_key()}_q_critical")

    def axial_stress(self) -> float:
        return self.axial_force() / self.whole_area() * 1e3

    def minimum_concrete_strength(self) -> float:
        return min([w.concrete.fc for w in self.walls])

    @ss7_tool.clip_decorator(1, 3)
    def shear_span_ratio(self) -> float:
        return abs(self.moment() / self.shear_force()) / self.whole_length() * 1e3

    def minimum_reinforcement_index(self) -> int:
        return np.argmin([w.horizontal.ratio_by_strength(w.wall_thickness, "終局強度") for w in self.walls])

    def minimum_reinforcement_strength(self) -> float:
        return self.walls[self.minimum_reinforcement_index()].horizontal.strength("終局強度")

    # @ss7_tool.clip_decorator(max=1.2e-2)
    def minimum_reinforcement_ratio(self) -> float:
        return self.walls[self.minimum_reinforcement_index()].horizontal.ratio(self.effective_thickness())

    def src_ultimate_strength(self, towards: str = None) -> float:
        if towards is not None:
            self.towards = towards
        return self.reduction_ratio() * self.effective_thickness() * self.lever_arm_length() * sum([
            0.068 * self.tensile_steel_ratio() ** 0.23 * (self.minimum_concrete_strength() + 18) / np.sqrt(0.12 + self.shear_span_ratio()),
            0.85 * np.sqrt(self.minimum_reinforcement_strength() * self.minimum_reinforcement_ratio()),
            0.1 * self.axial_stress(),
        ]) / 1e3

    def jinsei_ultimate_strength(self, towards: str = None) -> float:
        if towards is not None:
            self.towards = towards
        return sum([
            w.jinsei_ultimate_strength() for w in self.walls
        ])

    def test(self, key: str, digit: int = 3) -> None:
        name_dict: dict[str, str] = {
            "せん断スパン比": "shear_span_ratio",
            "等価引張鋼材比": "tensile_steel_ratio",
            "終局せん断耐力": "src_ultimate_strength",
            "有効壁厚さ": "effective_thickness",
            "開口低減率": "reduction_ratio",
            "壁筋比": "minimum_reinforcement_ratio",
        }
        name: str = name_dict[key]
        for towards in ["+", "-"]:
            self.towards = towards
            self.compare(
                key,
                getattr(self, name)(),
                getattr(self, f"test_{self.load_key()}_{name}"),
                digit,
            )

    def tensile_column(self) -> SS7_RC_Column:
        return self.l_column if getattr(self, f"{self.load_key()}_m_critical") > 0 else self.r_column

    def compression_column(self) -> SS7_RC_Column:
        return self.r_column if getattr(self, f"{self.load_key()}_m_critical") > 0 else self.l_column
