from .ss7_rc_column import SS7_RC_Column
from .ss7_member_base import SS7_Member_Base
from .. import ss7_tool


class SS7_Member_Between_Columns(SS7_Member_Base):
    frame: str
    l_axis: str
    r_axis: str
    has_left_wall: bool = False
    has_right_wall: bool = False

    def l_column_key(self) -> str:
        x_axis: str = self.l_axis if self.direction() == "x" else self.frame
        y_axis: str = self.l_axis if self.direction() == "y" else self.frame
        return f"{self.floor}F_{x_axis}-{y_axis}"

    def r_column_key(self) -> str:
        x_axis: str = self.r_axis if self.direction() == "x" else self.frame
        y_axis: str = self.r_axis if self.direction() == "y" else self.frame
        return f"{self.floor}F_{x_axis}-{y_axis}"

    def key(self) -> str:
        return f"{self.frame}_{self.floor}F_{self.l_axis}-{self.r_axis}"

    def key_in_int(self) -> str:
        return f"{self.in_int(self.frame)}_{self.floor}F_{self.in_int(self.l_axis)}-{self.in_int(self.r_axis)}"

    def direction(self) -> str:
        return self.ss7_axis_and_floor.direction(self.frame)

    def other_direction(self) -> str:
        return "x" if self.direction() == "y" else "y"

    def includes(self, other: "SS7_Member_Between_Columns") -> bool:
        return self.ss7_axis_and_floor.is_a_in_b(
            (other.frame, other.floor, other.l_axis, other.r_axis),
            (self.frame, self.floor, self.l_axis, self.r_axis),
        )

    rc_column_class: SS7_RC_Column = SS7_RC_Column
    l_column: SS7_RC_Column
    r_column: SS7_RC_Column
    towards: str = "+"

    def get_column(self, columns: list[SS7_RC_Column]) -> None:
        for column in columns:
            if column.key() == self.l_column_key():
                self.l_column = column
                self.l_column.direction = self.direction()
            elif column.key() == self.r_column_key():
                self.r_column = column
                self.r_column.direction = self.direction()

    def compare(self, title: str, a: float, b: float, digit: int = 3) -> None:
        if not ss7_tool.a_equals_to_b(a, b, digit):
            print(f"{self.key()}\t{title}\t{a:.{digit}g}\t{b:.{digit}g}")

    def load_key(self) -> str:
        if self.direction() == "x" and self.towards == "+":
            return "dsxp"
        elif self.direction() == "x" and self.towards == "-":
            return "dsxm"
        elif self.direction() == "y" and self.towards == "+":
            return "dsyp"
        elif self.direction() == "y" and self.towards == "-":
            return "dsym"
        else:
            raise ValueError(f"load_key: {self.direction()}{self.towards}")

    def l_column_axial_force(self) -> float:
        return getattr(self.l_column, f"{self.load_key()}_n_c_bottom") / (2 if self.has_left_wall else 1)

    def r_column_axial_force(self) -> float:
        return getattr(self.r_column, f"{self.load_key()}_n_c_bottom") / (2 if self.has_right_wall else 1)
