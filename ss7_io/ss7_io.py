from typing import TypeVar, Callable
from .ss7_input import SS7_Input
from .ss7_output import SS7_Output
from .. import ss7_member
from .. import ss7_tool
from functools import wraps


T = TypeVar("T")


class List(list[T]):
    def get(self, key: str) -> T:
        return self[[x.key() for x in self].index(key)]


def wrap_list(func) -> Callable:
    @wraps(func)
    def wrapper(*args) -> List[T]:
        return List(func(*args))
    return wrapper


class SS7_IO:
    """SS7の入力ファイルと出力ファイルを合わせたクラス
    """
    input: SS7_Input
    output: SS7_Output

    def __init__(self, input: str, output: str) -> None:
        """SS7の入力ファイルと出力ファイルを合わせたクラス

        Args:
            - input: SS7の入力CSVパス
            - output: SS7の出力CSVパス
        """
        if input is not None:
            self.input = SS7_Input(input)
        if output is not None:
            self.output = SS7_Output(output)

    @wrap_list
    def openings(self, member_class: ss7_member.SS7_Opening = ss7_member.SS7_Opening) -> list[ss7_member.SS7_Opening]:
        """壁開口

        Args:
            member_class: 開口クラス
        """
        return [member_class(d, self.input.axis_and_floor) for d in self.input.read("壁開口")]

    @wrap_list
    def walls(self, member_class: ss7_member.SS7_RC_Wall = ss7_member.SS7_RC_Wall) -> list[ss7_member.SS7_RC_Wall]:
        """RC・SRC耐震壁(耐震壁の指定, 剛性計算条件, 耐震壁部材断面情報, RC耐震壁断面算定表, SRC耐震壁断面算定表, rc_columns)

        Args:
            member_class: RC・SRC耐震壁クラス
        """
        walls: list[ss7_member.SS7_RC_Wall] = [
            member_class(d, self.input.axis_and_floor) for d in ss7_tool.merge_list_of_dict([
                self.output.read("耐震壁部材断面情報"),
                self.output.read("RC耐震壁断面算定表") + self.output.read("SRC耐震壁断面算定表"),
                self.input.read("耐震壁の指定"),
            ] + [
                self.output.read(key) for key in [
                    # "壁応力表(一次) G+P",
                    "壁応力表(二次) DSX+",
                    "壁応力表(二次) DSX-",
                    "壁応力表(二次) DSY+",
                    "壁応力表(二次) DSY-",
                    "壁応力表(危険断面位置) DSX+",
                    "壁応力表(危険断面位置) DSX-",
                    "壁応力表(危険断面位置) DSY+",
                    "壁応力表(危険断面位置) DSY-",
                    "RC耐震壁保証設計(靭性指針式) DSX+",
                    "RC耐震壁保証設計(靭性指針式) DSX-",
                    "RC耐震壁保証設計(靭性指針式) DSY+",
                    "RC耐震壁保証設計(靭性指針式) DSY-",
                    "RC耐震壁保証設計(靭性指針式の諸係数) DSX+",
                    "RC耐震壁保証設計(靭性指針式の諸係数) DSX-",
                    "RC耐震壁保証設計(靭性指針式の諸係数) DSY+",
                    "RC耐震壁保証設計(靭性指針式の諸係数) DSY-",
                ]
            ], lambda d: f'{d["floor"]}_{d["frame"]}_{d["l_axis"]}-{d["r_axis"]}')
        ]
        columns: list = self.rc_columns(member_class.rc_column_class)
        openings: list = self.openings(member_class.opening_class)
        data: dict = self.input.get("剛性計算条件 RC・SRC耐震壁・床版")
        multi_openings: str = {
            "1": "包絡開口",
            "2": "等面積",
            "3": "投影矩形",
        }[data["複数開口の扱い"]] if "複数開口の扱い" in data else "包絡開口"
        for wall in walls:
            wall.get_column(columns)
            if hasattr(wall, "l_column") and hasattr(wall, "r_column"):
                wall.get_openings(openings)
            if wall.multi_openings is None:
                wall.multi_openings = multi_openings
        return walls

    @wrap_list
    def rc_columns(self, member_class: ss7_member.SS7_RC_Column = ss7_member.SS7_RC_Column) -> list[ss7_member.SS7_RC_Column]:
        """RC・SRC柱(RC柱断面, RC柱断面情報, 柱部材断面情報)

        Args:
            member_class: RC・SRC柱クラス
        """
        return [member_class(d, self.input.axis_and_floor) for d in filter(
            lambda d: "concrete" in d and d["dy"] > 0,
            ss7_tool.merge_list_of_dict(
                [
                    #     ss7_tool.merge_list_of_dict(
                    #         [
                    #             self.output.read("RC柱断面情報"),
                    #             self.input.read("RC柱断面"),
                    #         ],
                    #         lambda d: f'{d["floor"]}_{d["name"]}',
                    #     ) + self.output.read("柱部材断面情報")
                    # ] + [
                    self.output.read(key) for key in [
                        "柱部材断面情報",
                        # "柱応力表(一次) G+P",
                        # "柱応力表(二次) DSX+",
                        # "柱応力表(二次) DSX-",
                        # "柱応力表(二次) DSY+",
                        # "柱応力表(二次) DSY-",
                        "柱初期応力表 DSX+",
                        "柱初期応力表 DSX-",
                        "柱初期応力表 DSY+",
                        "柱初期応力表 DSY-",
                        "柱応力表(危険断面位置) DSX+",
                        "柱応力表(危険断面位置) DSX-",
                        "柱応力表(危険断面位置) DSY+",
                        "柱応力表(危険断面位置) DSY-",
                    ]
                ],
                lambda d: f'{d["floor"]}_{d["x_axis"]}-{d["y_axis"]}',
            ),
        )]

    @wrap_list
    def s_columns(self, member_class: ss7_member.SS7_S_Column = ss7_member.SS7_S_Column) -> list[ss7_member.SS7_S_Column]:
        """S柱(柱部材断面情報)

        Args:
            member_class: S柱クラス
        """
        return [member_class(d, self.input.axis_and_floor) for d in filter(
            lambda d: d["dx"] == 0,
            self.output.read("柱部材断面情報")
        )]

    @wrap_list
    def s_beams(self, member_class: ss7_member.SS7_S_Beam = ss7_member.SS7_S_Beam) -> list[ss7_member.SS7_S_Beam]:
        """S梁(梁部材断面情報)

        Args:
            member_class: S柱クラス
        """
        return [member_class(d, self.input.axis_and_floor) for d in filter(
            lambda d: d["steel_shape_left"] != "",
            ss7_tool.merge_list_of_dict([
                self.output.read(key) for key in [
                    "梁部材断面情報",
                    "梁剛性表 鉛直時",
                ]
            ], lambda d: f'{d["floor"]}_{d["frame"]}_{d["l_axis"]}-{d["r_axis"]}')
        )]

    @wrap_list
    def multi_span_shear_walls(self, member_class: ss7_member.SS7_MultiSpanShearWall = ss7_member.SS7_MultiSpanShearWall) -> list[ss7_member.SS7_MultiSpanShearWall]:
        """連スパン耐震壁(連スパン壁応力表(一次) G+P, EX+, EX-, EY+, EY-, walls)

        Args:
            member_class: 連スパン耐震壁クラス
        """
        ms_walls: list[ss7_member.SS7_MultiSpanShearWall] = [member_class(d, self.input.axis_and_floor) for d in ss7_tool.merge_list_of_dict([
            self.output.read(key) for key in [
                # "連スパン壁応力表(一次) G+P",
                "連スパン壁応力表(二次) DSX+",
                # "連スパン壁応力表(二次) DSX-",
                # "連スパン壁応力表(二次) DSY+",
                # "連スパン壁応力表(二次) DSY-",
                "連スパン壁応力表(危険断面位置) DSX+",
                "連スパン壁応力表(危険断面位置) DSX-",
                "連スパン壁応力表(危険断面位置) DSY+",
                "連スパン壁応力表(危険断面位置) DSY-",
                "SRC耐震壁保証設計(SRC規準) DSX+",
                "SRC耐震壁保証設計(SRC規準) DSX-",
                "SRC耐震壁保証設計(SRC規準) DSY+",
                "SRC耐震壁保証設計(SRC規準) DSY-",
            ]
        ], lambda d: f'{d["floor"]}_{d["frame"]}_{d["l_axis"]}-{d["r_axis"]}')]
        walls: list = self.walls(member_class.rc_wall_class)
        columns: list = self.rc_columns(member_class.rc_column_class)
        for ms_wall in ms_walls:
            ms_wall.get_wall(walls)
            ms_wall.get_column(columns)
        return ms_walls
