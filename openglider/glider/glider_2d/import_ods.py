from __future__ import division
from openglider.glider.rib_elements import RibHole

try:
    import ezodf2 as ezodf
except ImportError:
    import ezodf

import numpy
import scipy.interpolate

from openglider.airfoil import Profile2D
from openglider.glider.ballooning import BallooningBezier
from openglider.utils.bezier import BezierCurve, SymmetricBezier

from .lines import UpperNode2D, LowerNode2D, BatchNode2D, Line2D, LineSet2D


def import_ods_2d(cls, filename, numpoints=4):
    ods = ezodf.opendoc(filename)
    sheets = ods.sheets

    profiles = [Profile2D(profile) for profile in transpose_columns(sheets[3])]

    balloonings_temp = transpose_columns(sheets[4])
    balloonings = []
    for baloon in balloonings_temp:
        upper = [[0, 0]] + baloon[:7] + [[1, 0]]
        lower = [[0, 0]] + [[i[0], -1 * i[1]] for i in baloon[8:15]] + [[1, 0]]
        balloonings.append(BallooningBezier(upper, lower))

    data = {}
    datasheet = sheets[-1]
    assert isinstance(datasheet, ezodf.Sheet)
    for row in datasheet.rows():
        if len(row) > 1:
            data[row[0].value] = row[1].value

    # All Lists
    front = []
    back = []
    cell_distribution = []
    aoa = []
    arc = []
    profile_merge = []
    ballooning_merge = []

    y = z = span_last = alpha = 0.
    main_sheet = sheets[0]
    assert isinstance(main_sheet, ezodf.Sheet)
    for i in range(1, main_sheet.nrows()+1):
        line = [main_sheet.get_cell([i, j]).value for j in range(main_sheet.ncols())]
        if not line[0]:
            break  # skip empty line
        # Index, Choord, Span(x_2d), Front(y_2d=x_3d), d_alpha(next), aoa,
        chord = line[1]
        span = line[2]
        x = line[3]
        y += numpy.cos(alpha) * (span - span_last)
        z -= numpy.sin(alpha) * (span - span_last)

        alpha += line[4] * numpy.pi / 180  # angle after the rib

        aoa.append([span, line[5] * numpy.pi / 180])
        arc.append([y, z])
        front.append([span, -x])
        back.append([span, -x-chord])
        cell_distribution.append([span, i-1])

        profile_merge.append([span, line[8]])
        ballooning_merge.append([span, line[9]])

        # zrot = line[7] * numpy.pi / 180

        span_last = span

    # Attachment points: rib_no, id, pos, force
    attachment_points = [UpperNode2D(args[0], args[2], args[3], args[1]) for args in read_elements(sheets[2], "AHP", len_data=3)]
    attachment_points.sort(key=lambda element: element.nr)
    attachment_points_lower = get_lower_aufhaengepunkte(data)

    # RIB HOLES
    #RibHole(rib, pos, size)
    rib_holes = [{"rib": res[0], "pos": res[1], "size": res[2]} for res in read_elements(sheets[2], "QUERLOCH", len_data=2)]

    # CUTS
    def get_cuts(name, target_name):
        return [{"rib": res[0], "left": res[1], "right": res[2], "type": "entry"}
                for res in read_elements(sheets[1], "EKV", len_data=2)]
    cuts = get_cuts("EKV", "entry") + get_cuts("EKH", "entry")
    cuts += get_cuts("DESIGNM", "cut") + get_cuts("DESIGNO", "cut")


    has_center_cell = not front[0][0] == 0
    cell_no = (len(front)-1)*2 + has_center_cell

    def symmetric_fit(data):
        not_from_center = data[0][0] == 0
        mirrored = [[-p[0], p[1]] for p in data[not_from_center:]][::-1] + data
        return SymmetricBezier.fit(mirrored, numpoints=numpoints)

    start = (2 - has_center_cell) / cell_no

    const_arr = [0.] + numpy.linspace(start, 1, len(front) - (not has_center_cell)).tolist()
    rib_pos = [0.] + [p[0] for p in front[not has_center_cell:]]
    rib_pos_int = scipy.interpolate.interp1d(rib_pos, [rib_pos, const_arr])
    rib_distribution = [rib_pos_int(i) for i in numpy.linspace(0, rib_pos[-1], 30)]

    rib_distribution = BezierCurve.fit(rib_distribution, numpoints=numpoints+3)

    return cls(front=symmetric_fit(front),
               back=symmetric_fit(back),
               cell_dist=rib_distribution,
               cell_num=cell_no,
               arc=symmetric_fit(arc),
               aoa=symmetric_fit(aoa),
               #rib_elements={"cuts": cuts},
               profiles=profiles,
               profile_merge_curve=symmetric_fit(profile_merge),
               balloonings=balloonings,
               ballooning_merge_curve=symmetric_fit(ballooning_merge),
               lineset=tolist_lines(sheets[6], attachment_points_lower, attachment_points),
               speed=data.get("GESCHWINDIGKEIT", 10),
               glide=data.get("GLEITZAHL", 10))


def get_lower_aufhaengepunkte(data):
    aufhaengepunkte = {}
    xyz = {"X": 0, "Y": 1, "Z": 2}
    for key in data:
        if key is not None and "AHP" in key:
            pos = int(key[4])
            aufhaengepunkte.setdefault(pos, [0, 0, 0])
            aufhaengepunkte[pos][xyz[key[3].upper()]] = data[key]
    return {nr: LowerNode2D([0, 0], pos, nr)
            for nr, pos in aufhaengepunkte.items()}


def transpose_columns(sheet=ezodf.Table(), columnswidth=2):
    num = sheet.ncols()
    #if num % columnswidth > 0:
    #    raise ValueError("irregular columnswidth")
    result = []
    for col in range(int(num / columnswidth)):
        columns = range(col * columnswidth, (col + 1) * columnswidth)
        element = []
        i = 0
        while i < sheet.nrows():
            row = [sheet.get_cell([i, j]).value for j in columns]
            if sum([j is None for j in row]) == len(row):  # Break at empty line
                break
            i += 1
            element.append(row)
        result.append(element)
    return result


def tolist_lines(sheet, attachment_points_lower, attachment_points_upper):
    num_rows = sheet.nrows()
    num_cols = sheet.ncols()
    linelist = []
    current_nodes = [None for i in range(num_cols)]
    i = j = level = 0
    count = 0

    while i < num_rows:
        val = sheet.get_cell([i, j]).value
        if j == 0:  # first (line-)floor
            if val is not None:
                current_nodes = [attachment_points_lower[int(sheet.get_cell([i, j]).value)]] + \
                                [None for __ in range(num_cols)]
            j += 1
        elif j+2 < num_cols:
            if val is None:  # ?
                j += 2
            else:
                lower = current_nodes[j//2]

                # gallery
                if j + 4 >= num_cols or sheet.get_cell([i, j+2]).value is None:

                    upper = attachment_points_upper[int(val-1)]
                    line_length = None
                    i += 1
                    j = 0
                # other line
                else:
                    upper = BatchNode2D([0, 0])
                    current_nodes[j//2+1] = upper
                    line_length = sheet.get_cell([i, j]).value
                    j += 2

                linelist.append(
                    Line2D(lower, upper, target_length=line_length)) # line_type=sheet.get_cell
                count += 1

        elif j+2 >= num_cols:
            j = 0
            i += 1
    return LineSet2D(linelist)


def read_elements(sheet, keyword, len_data=2):
    """
    Return rib/cell_no for the element + data
    """

    elements = []
    j = 0
    while j < sheet.ncols():
        if sheet.get_cell([0, j]).value == keyword:
            for i in range(1, sheet.nrows()):
                line = [sheet.get_cell([i, j+k]).value for k in range(len_data)]
                if line[0] is not None:
                    elements.append([i-1] + line)
            j += len_data
        else:
            j += 1
    return elements
