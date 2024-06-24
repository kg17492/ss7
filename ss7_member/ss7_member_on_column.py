from .ss7_member_base import SS7_Member_Base
from .. import ss7_tool


class SS7_Member_On_Column(SS7_Member_Base):
    x_axis: str
    y_axis: str

    def key(self) -> str:
        return f"{self.floor}F_{self.x_axis}-{self.y_axis}"

    def key_in_int(self) -> str:
        return f"{self.floor}F_{self.in_int(self.x_axis)}-{self.in_int(self.y_axis)}"

    def compare(self, title: str, a: float, b: float, digit: int = 3) -> None:
        if not ss7_tool.a_equals_to_b(a, b, digit):
            print(f"{self.key()} {title} {a:.0f} {b:.0f}")
