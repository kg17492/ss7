from .ss7_reader import SS7_Reader
import numpy as np


class SS7_Sekisan(SS7_Reader):
    def get_index(self, key: str, element: str) -> int:
        return [row[key] for row in self.get("部位別集計表")].index(element)

    def steel_section(self) -> list[dict[str, str]]:
        return self.get("部位別集計表")[0:self.get_index("種類", "小計")]

    def brace_section(self) -> list[dict[str, str]]:
        return self.get("部位別集計表")[self.get_index("", "ブレース長さ・本数"):]

    def get_materials(self, member: str) -> set[str]:
        return set([row["材料"] for row in filter(
            lambda row: row[member] != "",
            self.steel_section(),
        )])

    def get_braces(self) -> set[str]:
        return set([row["材料"] for row in self.brace_section()])

    def sum_steel(self, member: str, material: str) -> float:
        return sum(
            [
                0 if row[member] == "" else float(row[member]) for row in filter(
                    lambda row: row["材料"] == material,
                    self.steel_section()
                )
            ]
        )

    def sum_of_member(self, member: str) -> float:
        return sum([
            self.sum_steel(
                member,
                material
            ) for material in self.get_materials(member)
        ])

    def print_sum_steel(self, member: str) -> None:
        if member == "大梁・片持梁":
            for material in (self.get_materials("大梁") | self.get_materials("片持梁")):
                print(f'\t{member}\t{material}\t{self.sum_steel("大梁", material) + self.sum_steel("片持梁", material):.2f}')
        else:
            for material in self.get_materials(member):
                print(f'\t{member}\t{material}\t{self.sum_steel(member, material):.2f}')

    def sum_brace(self, material: str) -> tuple[float, int]:
        length: np.ndarray = np.array([row["大梁"] for row in filter(lambda row: row["材料"].startswith(material), self.get("部位別集計表"))], dtype=np.float64)
        counts: np.ndarray = np.array([row["小梁"] for row in filter(lambda row: row["材料"].startswith(material), self.get("部位別集計表"))], dtype=np.int64)
        return (
            sum(length * counts) / sum(counts),
            sum(counts),
        )

    def print_sum_brace(self) -> None:
        for brace in self.get_braces():
            print(f"\t{brace}\t{self.sum_brace(brace)[0]:.2f}\t{self.sum_brace(brace)[1]}")


def sekisan(filename: str) -> None:
    sekisan: SS7_Sekisan = SS7_Sekisan(filename)
    for member in ["柱", "大梁・片持梁", "小梁", "鉛直ﾌﾞﾚｰｽ"]:
        sekisan.print_sum_steel(member)
        print("")

    sekisan.print_sum_brace()
