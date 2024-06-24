import re
import numpy as np


class Concrete:
    fc: float = 0

    def __init__(self, fc) -> None:
        if type(fc) is int:
            self.fc = fc
        elif fc.isdecimal():
            self.fc = int(fc)
        elif fc.startswith("Fc"):
            self.fc = int(fc[2:])

    def shear_strength(self) -> float:
        return self.fc / 10

    def compression_strength(self) -> float:
        return self.fc


class Rebar_Type:
    rebar_type: str

    def __init__(self, rebar_type: str) -> None:
        self.rebar_type = rebar_type

    def strength(self) -> float:
        if self.rebar_type.startswith("SD"):
            return float(self.rebar_type[2:5])
        elif self.rebar_type.startswith("SBPD"):
            return float(self.rebar_type[4:8])
        else:
            return 0


def get_rebar_area_and_strength(name: str) -> tuple[float, float]:
    rebar: Rebar_Name = Rebar_Name(name)
    return (rebar.area, rebar.strength("基準強度"))


class Rebar_Name:
    name: str
    area: float
    rebar_type: str
    true_diameter: int

    def __init__(self, name: str, rebar_type: str = None) -> None:
        self.name = name
        data: dict[str, tuple] = {
            "key": ("area", "rebar_type", "true_diameter"),
            "": (0, "", 0),
            "D10": (71.33, "SD295", 11),
            "D10D13": (71.33 / 2 + 126.7 / 2, "SD295", 14),
            "D13": (126.7, "SD295", 14),
            "D16": (198.6, "SD295", 18),
            "D19": (286.5, "SD345", 21),
            "D22": (387.1, "SD345", 25),
            "D25": (506.7, "SD345", 28),
            "D29": (642.4, "SD390", 33),
            "D32": (794.2, "SD390", 36),
            "D35": (956.6, "SD390", 40),
            "D38": (1140, "SD390", 43),
            "U7.1": (40, "SBPD1275/1420", 7.1),
            "U9.0": (64, "SBPD1275/1420", 9.0),
            "U10.7": (90, "SBPD1275/1420", 10.7),
            "U11.8": (110.1, "SBPD1275/1420", 11.8),
            "U12.6": (125, "SBPD1275/1420", 12.6),
        }
        for i, key in enumerate(data["key"]):
            setattr(self, key, data[name][i])
        if rebar_type is not None:
            self.rebar_type = rebar_type

    def strength(self, key: str = "") -> float:
        f: float = Rebar_Type(self.rebar_type).strength()
        if "長期" in key:
            maximum: float = 195 if "せん断補強" in key or self.true_diameter > 28 else 215
            return min(maximum, f / 1.5)
        else:
            maximum: float = 390 if "せん断補強" in key else np.inf
            return min(maximum, f)

    def call_diameter(self) -> float:
        return float(self.name[1:]) if self.name != "" else 0


class Mother_Reinforcement:
    rebar_num: int = 0      # = 2
    rebar_type: str = ""    # = "SD295A"
    rebar_name: str = ""    # = "D13"
    key: str

    def set_rebar_type(self, rebar_type: str) -> None:
        self.rebar_type = rebar_type

    def area(self) -> float:
        return self.rebar_num * Rebar_Name(self.rebar_name).area

    def strength(self, key: str = "") -> float:
        f: float = Rebar_Type(self.rebar_type).strength()
        if "長期" in key:
            maximum: float = 195 if "せん断補強" in key or Rebar_Name(self.rebar_name).true_diameter > 28 else 215
            return min(maximum, f / 1.5)
        else:
            maximum: float = 390 if "せん断補強" in key else np.inf
            return min(maximum, f)

    def area_by_strength(self, key: str = "") -> float:
        return self.area() * self.strength(key)


class Hoop_Reinforcement(Mother_Reinforcement):
    # (4-D13@200, SD345)
    # (D13@200ダブル) == (D13@200) == (D13@200, SD295)
    interval: int       # = 100

    def __init__(self, hoop: str, rebar_type: str = None) -> None:
        self.key = hoop
        matched: re.Match = re.match("(\\d*)-*([D\\d]+)@(\\d+)(.*)", hoop)
        if matched is not None:
            rebar_num_str: str = matched.group(1)
            self.rebar_num = (
                int(rebar_num_str) if rebar_num_str != "" else
                1 if matched.group(4) == "シングル" else
                2
            )
            self.rebar_name = matched.group(2)
            self.interval = int(matched.group(3))
            self.rebar_type = (
                Rebar_Name(self.rebar_name).rebar_type if rebar_type is None else
                rebar_type
            )
            return
        matched = re.match("(\\d*)-(U\\d+\\.\\d+)@(\\d+)(.*)", hoop)
        if matched is not None:
            rebar_num_str: str = matched.group(1)
            self.rebar_num = (
                int(rebar_num_str) if rebar_num_str != "" else
                1 if matched.group(4) == "シングル" else
                2
            )
            self.rebar_name = matched.group(2)
            self.interval = int(matched.group(3))
            self.rebar_type = (
                Rebar_Name(self.rebar_name).rebar_type if rebar_type is None else
                rebar_type
            )

    def ratio(self, thickness: float) -> float:
        return self.area() / self.interval / thickness

    def ratio_by_strength(self, thickness: float, key: str = "") -> float:
        return self.area_by_strength(key) / self.interval / thickness


class Main_Reinforcement(Mother_Reinforcement):
    rebar_num_2nd: int
    # (4-D13, SD345)
    # (4-D13) == (4-D13, SD295)

    def __init__(self, main: str, rebar_type: str = None) -> None:
        matched: re.Match = re.match("(\\d+)/*(\\d*)-(D\\d+)", main)
        self.key = main
        if matched is not None:
            self.rebar_num = int(matched.group(1))
            if matched.group(2) != "":
                self.rebar_num_2nd = int(matched.group(1))
            self.rebar_name = matched.group(3)
            self.rebar_type = (
                Rebar_Name(self.rebar_name).rebar_type if rebar_type is None else
                rebar_type
            )

    def area_for_whole(self) -> float:
        return (self.rebar_num - 1) * Rebar_Name(self.rebar_name).area
