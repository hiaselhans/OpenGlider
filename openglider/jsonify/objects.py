import openglider.glider
import openglider.airfoil
import openglider.lines
import openglider.utils.bezier
import openglider.glider.ballooning
import openglider.glider.rib_elements
import openglider.glider.glider_2d

__ALL__ = ['objects']

objects = {"Glider": openglider.glider.Glider,
           "Rib": openglider.glider.Rib,
           "Cell": openglider.glider.Cell,
           "BallooningBezier": openglider.glider.ballooning.BallooningBezier,
           "Profile2D": openglider.airfoil.Profile2D,
           "LineSet": openglider.lines.LineSet,
           "Line": openglider.lines.Line,
           "Node": openglider.lines.Node,
           "AttachmentPoint": openglider.glider.rib_elements.AttachmentPoint,
           ################################BEZIER##############################
           "BezierCurve": openglider.utils.bezier.BezierCurve,
           "SymmetricBezier": openglider.utils.bezier.SymmetricBezier,
           ################################Glider2D############################
           "Glider2D": openglider.glider.Glider2D,
           "LineSet2D": openglider.glider.glider_2d.LineSet2D,
           "LowerNode2D": openglider.glider.glider_2d.LowerNode2D,
           "UpperNode2D": openglider.glider.glider_2d.UpperNode2D,
           "BatchNode2D": openglider.glider.glider_2d.BatchNode2D,
           "Line2D": openglider.glider.glider_2d.Line2D,
           }