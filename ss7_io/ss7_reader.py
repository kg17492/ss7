"""
ToDo:
    出力・建物情報のパースがうまく行っていない（辞書でも配列でもないため）
"""
from .. import ss7_tool
import re
from typing import Any


class Section(ss7_tool.String):
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

    def data_string(self) -> "Data":
        return Data(
            re.sub(
                "\\n+",
                "\\n",
                (
                    self.stripsplit("<data>")[1] if "<data>" in self else
                    self
                ).removeprefix("\n")
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

    def data(self) -> Any:
        data: "Data" = self.data_string()
        keys: list[ss7_tool.String] = self.keys()
        if any([
            key in self.name() for key in [
                "建物情報",
                "断面リスト",
                "長期支点反力表",
                "長期支点反力表 支点反力 [kN] B1FL",
                "浮き上がりのチェック",
                "ルート判定表",
                "風圧力基本データ",
                "地震力基本データ",
            ]
        ]):
            return data.read_as_list_of_table()
        elif self.name() in ["崩壊メカニズム"]:
            return data.read_as_list_of_line()
        elif "SRC耐震壁保証設計(SRC規準)" in self.name():
            def paragraph2dict(p: ss7_tool.String) -> dict[str, str]:
                result: list[dict[str, str]] = Data(p).read_as_list_of_dict(keys)
                result[0]["右軸"] = result[0].pop("軸")
                result[0]["左軸"] = result[-1].pop("軸")
                result[0]["twmm"] = result[-1].pop("twmm")
                return result[0]
            return [paragraph2dict(p) for p in data.stripsplit(",<RE>\n")]
        elif any([
            key in self.name() for key in [
                "RC耐震壁保証設計(靭性指針式)",
                "地震用重量",
                "梁剛性表",
            ]
        ]):
            return data.read_first_line_as_list_of_dict(keys)
            return Data(
                ss7_tool.Table(data.read_as_list_of_line()).to_text()
            ).read_as_list_of_dict(keys)
        elif self.name() in [
            "部位別集計表(鉄骨)"
        ]:
            return data.read_as_list_of_dict(keys)
        else:
            return data.read_self(keys)

    def dictionary(self) -> dict:
        return {
            "name": self.name(),
            "keys": self.keys(),
            "data": self.data(),
        }


class Data(ss7_tool.String):
    def read_self(self, keys: list[ss7_tool.String]) -> Any:
        if "<RE>" not in self and self.count("\n") > 1:
            keys: list[ss7_tool.String] = ss7_tool.Table(
                self.read_as_table().transposed()[:-1]
            ).filled_from_left().accumulated()
            values: list[ss7_tool.String] = self.read_as_table().transposed()[-1]
            return ss7_tool.String(f'{",".join(keys)}\n{",".join(values)}').read_as_dict()[0]
        elif all([len(table[0]) == 1 for table in self.read_as_list_of_table()]):
            return [table[0][0] for table in self.read_as_list_of_table()]
        elif all([len(table) == 1 for table in self.read_as_list_of_table()]):
            return self.read_as_list_of_dict(keys)
        else:
            return self.read_as_list_of_table()

    def read_as_list_of_dict(self, keys: list[str]) -> list[dict[str, str]]:
        return ss7_tool.String(f'{",".join(keys)}\n{self.replace(",<RE>", "")}').read_as_dict()

    def read_as_list_of_table(self) -> list[ss7_tool.Table]:
        return [p.read_as_table() for p in filter(lambda p: len(p[0]) > 0, self.stripsplit(",<RE>\n"))]

    def read_as_list_of_line(self) -> list[list[ss7_tool.String]]:
        return [p[0] for p in self.read_as_list_of_table()]

    def read_first_line_as_list_of_dict(self, keys: list[str]) -> list[dict[str, str]]:
        return Data(
            ss7_tool.Table(self.read_as_list_of_line()).to_text()
        ).read_as_list_of_dict(keys)


class SS7_Reader:
    """SS7_InputとSS7_Outputの親クラス
    """
    data: list[dict]
    filename: str
    gotten: list[str]

    def __init__(self, filename: str) -> None:
        """
        Args:
            filename: SS7の入出力CSVパス
        """

        self.filename = filename
        self.gotten = []
        self.data = [Section(
            s if "ApName" in s else f'name={s}'
        ).dictionary() for s in ss7_tool.read_text(
            filename
        ).multiple_replace(
            "－", "-",
            "靱", "靭",
        ).stripsplit(
            "name="
        )]

    def save_json(self) -> None:
        """データをjsonファイルに書き出す。
        """
        ss7_tool.save_json(self.filename.replace(".csv", ".json"), self.data)

    def search(self, keyword: str) -> list[dict]:
        """keywordを含むデータ[辞書配列]を全て返す"""
        return [d for d in filter(lambda d: keyword in d["name"], self.data)]

    def keys(self, keyword: str = "") -> list[str]:
        """keywordを含むkeyを全て返す"""
        return [d["name"] for d in self.search(keyword)]

    def get(self, key: str) -> Any:
        """keyによって指定される事項のデータ[配列]を1つ返す
        """
        self.gotten.append(key)
        found_dict: list[dict] = self.search(key)
        if len(found_dict) < 1:
            if key not in self.gotten[:-1]:
                print(f"{key}に該当するデータはありません。")
            return {}
        elif len(found_dict) > 1 and key not in self.gotten[:-1]:
            print(f"{key}に該当するデータが複数あります: " + " ".join([d["name"] for d in found_dict]))
        return found_dict[0]["data"]
