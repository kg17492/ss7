"""
ToDo:
    出力・建物情報のパースがうまく行っていない（辞書でも配列でもないため）
"""
from .. import ss7_tool
import re
from typing import Any


class Section_Temp(ss7_tool.String):
    def name(self) -> str:
        """セクション固有の名前を返す。
        """
        return " ".join([
            (
                col.split("=")[1] if "=" in col else
                col
            ) for col in self.read_as_table()[0]
        ]).strip(" ") if "name=" in self else "info"

    def key_string(self) -> ss7_tool.String:
        return ss7_tool.String(
            "\n".join(
                self.stripsplit(
                    "<unit>" if "<unit>" in self else "<data>"
                )[0].stripsplit(
                    "\n"
                )[1:]
            )
        )

    def keys(self) -> list[ss7_tool.String]:
        """セクションの2行目~<unit>もしくは<data>を読み取り、表の列見出しを返す。
        """
        if "<data>" not in self:
            return []
        keys: list[ss7_tool.String] = self.key_string().read_as_table().filled_from_left().accumulated()
        if len([key for key in filter(lambda key: key == "軸-軸", keys)]) == 2:
            idx: int = keys.index("軸-軸")
            keys[idx + 0] = "左軸"
            keys[idx + 1] = "右軸"
        if len([key for key in filter(lambda key: key == "壁筋材料縦", keys)]) == 2:
            idx: int
            idx = keys.index("壁筋材料縦")
            keys[idx + 1] = ""
            idx = keys.index("壁筋材料横")
            keys[idx + 1] = ""
        return keys

    def section(self) -> "Section":
        return Section(
            re.sub(
                "\\n+",
                "\\n",
                (
                    self.stripsplit("<data>")[1] if "<data>" in self else
                    self
                ).removeprefix("\n")
            ),
            self.name(),
            self.keys(),
        )


class Section(ss7_tool.String):
    name: str
    keys: list[str]

    def __new__(cls, content, name: str, keys: list[ss7_tool.String]) -> "Section":
        ret: "Section" = super().__new__(cls, content)
        ret.name = name
        ret.keys = keys
        return ret

    def read_self(self) -> Any:
        if "<RE>" not in self and self.count("\n") > 1:
            keys: list[ss7_tool.String] = ss7_tool.Table(
                self.read_as_table().transposed()[:-1]
            ).filled_from_left().accumulated()
            values: list[ss7_tool.String] = self.read_as_table().transposed()[-1]
            return ss7_tool.String(f'{",".join(keys)}\n{",".join(values)}').read_as_dict()[0]
        elif all([len(table[0]) == 1 for table in self.read_as_list_of_table()]):
            return [table[0][0] for table in self.read_as_list_of_table()]
        elif all([len(table) == 1 for table in self.read_as_list_of_table()]):
            return self.read_as_list_of_dict()
        else:
            return self.read_as_list_of_table()

    def read_as_list_of_dict(self) -> list[dict[str, str]]:
        return ss7_tool.String(f'{",".join(self.keys)}\n{self.replace(",<RE>", "")}').read_as_dict()

    def read_as_list_of_table(self) -> list[ss7_tool.Table]:
        return [p.read_as_table() for p in filter(lambda p: len(p[0]) > 0, self.stripsplit(",<RE>\n"))]

    def read_as_list_of_line(self) -> list[list[ss7_tool.String]]:
        return [p[0] for p in self.read_as_list_of_table()]

    def read_first_line_as_list_of_dict(self) -> list[dict[str, str]]:
        return Section(
            ss7_tool.Table(self.read_as_list_of_line()).to_text(),
            self.name,
            self.keys,
        ).read_as_list_of_dict()


class SS7_Reader(list[Section]):
    """SS7_InputとSS7_Outputの親クラス
    """
    filename: str
    gotten_list: list[str] = []
    gotten_dict: dict[str, str] = {}

    def __init__(self, filename: str) -> None:
        """
        Args:
            filename: SS7の入出力CSVパス
        """

        self.filename = filename
        self.gotten_list = []
        super().__init__([Section_Temp(
            s if "ApName" in s else f'name={s}'
        ).section() for s in ss7_tool.read_text(
            filename
        ).multiple_replace(
            "－", "-",
            "靱", "靭",
        ).stripsplit(
            "name="
        )])

    def search(self, keyword: str) -> list[Section]:
        """keywordを含むデータ[辞書配列]を全て返す"""
        return [d for d in filter(lambda d: keyword in d.name, self)]

    def keys(self, keyword: str = "") -> list[str]:
        """keywordを含むkeyを全て返す"""
        return [d.name for d in self.search(keyword)]

    def get(self, key: str) -> Section:
        """keyによって指定される事項のデータ[配列]を1つ返す
        """
        self.gotten_list.append(key)
        found_dict: list[Section] = self.search(key)
        if len(found_dict) < 1:
            if key not in self.gotten_list[:-1]:
                print(f"{key}に該当するデータはありません。")
            return None
        elif len(found_dict) > 1 and key not in self.gotten_list[:-1]:
            print(f"{key}に該当するデータが複数あります: " + " ".join([d.name for d in found_dict]))

        return found_dict[0]
