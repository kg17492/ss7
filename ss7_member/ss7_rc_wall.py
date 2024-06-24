import numpy as np
import matplotlib.pyplot as plt
from .ss7_member_between_columns import SS7_Member_Between_Columns
from .ss7_opening import SS7_Opening
from .ss7_axis_and_floor import SS7_Axis_and_Floor
from .ss7_rc_column import SS7_RC_Column
from .. import ss7_material
from .. import ss7_tool


class SS7_RC_Wall(SS7_Member_Between_Columns):
    """RC, SRC壁
    """
    floor: str
    frame: str
    l_axis: str
    r_axis: str
    name: str

    gpp_m_top: float
    gpp_m_bottom: float
    gpp_n_bottom: float
    gpp_q_bottom: float

    multi_openings: str = None

    wall_thickness: int
    concrete: ss7_material.Concrete
    vertical: ss7_material.Hoop_Reinforcement
    horizontal: ss7_material.Hoop_Reinforcement
    dt: int

    wall_length: float
    wall_height: float
    floor_height: float
    reduction_ratio: float
    reduction_previous: list[float]

    opening_class: SS7_Opening = SS7_Opening
    openings: list[SS7_Opening]
    old_openings: list[SS7_Opening] = []

    def __init__(self, dictionary: dict, axis_and_floor: SS7_Axis_and_Floor) -> None:
        super().__init__(dictionary, axis_and_floor)
        self.concrete = ss7_material.Concrete(self.concrete)
        self.vertical = ss7_material.Hoop_Reinforcement(*self.vertical)
        self.horizontal = ss7_material.Hoop_Reinforcement(*self.horizontal)
        name: str = dictionary["name"]
        self.name = ("E" if self.reduction_ratio > 0.6 and name[0] == "W" else "") + name

    def get_openings(self, openings: list[SS7_Opening]) -> None:
        result: list[SS7_Opening] = sorted([o.relative_to_absolute(
            self.span_inside(),
            self.span_center(),
            self.height_inside(),
            self.height_center(),
        ) for o in filter(lambda o: self.includes(o), openings)], key=lambda o: o.left)
        self.openings = result

    def get_nodes(self) -> None:
        pass

    def span_inside(self) -> float:
        return self.wall_length

    def span_center(self) -> float:
        return self.wall_length + self.l_column.depth(self.direction()) / 2 + self.r_column.depth(self.direction()) / 2

    def height_inside(self) -> float:
        return self.wall_height

    def height_center(self) -> float:
        return self.floor_height

    def area(self) -> float:
        return self.wall_length * self.wall_thickness

    def jinsei_ultimate_strength(self) -> float:
        expect_delta: bool = self.can_expect_column_contribution()
        return self.reduction_ratio * (self.truss_contribution(expect_delta) + self.arch_contribution(expect_delta))

    def truss_contribution(self, expect_delta: bool) -> float:
        return np.prod([
            self.wall_thickness,                        # mm
            self.truss_effective_length(expect_delta),  # mm
            self.horizontal_ratio_by_strength(),        # N/mm^2
            self.cot_phi(),
        ]) / 1e3

    def horizontal_ratio_by_strength(self) -> float:
        return np.clip(
            self.horizontal.ratio_by_strength(self.wall_thickness, "終局強度"),
            -float("inf"),
            self.effective_concrete_strength(),
        )

    def effective_concrete_strength(self) -> float:
        return self.concrete_effectiveness() * self.concrete.compression_strength() / 2

    def concrete_effectiveness(self) -> float:
        ru: float = self.hinge_rotation()
        nu_0: float = 0.7 - self.concrete.compression_strength() / 200
        return (
            nu_0 if ru < 0.005 else
            (1.2 - 40 * ru) * nu_0 if ru < 0.02 else
            0.4 * nu_0
        )

    def hinge_rotation(self) -> float:
        if hasattr(self, f"test_{self.load_key()}_hinge_rotation"):
            return getattr(self, f"test_{self.load_key()}_hinge_rotation")
        else:
            return 0.002

    def arch_contribution(self, expect_delta: bool) -> float:
        return np.prod([
            self.tan_theta(expect_delta),
            1 - self.beta(),
            self.wall_thickness,
            self.arch_effective_length(expect_delta),
            self.effective_concrete_strength(),
        ]) / 1e3

    def arch_effective_length(self, expect_delta: bool) -> float:
        return sum([
            self.wall_length,
            self.compression_column().depth(self.direction()),
            self.delta_arch(expect_delta),
        ])

    def truss_effective_length(self, expect_delta: bool) -> float:
        return sum([
            self.wall_length,
            self.compression_column().depth(self.direction()),
            self.delta_truss(expect_delta),
        ])

    def delta_arch(self, expect_delta: bool) -> float:
        if not expect_delta:
            return 0
        ace: float = self.effective_compression_column_area()
        dc: float = self.compression_column().depth(self.direction())
        tw: float = self.wall_thickness
        return (
            ace / tw if ace < tw * dc else
            (dc + np.sqrt(ace * dc / tw)) / 2
        )

    def delta_truss(self, expect_delta: bool) -> float:
        if not expect_delta:
            return 0
        ace: float = self.effective_compression_column_area()
        dc: float = self.compression_column().depth(self.direction())
        tw: float = self.wall_thickness
        return (
            ace / tw if ace < tw * dc else
            dc
        )

    def effective_compression_column_area(self) -> float:
        return np.clip(
            self.compression_column().area() - self.ncc() / self.compression_column().concrete.compression_strength() * 1e3,
            0,
            3 * self.wall_thickness * self.compression_column().depth(self.direction()),
        )

    def m(self, key: str) -> float:
        return getattr(self, f"{self.load_key()}_m_{key}")

    def q(self, key: str) -> float:
        return getattr(self, f"{self.load_key()}_q_{key}")

    def n(self, key: str) -> float:
        return getattr(self, f"{self.load_key()}_n_{key}")

    def get_test(self, key: str) -> float:
        return getattr(self, f"test_{self.load_key()}_{key}")

    def ln(self, key: str) -> float:
        return getattr(self.l_column, f"{self.load_key()}_n_{key}") / (2 if self.has_left_wall else 1)

    def rn(self, key: str) -> float:
        return getattr(self.r_column, f"{self.load_key()}_n_{key}") / (2 if self.has_right_wall else 1)

    def bottom_face_from_axis(self) -> float:
        m_bottom: float = self.m("bottom")
        m_critical: float = self.m("critical")
        q_bottom: float = self.q("bottom")
        return (m_bottom - m_critical) / q_bottom

    def structural_height(self) -> float:
        m_top: float = self.m("top")
        m_bottom: float = self.m("bottom")
        q_bottom: float = self.q("bottom")
        return (m_top + m_bottom) / q_bottom

    def mwt(self) -> float:
        lni_top: float = self.ln("i_top")
        lni_bottom: float = self.ln("i_bottom")
        rni_top: float = self.rn("i_top")
        rni_bottom: float = self.rn("i_bottom")
        mi_top: float = (rni_top - lni_top) * self.span_center() / 2000
        mi_bottom: float = (rni_bottom - lni_bottom) * self.span_center() / 2000
        qi: float = (mi_top + mi_bottom) / self.structural_height()
        mc_bottom: float = mi_bottom - qi * self.bottom_face_from_axis()
        lnc_bottom: float = self.ln("c_bottom")
        rnc_bottom: float = self.rn("c_bottom")
        ln_bottom: float = lnc_bottom - lni_bottom
        rn_bottom: float = rnc_bottom - rni_bottom
        m_bottom: float = (rn_bottom - ln_bottom) * self.span_center() / 2000
        return - sum([
            self.m("critical"),
            mc_bottom,
            m_bottom,
        ])
        return - sum([
            self.m("critical"),
            - self.ln("c_bottom") * self.span_center() / 2000,
            + self.rn("c_bottom") * self.span_center() / 2000,
        ])

    def tensile_column(self) -> SS7_RC_Column:
        return self.r_column if self.mwt() > 0 else self.l_column

    def compression_column(self) -> SS7_RC_Column:
        return self.l_column if self.mwt() > 0 else self.r_column

    def nl_ne(self) -> float:
        return sum([
            self.ln("c_bottom"),
            self.rn("c_bottom"),
            self.n("critical"),
        ])

    def ncc(self) -> float:
        return self.nl_ne() + self.mwt() / self.span_center() * 1000
        return self.nl_ne() + abs(self.mwt()) / self.span_center() * 1000

    def cot_phi(self) -> float:
        return 1

    def hw(self) -> float:
        if hasattr(self, f"test_{self.load_key()}_tan_theta"):
            tan: float = self.get_test("tan_theta")
            dlwa: float = self.get_test("delta_arch")
            return self.arch_effective_length(dlwa > 0) * (1 - tan**2) / 2 / tan
        else:
            return self.floor_height

    def tan_theta(self, expect_delta: bool) -> float:
        hwlwa: float = self.hw() / self.arch_effective_length(expect_delta)
        return np.sqrt(hwlwa**2 + 1) - hwlwa

    def beta(self) -> float:
        return np.prod([
            (1 + self.cot_phi()**2),
            self.horizontal.ratio_by_strength(self.wall_thickness, "終局強度"),
            1 / self.effective_concrete_strength() / 2,
        ])

    def can_expect_column_contribution(self) -> bool:
        return self.required_column_contribution() <= self.allowable_column_contribution()

    @ss7_tool.clip_decorator(min=0)
    def effective_column_width(self) -> float:
        return self.effective_compression_column_area() / self.compression_column().depth(self.direction()) - self.beta() * self.wall_thickness

    @ss7_tool.clip_decorator(min=0)
    def required_column_contribution(self) -> float:
        return np.prod([
            2,
            self.arch_contribution(True),
            self.delta_arch(True) - self.compression_column().depth(self.direction()) / 2,
            1 / self.arch_effective_length(True),
            1 / (1 + self.tan_theta(True)**2),
            2,
        ])

    def allowable_column_contribution(self) -> float:
        return np.prod([
            self.effective_column_width(),
            self.compression_column().between_main_reinforcement(self.direction()),
            self.compression_column().hoop_ratio_by_strength(self.direction(), key="規格降伏点"),
        ]) / 1000

    def test(self, key: str, digit: int) -> None:
        name_dict: dict[str, str] = {
            "N": "nl_ne",
            "Ru": "hinge_rotation",
            "be": "effective_column_width",
            "Δlwa": "delta_arch",
            "Δlwb": "delta_truss",
            "lwa": "arch_effective_length",
            "lwb": "truss_effective_length",
            "tanθ": "tan_theta",
            "ν": "concrete_effectiveness",
            "β": "beta",
            "Va": "arch_contribution",
            "Vt": "truss_contribution",
            "Vac": "required_column_contribution",
            "Vtc": "allowable_column_contribution",
            "Vu": "jinsei_ultimate_strength",
            "圧縮側柱": "compression_column",
        }
        name: str = name_dict[key]
        for towards in ["+", "-"]:
            self.towards = towards
            if key == "圧縮側柱":
                testee: str = self.get_test("compression_column")[0]
                tested: str = "左" if self.compression_column() is self.l_column else "右"
                if tested != testee:
                    print(f"{self.key()}\t{key}\t{self.load_key()}\t{tested}\t{testee}")
            else:
                args: list[bool] = [] if key in ["Ru", "be", "ν", "β", "Vac", "Vtc", "N", "Vu"] else [self.can_expect_column_contribution()]    # [getattr(self, f"test_delta_arch_{self.load_key()}") > 0]
                self.compare(
                    f"{key}\t{self.load_key()}",
                    getattr(self, name)(*args),
                    self.get_test(name),
                    digit
                )

    def update_openings(self, *openings: list[list[int]]) -> None:
        self.get_openings([SS7_Opening(
            {
                "floor": self.floor,
                "frame": self.frame,
                "l_axis": self.l_axis,
                "r_axis": self.r_axis,
                "dimension": str(dimension),
                "l1": l1,
                "l2": l2,
                "h1": h1,
                "h2": h2,
                "owner": "",
            },
            self.ss7_axis_and_floor,
        ) for l1, h1, l2, h2, dimension in openings])

    def check_opening_reinforcment(
        self,
        idx: int,
        rv: str,
        rh: str,
        rd: str,
        nv: int = None,
        nh: int = None,
        nrv: int = None,
        nrh: int = None,
    ) -> None:
        if nv is None:
            nv = len(self.openings)
        if nh is None:
            nh = len(self.openings)
        if nrv is None:
            nrv = np.floor(500 / self.vertical.interval)
        if nrh is None:
            nrh = np.floor(500 / self.horizontal.interval)
        h: int = self.height_center()
        l: int = sum([
            self.wall_length,
            self.l_column.depth(self.direction()),
            self.r_column.depth(self.direction()),
        ])
        t: int = self.wall_thickness
        q: int = self.qds * (4.1 if self.direction() == "x" else 4.15)
        lop: float
        hop: float
        lop, hop = self.projected_opening()
        psvft: float = self.vertical.ratio_by_strength(self.wall_thickness)
        pshft: float = self.horizontal.ratio_by_strength(self.wall_thickness)
        avoft: float = ss7_material.Main_Reinforcement(rv).area_by_strength()
        ahoft: float = ss7_material.Main_Reinforcement(rh).area_by_strength()
        avft: float = avoft + self.vertical.area_by_strength() * nrv
        ahft: float = ahoft + self.horizontal.area_by_strength() * nrh
        adft: float = ss7_material.Main_Reinforcement(rd).area_by_strength()
        root: float = 2.0**0.5
        td_allowable: float = (adft + (avft + ahft) / root) / 1e3
        md_allowable: float = sum([
            (l - lop) * (adft / root + avoft),
            t * (l - lop) ** 2 / 4 / (nh + 1) * psvft,
        ]) / 1e6
        mb_allowable: float = sum([
            (h - hop) * (adft / root + ahoft),
            t * (h - hop) ** 2 / 4 / nv * pshft,
        ]) / 1e6
        ho: float = self.openings[idx].height
        lo: float = self.openings[idx].width
        td: float = (ho + lo) / 2 / root / l * q
        md: float = ho / 2 * q / 1e3
        mb: float = lo / 2 * h / l * q / 1e3
        print(f"## {self.key()} {idx} {lo:.0f}×{ho:.0f}")
        # print(f"v {rv:>6} {md < md_allowable} {f'{md:.0f}':>5} < {f'{md_allowable:.0f}':>5} {md / md_allowable:.2f}")
        # print(f"h {rh:>6} {mb < mb_allowable} {f'{mb:.0f}':>5} < {f'{mb_allowable:.0f}':>5} {mb / mb_allowable:.2f}")
        # print(f"d {rd:>6} {td < td_allowable} {f'{td:.0f}':>5} < {f'{td_allowable:.0f}':>5} {td / td_allowable:.2f}")

        lop_str: str = "$l_{0p}$"
        hop_str: str = "$h_{0p}$"
        psv_str: str = "$p_{sv}$"
        psh_str: str = "$p_{sh}$"
        print("")
        print("|||")
        print("|:--:|:--:|")
        print(f"|$l$|{l:.0f}mm|")
        print(f"|$h$|{h:.0f}mm|")
        print(f"|{lop_str}|{lop:.0f}mm|")
        print(f"|{hop_str}|{hop:.0f}mm|")
        print(f"|$t$|{t:.0f}mm|")
        print(f"|$Q$|{q:.0f}kN|")

        def main_ft(key: str) -> str:
            return f"{ss7_material.Main_Reinforcement(key).strength():.0f}"

        def hoop_ft(key: str) -> str:
            return f"{ss7_material.Hoop_Reinforcement(key).strength():.0f}"

        def hoop_ratio(key: str) -> str:
            return f"{ss7_material.Hoop_Reinforcement(key).ratio(t) * 100:.2f}"

        nmm: str = "$\\mathrm{N/mm^2}$"
        md_str: str = "$M_d$"
        mb_str: str = "$M_b$"
        td_str: str = "$t_d$"

        print("")
        print("|||縦||横||斜||")
        print("|:--|--:|:--:|--:|:--:|:--:|:--:|:--|")
        print(f"|開口寸法||{ho:.0f} mm||{lo:.0f} mm|")
        print(f"|配筋||{rv}||{rh}||{rd}|")
        print(f"|配筋強度||{main_ft(rv)}||{main_ft(rh)}||{main_ft(rd)}|{nmm}|")
        print(f"|壁筋||{self.vertical.key}||{self.horizontal.key}||")
        print(f"|壁筋強度||{hoop_ft(self.vertical.key)}||{hoop_ft(self.horizontal.key)}|||{nmm}|")
        print(f"|壁筋比|{psv_str}|{hoop_ratio(self.vertical.key)}|{psh_str}|{hoop_ratio(self.horizontal.key)}|||%|")
        print(f"|考慮する壁筋本数||{nrv}||{nrh}|")
        print(f"|開口数|$n_h$|{nh}|$n_v$|{nv}||")
        print(f"|許容応力||{md_allowable:.0f} kNm||{mb_allowable:.0f} kNm||{td_allowable:.0f} kN|")
        print(f"|設計応力|{md_str}|{md:.0f} kNm|{mb_str}|{mb:.0f} kNm|{td_str}|{td:.0f} kN|")
        print(f"|検定比||{md / md_allowable:.2f}||{mb / mb_allowable:.2f}||{td / td_allowable:.2f}")
        print(f'|判定||{"OK" if md < md_allowable else "NG"}||{"OK" if mb < mb_allowable else "NG"}||{"OK" if td < td_allowable else "NG"}|')
        print("")

    def projected_opening(self) -> tuple[float, float]:
        def vectorize(array: np.ndarray) -> np.ndarray:
            return np.array([array.tolist()]).T

        lrbt: np.ndarray = np.array([[o.left, o.right, o.bottom, o.top] for o in filter(lambda o: not o.ignore, self.openings)])
        l: np.ndarray = vectorize(lrbt[:, 0])
        r: np.ndarray = vectorize(lrbt[:, 1])
        b: np.ndarray = vectorize(lrbt[:, 2])
        t: np.ndarray = vectorize(lrbt[:, 3])
        w: float = self.span_center()
        h: float = self.height_center()
        num: int = 100000
        x: np.ndarray = np.linspace(0, w, num)
        y: np.ndarray = np.linspace(0, h, num)
        return (
            np.sum(np.any((l <= x) * (x < r), axis=0)) / num * w,
            np.sum(np.any((b <= y) * (y < t), axis=0)) / num * h
        )

    def plot_wall(self) -> None:
        ox: float = self.ss7_axis_and_floor.get_axis_location(self.l_axis)
        oy: float = self.ss7_axis_and_floor.get_floor_location(self.floor)

        def plot_lrbt(lrbt: list[float], color: str = "tab:blue", linestyle="solid") -> None:
            l: float
            r: float
            b: float
            t: float
            l, r, b, t = lrbt
            lw: float = 0.8 if linestyle == "dotted" else 1.5
            x: np.ndarray = np.array([l, r, r, l, l])
            y: np.ndarray = np.array([b, b, t, t, b])
            plt.plot(ox + x, oy + y, color=color, lw=lw, linestyle=linestyle)

        w: float = self.span_inside()
        h: float = self.height_inside()
        x: float = (self.span_center() - w) / 2
        plot_lrbt([0, self.span_center(), 0, self.height_center()], "tab:blue", "dotted")
        plot_lrbt([x, w + x, 0, h], "tab:blue")
        for o in self.openings:
            owners: list[str] = ["建築", "設備", "電気", "プラント"]
            color: str = ss7_material.colors(owners.index(o.owner) + 1) if o.owner in owners else "black"
            plot_lrbt([o.left, o.right, o.bottom, o.top], color, "dotted" if o.ignore else "solid")

    def show_wall(self) -> None:
        fig: plt.Figure
        ax: plt.Axes
        fig, ax = plt.subplots()
        self.plot_wall()
        self.ss7_axis_and_floor.axis_in_elevation(self.frame)
        ax.set_aspect("equal")
        ax.set_title(self.key())
        fig.show()
