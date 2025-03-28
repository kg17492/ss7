from .ss7_reader import SS7_Reader, Section
from .. import ss7_tool


def story_formatter(story: str) -> str:
    return story[:-1] if story.endswith("F") else story


def floor_formatter(floor: str) -> str:
    return floor[:-2] if floor.endswith("FL") else floor


class SS7_Output(SS7_Reader):
    """出力ファイルから各sectionを適当な辞書形式に読み替える
    """
    def get(self, key: str):
        if key not in self.gotten_dict:
            data: Section = super().get(key)

            def temp():
                if any([
                    key in data.name for key in [
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
                elif data.name in ["崩壊メカニズム"]:
                    return data.read_as_list_of_line()
                elif "SRC耐震壁保証設計(SRC規準)" in data.name:
                    def paragraph2dict(p: ss7_tool.String) -> dict[str, str]:
                        result: list[dict[str, str]] = Section(
                            data.name,
                            data.keys,
                            p,
                        ).read_as_list_of_dict()
                        result[0]["右軸"] = result[0].pop("軸")
                        result[0]["左軸"] = result[-1].pop("軸")
                        result[0]["twmm"] = result[-1].pop("twmm")
                        return result[0]
                    return [paragraph2dict(p) for p in data.stripsplit(",<RE>\n")]
                elif any([
                    key in data.name for key in [
                        "RC耐震壁保証設計(靭性指針式)",
                        "地震用重量",
                        "梁剛性表",
                    ]
                ]):
                    return data.read_first_line_as_list_of_dict()
                else:
                    return data.read_self()

            self.gotten_dict[key] = temp()
        return self.gotten_dict[key]

    def load_key(self, load: str) -> str:
        """loadで指定された載荷を適当なkeyに変換する

        Args:
            - load:
                - G+P   -> gpp
                - EX+   -> exp
                - EX-   -> exm
                - DSX+  -> dsxp
                - DSX-  -> dsxm
                - QUX+低減 -> quxp_reduced
        """
        return ss7_tool.String(load).multiple_replace(
            "+", "p",
            "-", "m",
            "低減", "_reduced",
        ).lower()

    def read(self, key: str) -> list[dict]:
        """keyで指定されたセクションをここで定義された形式で読み取る

        Args:
            - key:
                - 壁応力表（危険断面位置）
                - 壁応力表（一次）
                - 壁応力表（二次）
                - 柱応力表（危険断面位置）
                - 柱応力表（一次）
                - 柱応力表（二次）
                - SRC耐震壁保証設計（SRC規準）
                - RC耐震壁保証設計（靭性指針式）
                - RC耐震壁保証設計（靭性指針式の諸係数）
                - RC柱断面情報
                - 柱部材断面情報
                - 耐震壁部材断面情報
                - RC耐震壁断面算定表
                - SRC耐震壁断面算定表
        """
        if "壁応力表(危険断面位置)" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "frame": d["ﾌﾚｰﾑ"],
                    "l_axis": d["左軸"],
                    "r_axis": d["右軸"],

                    f"{load_key}_m_critical": float(d["MkNm"]),
                    f"{load_key}_q_critical": float(d["QkN"]),
                    f"{load_key}_n_critical": float(d["NkN"]),
                }
        elif "壁応力表(一次)" in key or "壁応力表(二次)" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "frame": d["ﾌﾚｰﾑ"],
                    "l_axis": d["左軸"],
                    "r_axis": d["右軸"],

                    f"{load_key}_m_top": float(d["壁頭MkNm"]),
                    f"{load_key}_q_top": float(d["壁頭QkN"]),
                    f"{load_key}_n_top": float(d["壁頭NkN"]),
                    f"{load_key}_m_bottom": float(d["壁脚MkNm"]),
                    f"{load_key}_q_bottom": float(d["壁脚QkN"]),
                    f"{load_key}_n_bottom": float(d["壁脚NkN"]),
                }
        elif "柱応力表(危険断面位置)" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "x_axis": d["X軸"],
                    "y_axis": d["Y軸"],

                    f"{load_key}_m_c_top_x": float(d["X方向柱頭MkNm"]),
                    f"{load_key}_q_c_top_x": float(d["X方向柱頭QkN"]),
                    f"{load_key}_m_c_top_y": float(d["Y方向柱頭MkNm"]),
                    f"{load_key}_q_c_top_y": float(d["Y方向柱頭QkN"]),
                    f"{load_key}_m_c_bottom_x": float(d["X方向柱脚MkNm"]),
                    f"{load_key}_q_c_bottom_x": float(d["X方向柱脚QkN"]),
                    f"{load_key}_m_c_bottom_y": float(d["Y方向柱脚MkNm"]),
                    f"{load_key}_q_c_bottom_y": float(d["Y方向柱脚QkN"]),
                    f"{load_key}_n_c_top": float(d["柱頭NkN"]),
                    f"{load_key}_n_c_bottom": float(d["柱脚NkN"]),
                }
        elif "柱応力表(一次)" in key or "柱応力表(二次)" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "x_axis": d["X軸"],
                    "y_axis": d["Y軸"],

                    f"{load_key}_m_top_x": float(d["X方向柱頭MkNm"]),
                    f"{load_key}_q_top_x": float(d["X方向柱頭QkN"]),
                    f"{load_key}_m_top_y": float(d["Y方向柱頭MkNm"]),
                    f"{load_key}_q_top_y": float(d["Y方向柱頭QkN"]),
                    f"{load_key}_m_bottom_x": float(d["X方向柱脚MkNm"]),
                    f"{load_key}_q_bottom_x": float(d["X方向柱脚QkN"]),
                    f"{load_key}_m_bottom_y": float(d["Y方向柱脚MkNm"]),
                    f"{load_key}_q_bottom_y": float(d["Y方向柱脚QkN"]),
                    f"{load_key}_m_center_x": float(d["X方向中央MkNm"]),
                    f"{load_key}_m_center_y": float(d["Y方向中央MkNm"]),
                    f"{load_key}_n_top": float(d["柱頭NkN"]),
                    f"{load_key}_n_bottom": float(d["柱脚NkN"]),
                }
        elif "柱初期応力表" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "x_axis": d["X軸"],
                    "y_axis": d["Y軸"],

                    f"{load_key}_m_i_top_x": float(d["X方向柱頭MkNm"]),
                    f"{load_key}_q_i_top_x": float(d["X方向柱頭QkN"]),
                    f"{load_key}_m_i_top_y": float(d["Y方向柱頭MkNm"]),
                    f"{load_key}_q_i_top_y": float(d["Y方向柱頭QkN"]),
                    f"{load_key}_m_i_bottom_x": float(d["X方向柱脚MkNm"]),
                    f"{load_key}_q_i_bottom_x": float(d["X方向柱脚QkN"]),
                    f"{load_key}_m_i_bottom_y": float(d["Y方向柱脚MkNm"]),
                    f"{load_key}_q_i_bottom_y": float(d["Y方向柱脚QkN"]),
                    f"{load_key}_m_i_center_x": float(d["X方向中央MkNm"]),
                    f"{load_key}_m_i_center_y": float(d["Y方向中央MkNm"]),
                    f"{load_key}_n_i_top": float(d["柱頭NkN"]),
                    f"{load_key}_n_i_bottom": float(d["柱脚NkN"]),
                }
        elif "節点初期変位" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "x_axis": d["X軸"],
                    "y_axis": d["Y軸"],

                    f"init_{load_key}_x": float(d["Xmm"]),
                    f"init_{load_key}_y": float(d["Ymm"]),
                    f"init_{load_key}_z": float(d["Zmm"]),
                    f"init_{load_key}_rx": float(d["θXrad"]),
                    f"init_{load_key}_ry": float(d["θYrad"]),
                    f"init_{load_key}_rz": float(d["θZrad"]),
                }
        elif "変位量(節点)(二次)" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "x_axis": d["X軸"],
                    "y_axis": d["Y軸"],

                    f"{load_key}_x": float(d["Xmm"]),
                    f"{load_key}_y": float(d["Ymm"]),
                    f"{load_key}_z": float(d["Zmm"]),
                    f"{load_key}_rx": float(d["θXrad"]),
                    f"{load_key}_ry": float(d["θYrad"]),
                    f"{load_key}_rz": float(d["θZrad"]),
                }
        elif "構造階高" in key:
            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "floor_height": float(d["階高mm"]) if d["階高mm"].isdecimal() else 0,
                    "structure_height": float(d["構造階高mm"]) if d["構造階高mm"].isdecimal() else 0,
                }
        elif "SRC耐震壁保証設計(SRC規準)" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "frame": d["ﾌﾚｰﾑ"],
                    "l_axis": d["左軸"],
                    "r_axis": d["右軸"],

                    f"test_{load_key}_effective_thickness": float(d["twmm"]),
                    f"test_{load_key}_reduction_ratio": float(d["開口γ"]),
                    f"test_{load_key}_axial_force": float(d["NkN"]),
                    f"test_{load_key}_shear_force": float(d["QMkN"]),
                    f"test_{load_key}_tensile_steel_ratio": float(d["pte%"]),
                    f"test_{load_key}_shear_span_ratio": float(d["M/QD"]),
                    f"test_{load_key}_minimum_reinforcement_ratio": float(d["pwh%"]),
                    f"test_{load_key}_src_ultimate_strength": float(d["QukN"]),
                }
        elif "RC耐震壁保証設計(靭性指針式の諸係数)" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "frame": d["ﾌﾚｰﾑ"],
                    "l_axis": d["左軸"],
                    "r_axis": d["右軸"],

                    f"test_{load_key}_hinge_rotation": float(d["Rurad"]),
                    f"test_{load_key}_effective_column_width": float(d["bemm"]),
                    f"test_{load_key}_delta_arch": float(d["Δlwamm"]),
                    f"test_{load_key}_delta_truss": float(d["Δlwbmm"]),
                    f"test_{load_key}_arch_effective_length": float(d["lwamm"]),
                    f"test_{load_key}_truss_effective_length": float(d["lwbmm"]),
                    f"test_{load_key}_tan_theta": float(d["tanθ"]),
                    f"test_{load_key}_concrete_effectiveness": float(d["ν"]),
                    f"test_{load_key}_beta": float(d["β"]),
                    f"test_{load_key}_arch_contribution": float(d["VakN"]),
                    f"test_{load_key}_truss_contribution": float(d["VtkN"]),
                    f"test_{load_key}_required_column_contribution": float(d["VackN"]),
                    f"test_{load_key}_allowable_column_contribution": float(d["VtckN"]),
                    f"test_{load_key}_compression_column": d["圧縮側柱"],
                    f"test_{load_key}_wall_thickness": float(d["twmm"]),
                    f"test_{load_key}_span_center": float(d["lwmm"]),
                    f"test_{load_key}_Dcx": float(d["Dcxmm"]),
                    f"test_{load_key}_Dcy": float(d["Dcymm"]),
                    f"test_{load_key}_concrete_compression_strength": float(d["柱σBN/mm2"]),
                }
        elif "RC耐震壁保証設計(靭性指針式)" in key:
            load_key: str = self.load_key(key.split(" ")[1])

            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "frame": d["ﾌﾚｰﾑ"],
                    "l_axis": d["左軸"],
                    "r_axis": d["右軸"],

                    f"test_{load_key}_nl_ne": float(d["NkN"]),
                    f"test_{load_key}_shear_force": float(d["QMkN"]),
                    f"test_{load_key}_jinsei_ultimate_strength": float(d["VukN"]),
                }
        elif "RC柱断面情報" == key:
            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "x_axis": d["X軸"],
                    "y_axis": d["Y軸"],
                    "name": d["符号"],

                    "dx": int(d["Dxmm"]),
                    "dy": int(d["Dymm"]),
                }
        elif "柱部材断面情報" == key:
            def temp(d: dict[str, str]) -> dict:
                template_dict: dict[str, str] = {
                    'ｺﾝｸﾘｰﾄDx×Dy': '0×0',
                    'ｺﾝｸﾘｰﾄ材料': 'Fc00',
                    '柱頭鉄骨形状X': '',
                    '柱頭鉄骨材料X(flange)': '',
                    '柱頭鉄骨材料X(web)': '',
                    '柱頭鉄骨形状Y': '',
                    '柱頭鉄骨材料Y(flange)': '',
                    '柱頭鉄骨材料Y(web)': '',
                    '柱頭鉄骨形状XY': '',
                    '柱頭鉄骨材料XY': '',

                    '柱頭主筋本数-径X': '0-D25',
                    '柱頭主筋本数-径Y': '0-D25',
                    '柱頭主筋材料X': 'SD000',
                    '柱頭主筋材料Y': 'SD000',
                    '柱頭1段目dtXmm': '0',
                    '柱頭1段目dtYmm': '0',
                    '柱頭帯筋本数-径@ピッチX': '0-D13@100',
                    '柱頭帯筋本数-径@ピッチY': '0-D13@100',
                    '柱頭帯筋材料X': 'SD000',
                    '柱頭帯筋材料Y': 'SD000',

                    '柱脚鉄骨形状X': '',
                    '柱脚鉄骨材料X(flange)': 'SN000B',
                    '柱脚鉄骨材料X(web)': 'SN000B',
                    '柱脚鉄骨形状Y': '',
                    '柱脚鉄骨材料Y(flange)': 'SN000B',
                    '柱脚鉄骨材料Y(web)': 'SN000B',
                    '柱脚鉄骨形状XY': '',
                    '柱脚鉄骨材料XY': '',

                    '柱脚主筋本数-径X': '0-D25',
                    '柱脚主筋本数-径Y': '0-D25',
                    '柱脚主筋材料X': 'SD000',
                    '柱脚主筋材料Y': 'SD000',
                    '柱脚1段目dtXmm': '0',
                    '柱脚1段目dtYmm': '0',
                    '柱脚帯筋本数-径@ピッチX': '0-D13@100',
                    '柱脚帯筋本数-径@ピッチY': '0-D13@100',
                    '柱脚帯筋材料X': 'SD000',
                    '柱脚帯筋材料Y': 'SD000',
                }
                for key in d:
                    if d[key] == "":
                        d[key] = template_dict[key]
                d = template_dict | d
                dx: str
                dy: str
                dx, dy = (
                    d["ｺﾝｸﾘｰﾄDx×Dy"].split("×") if "ｺﾝｸﾘｰﾄDx×Dy" in d else
                    (0, 0)
                )
                return {
                    "floor": story_formatter(d["階"]),
                    "x_axis": d["X軸"],
                    "y_axis": d["Y軸"],
                    "name": d["符号"],

                    "sx_top": (d["柱頭鉄骨形状X"], d["柱頭鉄骨材料X(flange)"]),
                    "sy_top": (d["柱頭鉄骨形状Y"], d["柱頭鉄骨材料Y(flange)"]),
                    "sxy_top": (d["柱頭鉄骨形状XY"], d["柱頭鉄骨材料XY"]),
                    "sx_bottom": (d["柱脚鉄骨形状X"], d["柱脚鉄骨材料X(flange)"]),
                    "sy_bottom": (d["柱脚鉄骨形状Y"], d["柱脚鉄骨材料Y(flange)"]),
                    "sxy_bottom": (d["柱脚鉄骨形状XY"], d["柱脚鉄骨材料XY"]),

                    "dx": int(dx),
                    "dy": int(dy),
                    "concrete": d["ｺﾝｸﾘｰﾄ材料"],
                    "x_top": (d["柱頭主筋本数-径X"], d["柱頭主筋材料X"]),
                    "y_top": (d["柱頭主筋本数-径Y"], d["柱頭主筋材料Y"]),
                    "x_top_dt": int(d["柱頭1段目dtXmm"]),
                    "y_top_dt": int(d["柱頭1段目dtYmm"]),
                    "x_bottom": (d["柱脚主筋本数-径X"], d["柱脚主筋材料X"]),
                    "y_bottom": (d["柱脚主筋本数-径Y"], d["柱脚主筋材料Y"]),
                    "x_bottom_dt": int(d["柱脚1段目dtXmm"]),
                    "y_bottom_dt": int(d["柱脚1段目dtYmm"]),
                    "x_hoop": (d["柱頭帯筋本数-径@ピッチX"], d["柱頭帯筋材料X"]),
                    "y_hoop": (d["柱頭帯筋本数-径@ピッチY"], d["柱頭帯筋材料Y"]),
                }
        elif "耐震壁部材断面情報" == key:
            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": story_formatter(d["階"]),
                    "frame": d["ﾌﾚｰﾑ"],
                    "l_axis": d["左軸"],
                    "r_axis": d["右軸"],

                    "name": d["符号"],
                    "wall_thickness": int(d["コンクリートt"]),
                    "concrete": d["コンクリート材料"],
                    "vertical": (d["壁筋径@ピッチ縦"], d["壁筋材料縦"]),
                    "horizontal": (d["壁筋径@ピッチ横"], d["壁筋材料横"] if "壁筋材料横" in d else d["横"]),
                    "dt": int(d["壁筋かぶり厚mm"]),
                }
        elif key in ["RC耐震壁断面算定表", "SRC耐震壁断面算定表"]:
            def table2dict(wall: ss7_tool.Table) -> dict:
                return {
                    "name": wall.get(0, 0).strip("[] "),
                    "floor": story_formatter(wall.get(1, 0).strip("[] ")),
                    "frame": wall.get(1, 2),
                    "l_axis": wall.get(1, 3),
                    "r_axis": wall.get(1, 5).strip("[] "),
                    "wall_length": wall.get_right_float("内法"),
                    "wall_height": wall.get_right_float("内法", 4),
                    "floor_height": wall.get_right_float("階高"),

                    "reduction_ratio": wall.get_right_float("r"),
                    "reduction_previous": [wall.get_right_float(key) for key in ["r1", "r2", "r3"]],
                    "l_qc": wall.get_right_float("QC", 1),
                    "r_qc": wall.get_right_float("QC", 2),
                    "qe": abs(wall.get_right_float("QE")),
                    "qw": wall.get_right_float("QW"),
                    "q1": wall.get_right_float("Q1"),
                    "q2": wall.get_right_float("Q2"),
                    "qdl": abs(wall.get_right_float("QDL")),
                    "qal": wall.get_right_float("QAL"),
                    "qds": abs(wall.get_right_float("QDS")),
                    "qas": wall.get_right_float("QAS"),
                }

            def temp(paragraph: list[list[str]]) -> dict:
                lines: list[str] = ["".join(row) for row in paragraph]
                idx: int = [("[" in line) for line in lines].index(True) if "[" in "".join(lines) else 0
                return table2dict(ss7_tool.Table(paragraph[idx:]))
        elif "梁部材断面情報" == key:
            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": floor_formatter(d["層"]),
                    "frame": d["ﾌﾚｰﾑ"],
                    "l_axis": d["左軸"],
                    "r_axis": d["右軸"],

                    "name": d["符号"],
                    "steel_shape_left": d["鉄骨形状左端"],
                    "steel_shape_center": d["鉄骨形状中央"],
                    "steel_shape_right": d["鉄骨形状右端"],
                    "steel_type_left": d["鉄骨材料左端"],
                    "steel_type_center": d["鉄骨材料中央"],
                    "steel_type_right": d["鉄骨材料右端"],
                }
        elif "梁剛性表" in key:
            def temp(d: dict[str, str]) -> dict:
                return {
                    "floor": floor_formatter(d["層"]),
                    "frame": d["ﾌﾚｰﾑ"],
                    "l_axis": d["左軸"],
                    "r_axis": d["右軸"],

                    "name": d["符号"],
                    "beam_length": float(d["部材長mm"]),
                }

        else:
            def temp(d: dict[str, str]) -> dict[str, str]:
                return d

        return [temp(d) for d in self.get(key)]
