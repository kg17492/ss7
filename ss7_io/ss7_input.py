from .ss7_reader import SS7_Reader
from ..ss7_member import SS7_Axis_and_Floor
import numpy as np


def floor_formatter(floor: str) -> str:
    return floor[:-1] if floor.endswith("F") else floor


class SS7_Input(SS7_Reader):
    """入力ファイルにまつわるメソッドを集めたクラス
    """
    axis_and_floor: SS7_Axis_and_Floor

    def __init__(self, filename: str) -> None:
        super().__init__(filename)
        self.axis_and_floor = SS7_Axis_and_Floor(
            self.get("軸名"),
            self.axis_location(),
            [h["階名"] for h in self.get("標準階高")],
            self.floor_height(),
            int(self.get("基本事項")["建物概要Y方向スパン数"]),
        )

    def get_without_cache(self, key: str):
        return super().get_without_cache(key).read_self()

    def axis_location(self) -> list[float]:
        """軸名に対応した軸の座標を返す
        """
        axis: list[str] = self.get("軸名")
        location: list[float] = [0 for _ in axis]
        s: dict[str, str]
        for s in self.get("基準スパン長"):
            l_axis: str
            r_axis: str
            l_axis, r_axis = [key.strip() for key in s["軸-軸"].split("-")]
            index_left: int = axis.index(l_axis)
            index_right: int = axis.index(r_axis)
            location[index_right] = location[index_left] + float(s["スパン長"])
        return location

    def floor_height(self) -> list[float]:
        """階名に対応した階高の高さを返す
        """
        height: list[int] = np.cumsum([float(h["階高"]) for h in self.get("標準階高")][::-1])[::-1].tolist()
        height.pop(0)
        height.append(0)
        return height

    def read(self, key: str) -> list[dict]:
        """keyで指定されたセクションを辞書形式で読む

        Args:
            - key:
                - RC柱断面
                - 壁開口
                - 耐震壁の指定
        """
        if key == "RC柱断面":
            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": floor_formatter(d["階"]),
                    "name": f'{"" if d["添字"] == "-" else d["添字"]}{d["柱符号"]}',
                    "dx": int(d["コンクリートDx"]),
                    "dy": int(d["コンクリートDy"]),
                    "concrete": d["コンクリート材料"],
                    "x_top": (f'{d["主筋本数柱頭X"]}-{d["主筋径柱頭X"]}', d["主筋材料柱頭X"]),
                    "y_top": (f'{d["主筋本数柱頭Y"]}-{d["主筋径柱頭Y"]}', d["主筋材料柱頭Y"]),
                    "x_bottom": (f'{d["主筋本数柱脚X"]}-{d["主筋径柱脚X"]}', d["主筋材料柱脚X"]),
                    "y_bottom": (f'{d["主筋本数柱脚Y"]}-{d["主筋径柱脚Y"]}', d["主筋材料柱脚Y"]),
                    "x_top_dt": int(d["主筋dt1柱頭X"]),
                    "y_top_dt": int(d["主筋dt1柱頭Y"]),
                    "x_bottom_dt": int(d["主筋dt1柱脚X"]),
                    "y_bottom_dt": int(d["主筋dt1柱脚Y"]),
                    "x_hoop": (f'{d["帯筋本数X"]}-{d["帯筋径"]}@{d["帯筋ピッチ"]}', d["帯筋材料"]),
                    "y_hoop": (f'{d["帯筋本数Y"]}-{d["帯筋径"]}@{d["帯筋ピッチ"]}', d["帯筋材料"]),
                }
            return [temp(d) for d in filter(
                lambda d: d["コンクリートDx"] != "",
                self.get(key),
            )]
        elif key == "壁開口":
            def temp(d: dict[str, str]) -> dict:
                frame: str
                l_axis: str
                r_axis: str
                frame, l_axis, r_axis = d["フレーム-軸-軸"].split(" - ")
                return {
                    "floor": floor_formatter(d["階"]),
                    "frame": frame,
                    "l_axis": l_axis,
                    "r_axis": r_axis,
                    "dimension": d["押えタイプ"],
                    "l1": float(d["開口の寸法と位置L1"]),
                    "l2": float(d["開口の寸法と位置L2"]),
                    "h1": float(d["開口の寸法と位置H1"]),
                    "h2": float(d["開口の寸法と位置H2"]),
                }
        elif key == "耐震壁の指定":
            def temp(d: dict[str, str]) -> dict[str]:
                frame: str
                l_axis: str
                r_axis: str
                frame, l_axis, r_axis = d["フレーム-軸-軸"].split(" - ")
                return {
                    "floor": floor_formatter(d["階"]),
                    "frame": frame,
                    "l_axis": l_axis,
                    "r_axis": r_axis,
                    "multi_openings": d["複数開口の扱い"],
                }
        else:
            def temp(d: dict[str, str]) -> dict[str, str]:
                return d
        return [temp(d) for d in self.get(key)]
