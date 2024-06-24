import matplotlib.pyplot as plt


class SS7_Axis_and_Floor:
    axis_key: list[str]
    axis_location: list[float]
    floor_key: list[str]
    floor_height: list[float]
    x_axis_num: int

    def __init__(
        self,
        axis_key: list[str],
        axis_location: list[float],
        floor_key: list[str],
        floor_height: list[float],
        x_axis_num: int,
    ) -> None:
        self.axis_key = axis_key
        self.axis_location = axis_location
        self.floor_key = floor_key
        self.floor_height = floor_height
        self.x_axis_num = x_axis_num + 1

    def x_axis(self) -> list[str]:
        return self.axis_key[0:self.x_axis_num]

    def y_axis(self) -> list[str]:
        return self.axis_key[self.x_axis_num:]

    def direction(self, frame: str) -> str:
        return "x" if frame in self.x_axis() else "y"

    def get_axis_index(self, axis: str) -> int:
        """軸名に対応するインデックスを返す"""
        return self.axis_key.index(axis)

    def is_a_in_b(self, a: tuple[str, str, str, str], b: tuple[str, str, str, str]) -> bool:
        """階・通り・左右の通りによって規定されるaがbの中に納まっているかの真偽値を返す"""
        a_floor: str
        a_frame: str
        a_axis_left: str
        a_axis_right: str
        b_floor: str
        b_frame: str
        b_axis_left: str
        b_axis_right: str
        a_floor, a_frame, a_axis_left, a_axis_right = a
        b_floor, b_frame, b_axis_left, b_axis_right = b
        return all([
            a_floor == b_floor,
            a_frame == b_frame,
            self.get_axis_index(b_axis_left) <= self.get_axis_index(a_axis_left),
            self.get_axis_index(a_axis_right) <= self.get_axis_index(b_axis_right),
        ])

    def get_axis_location(self, axis: str) -> float:
        """軸の絶対位置を返す"""
        return self.axis_location[self.get_axis_index(axis)]

    def get_floor_location(self, floor: str) -> float:
        """階の絶対位置を返す"""
        return self.floor_height[self.floor_key.index(floor)]

    def axis_in_elevation(self, frame: str) -> None:
        """Matplotlibにおいて、立面図の軸等を設定する"""
        xmin: float
        xmax: float
        ymin: float
        ymax: float
        xmin, xmax = plt.xlim()
        ymin, ymax = plt.ylim()
        xticklabel: list[str] = [key for key in filter(lambda x: "_" not in x and x[0].isdecimal() != frame[0].isdecimal(), self.axis_key)]
        xtick: list[float] = [self.get_axis_location(key) for key in xticklabel]
        yticklabel: list[str] = self.floor_key
        ytick: list[float] = self.floor_height
        plt.vlines(x=xtick, ymin=ymin, ymax=ymax, color="black", linestyles="dashdot", lw=0.5)
        plt.hlines(y=ytick, xmin=xmin, xmax=xmax, color="black", linestyles="dashdot", lw=0.5)
        plt.xticks(xtick, ["" if "_" in key else key for key in xticklabel])
        plt.yticks(ytick, yticklabel)
        plt.xlim(xmin, xmax)
        plt.ylim(ymin, ymax)
