import re
import numpy as np


class Steel_Type(str):
    def standard_strength(self) -> int:
        return (
            int(self[2:5]) if self.startswith("S") else
            (
                400 if self.allowable_strength() == 235 else
                490 if self.allowable_strength() == 325 else
                520 if self.allowable_strength() == 355 else
                550 if self.allowable_strength() == 385 else
                0
            ) if self.startswith("B") else
            0
        )

    def allowable_strength(self) -> float:
        return (
            int(self[-3:]) if self.startswith("B") else
            (
                235 if self.standard_strength() == 400 else
                325 if self.standard_strength() == 490 else
                355 if self.standard_strength() == 520 else
                385 if self.standard_strength() == 550 else
                0
            ) if self.startswith("S") else
            0
        )

    def strength(self, key: str) -> float:
        return {
            "長期許容応力度": self.allowable_strength() / 1.5,
            "長期引張許容応力度": self.allowable_strength() / 1.5,
            "長期せん断許容応力度": self.allowable_strength() / 1.5 / np.sqrt(3),
            "短期許容応力度": self.allowable_strength(),
            "短期引張許容応力度": self.allowable_strength(),
            "短期せん断許容応力度": self.allowable_strength(),
            "引張強度": self.standard_strength(),
            "基準強度": self.standard_strength(),
        }[key]


class Steel_Section(str):
    # □-400*400*16*40
    # H-390×300×10×16
    # H-390*300*10*16*18
    steel_type: "Steel_Type"
    shape: str
    width: int
    depth: int
    web_thick: int
    flange_thick: int
    fillet_radius: int
    SCALLOP_SIZE: int = 35

    def __new__(cls, steel_shape: str = "", steel_type: str = "") -> "Steel_Section":
        steel_shape = steel_shape.replace("*", "x").replace("×", "x")
        self = super().__new__(cls, steel_shape)
        self.steel_type = Steel_Type(steel_type)
        matched: re.Match
        matched = re.match("S*H-(\\d+)x(\\d+)x(\\d+)x(\\d+)x*(\\d*)", steel_shape)
        if matched is not None:
            self.depth = int(matched.group(1))
            self.width = int(matched.group(2))
            self.web_thick = int(matched.group(3))
            self.flange_thick = int(matched.group(4))
            if matched.group(5) != "":
                self.fillet_radius = int(matched.group(5))
        matched = re.match("□-(\\d+)x(\\d+)x(\\d+)x*(\\d*)", steel_shape)
        if matched is not None:
            self.shape = "□"
            self.depth = int(matched.group(1))
            self.width = int(matched.group(2))
            self.web_thick = int(matched.group(3))
            self.flange_thick = int(matched.group(3))
            if matched.group(4) != "":
                self.fillet_radius = int(matched.group(4))
        matched = re.match("CT-(\\d+)x(\\d+)x(\\d+)x(\\d+)x*(\\d*)", steel_shape)
        if matched is not None:
            self.shape = "CT"
            self.depth = int(matched.group(1))
            self.width = int(matched.group(2))
            self.web_thick = int(matched.group(3))
            self.flange_thick = int(matched.group(4))
            if matched.group(5) != "":
                self.fillet_radius = int(matched.group(5))
        return self

    def web_area(self) -> float:
        if self.shape == "CT":
            return (self.depth - self.flange_thick) * self.web_thick
        elif self.shape == "□":
            return (self.depth - 2 * self.fillet_radius) * self.web_thick * 2
        else:
            return (self.depth - 2 * self.flange_thick) * self.web_thick

    def flange_area(self) -> float:
        if self.shape == "CT":
            return self.width * self.flange_thick
        elif self.shape == "□":
            return (self.width - 2 * self.fillet_radius) * self.flange_thick * 2
        else:
            return self.width * self.flange_thick * 2

    def fillet_area(self) -> float:
        if self.shape == "CT":
            return (4 - np.pi) * self.fillet_radius ** 2 / 2
        elif self.shape == "□":
            r1: float = self.fillet_radius
            r2: float = self.fillet_radius - self.web_thick
            return np.pi * (r1 ** 2 - r2 ** 2)
        else:
            return (4 - np.pi) * self.fillet_radius ** 2

    def calculated_area(self) -> float:
        return self.web_area() + self.flange_area() + self.fillet_area()

    def strength(self, key: str) -> float:
        return self.steel_type.strength(key)

    def plastic_web(self) -> float:
        return self.web_thick * (self.depth - 2 * self.flange_thick) ** 2 / 4

    def plastic_flange(self) -> float:
        return self.width * self.flange_thick * (self.depth - self.flange_thick)

    def plastic_design(self) -> float:
        return (self.plastic_flange() + self.plastic_web()) * self.steel_type.allowable_strength()

    def strength_flange(self) -> float:
        return self.plastic_flange() * self.strength("引張強度")

    def m(self, column: "Steel_Section") -> float:
        tcf: float = column.flange_thick
        dj: float = self.depth - 2 * self.flange_thick
        bj: float = column.width - 2 * column.flange_thick
        scy: float = column.steel_type.allowable_strength()
        swy: float = self.steel_type.allowable_strength()
        tbw: float = self.web_thick
        return min([
            1,
            4 * tcf / dj * np.sqrt(bj * scy / tbw / swy)
        ])

    def zwpe(self) -> float:
        return self.web_thick * (self.depth - 2 * self.flange_thick - 2 * self.SCALLOP_SIZE) ** 2 / 4

    def strength_web(self, column: "Steel_Section") -> float:
        return self.m(column) * self.zwpe() * self.steel_type.allowable_strength()
