from .ss7_input_reader import SS7_Input_Reader
from ..ss7_member import SS7_Axis_and_Floor


class SS7_Input(SS7_Input_Reader):
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
