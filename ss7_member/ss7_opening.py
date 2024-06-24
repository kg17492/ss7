from .ss7_member_between_columns import SS7_Member_Between_Columns


class SS7_Opening(SS7_Member_Between_Columns):
    """壁開口
    """
    floor: str
    frame: str
    l_axis: str
    r_axis: str
    dimension: str
    l1: float
    l2: float
    h1: float
    h2: float
    owner: str = ""

    located: bool = False
    left: float
    right: float
    bottom: float
    top: float
    width: float
    height: float
    ignore: bool

    def relative_to_absolute(
        self,
        span_inside: float,
        span_center: float,
        height_inside: float,
        height_center: float,
    ) -> "SS7_Opening":
        """壁の内法・芯々スパン/階高を受け取って、開口の相対位置入力を絶対位置に直す"""
        self.located = True

        def r2a(iwxsc: tuple[int, float, float, float, float]) -> list[float]:
            i: int
            w: float
            x: float
            s: float
            c: float
            i, w, x, s, c = iwxsc
            # x = \
            #     abs(x) + (c - s) / 2 if x < 0 and i == 0 else \
            #     abs(x) if x < 0 and i == 1 else \
            #     x
            # if i == 0 and x < (c - s) / 2:
            #     x = (c - s) / 2
            # elif i == 1 and x < 0:
            #     x = 0
            # elif i == 1 and self.dimension[i] in "356" and x < (c - s):
            #     x = c - s
            absolute: dict[str, list[float]] = {
                "1": [x, x + w],
                "2": [x - w / 2, x + w / 2],
                "3": [w, c - x],
                "5": [c - x - w / 2, c - x + w / 2],
                "6": [c - x - w, c - x],
            }
            return absolute[self.dimension[i]]

        self.left, self.right = r2a((0, self.l1, self.l2, span_inside, span_center))
        self.bottom, self.top = r2a((1, self.h1, self.h2, height_inside, height_center))
        self.width = self.right - self.left
        self.height = self.top - self.bottom
        self.ignore = all([
            (self.right - self.left) / span_inside < 0.05,
            ((self.right - self.left) * (self.top - self.bottom) / (span_inside * height_inside)) ** 0.5 < 0.05
        ])
        return self
