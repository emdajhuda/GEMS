# Proyecto proca v.1.0
# Plot configurations

import matplotlib as mpl
import matplotlib.font_manager as font_manager

from cycler import cycler

################
## SET OF COLORS
################

def get_colors():
    """
    Returns a predefined tuple of hex color codes for consistent plotting.
    
    Returns:
        tuple: A tuple of hex color strings.
    """
    return (
        '#1a1919', '#f0784d', '#2681ab', '#ab262f', '#bc92e0', 
        '#486318', '#ed5b0c', '#f0a092', '#484f07', '#694d0c'
    )

######
# MODULO PARA CONFIGURACION GENERAL DE GRAFICOS
# For more rcParams check
# https://matplotlib.org/stable/users/explain/customizing.html#matplotlibrc-sample
####

def general():
    """
    CONFIGURACIÓN GENERAL
    """ 
    for i in [FigParam(), LineParam(), axesParam(), labelParam(), fontParam()]:
        i

    return

def FigParam():
    """
    configuracion de los marcos, resolucion, etc.
    see: https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html
    """
    # resolution
    mpl.rcParams['figure.figsize'] = [6.4, 4.8]  # (width, height) in inches
    mpl.rcParams['figure.facecolor'] = 'white'     # figure facecolor
    mpl.rcParams['figure.edgecolor'] = 'white'     # figure edgecolor
    mpl.rcParams['figure.dpi'] = 100 # resolution in dots per inch.

    # to save
    mpl.rcParams['savefig.dpi'] = 1000
    #mpl.rcParams['savefig.metadata'] = None
    mpl.rcParams['savefig.format'] = 'pdf'
    mpl.rcParams['savefig.bbox'] = 'tight' # Plot will be occupy a maximum of available space
    mpl.rcParams['savefig.pad_inches'] = 0.1
    mpl.rcParams['savefig.facecolor'] = 'auto'
    mpl.rcParams['savefig.edgecolor'] = 'auto'
    
        
def LineParam():
    # estilo de linea y grosor
    mpl.rcParams['lines.linestyle'] = '-'
    mpl.rcParams['lines.linewidth'] = 1.5
    mpl.rcParams['lines.markersize'] = 10  # weight of the marker

    # orden de los colores que usará
    mpl.rcParams['axes.prop_cycle'] = cycler('color',
                                             ['#1f77b4', '#ff7f0e', '#2ca02c',
                                              '#d62728', '#9467bd', '#8c564b',
                                              '#e377c2', '#7f7f7f', '#bcbd22',
                                              '#17becf'])

def axesParam():
    mpl.rcParams['axes.grid'] = False
    mpl.rcParams['axes.formatter.limits'] = -4, 6  # use scientific notation if log10
                                                   # of the axis range is smaller than the
                                                   # first or larger than the second

    mpl.rcParams['axes.formatter.use_mathtext'] = True # When True, use mathtext for scientific notation.

    # Display axis spines, (muestra la linea de los marcos)
    mpl.rcParams['axes.spines.left'] = True
    mpl.rcParams['axes.spines.bottom'] = True
    mpl.rcParams['axes.spines.top'] = True
    mpl.rcParams['axes.spines.right'] = True

    # draw ticks on the top side
    mpl.rcParams['xtick.bottom'] = True
    mpl.rcParams['xtick.top'] = False
    mpl.rcParams['ytick.left'] = True
    mpl.rcParams['ytick.right'] = False

    # draw x axis bottom/top major ticks
    mpl.rcParams['xtick.major.top'] = False
    mpl.rcParams['xtick.major.bottom'] = True
    mpl.rcParams['ytick.major.right'] = False
    mpl.rcParams['ytick.major.left'] = True
    
    # draw x axis bottom/top minor ticks
    mpl.rcParams['xtick.minor.top'] = False
    mpl.rcParams['xtick.minor.bottom'] = False 
    mpl.rcParams['ytick.minor.right'] = False
    mpl.rcParams['ytick.minor.left'] = False 

    # direction: {in, out, inout} señalamiento de los ejes
    mpl.rcParams['xtick.direction'] = 'out'
    mpl.rcParams['ytick.direction'] = 'out'
    
    mpl.rcParams['xtick.minor.visible'] = True # visibility of minor ticks on x-axis


def labelParam():
    mpl.rcParams['xaxis.labellocation'] = 'center'  # alignment of the xaxis label: {left, right, center}
    mpl.rcParams['yaxis.labellocation'] = 'center'  # alignment of the yaxis label: {bottom, top, center}

    # axes numbers, etc.
    # 'large' tamaño de los números de las x, y
    mpl.rcParams['xtick.labelsize'] = 13
    mpl.rcParams['ytick.labelsize'] = 13
    
    # draw label on the top/bottom
    mpl.rcParams['xtick.labeltop'] = False
    mpl.rcParams['xtick.labelbottom'] = True
    mpl.rcParams['ytick.labelright'] = False
    mpl.rcParams['ytick.labelleft'] = True
    
    # labels and title
    mpl.rcParams['axes.titlepad'] = 6.0  # pad between axes and title in points
    mpl.rcParams['axes.labelpad'] = 3.0  # 10.0     # space between label and axis
    mpl.rcParams['axes.labelweight'] = 'normal'  # weight (grosor) of the x and y labels
    mpl.rcParams['axes.labelcolor'] = 'black'
    mpl.rcParams['axes.unicode_minus'] = False  # use Unicode for the minus symbol
    mpl.rcParams['axes.linewidth'] = 1  # edge linewidth, grosor del marco

    mpl.rcParams['axes.titlesize'] = 24  # title size
    mpl.rcParams['axes.labelsize'] = 15  # label size


def legendParam():
    # Legend
    mpl.rcParams['legend.loc'] = 'best'
    mpl.rcParams['legend.frameon'] = True  # if True, draw the legend on a background patch
    mpl.rcParams['legend.framealpha'] = 0.19  # 0.8 legend patch transparency
    mpl.rcParams['legend.facecolor'] = 'inherit'  # inherit from axes.facecolor; or color spec
    mpl.rcParams['legend.edgecolor'] = 'inherit' # background patch boundary color
    mpl.rcParams['legend.fancybox'] = True  # if True, use a rounded box for the

    # mpl.rcParams['legend.numpoints'] = 1 # the number of marker points in the legend line
    # mpl.rcParams['legend.scatterpoints'] = 1 # number of scatter points
    # mpl.rcParams['legend.markerscale'] = 1.0 # the relative size of legend markers vs. original
    mpl.rcParams['legend.fontsize'] = 15  # 'medium' 'large'
    mpl.rcParams['legend.title_fontsize'] = 13  # 'xx-small'

    # Dimensions as fraction of fontsize:
    mpl.rcParams['legend.borderpad'] = 0.4  # border whitespace espacio de los bordes con respecto al texto
    mpl.rcParams['legend.labelspacing'] = 0.5  # the vertical space between the legend entries
    mpl.rcParams['legend.handlelength'] = 1.5  # the length of the legend lines defauld 2
    # mpl.rcParams['legend.handleheight'] = 0.7  # the height of the legend handle
    mpl.rcParams['legend.handletextpad'] = 0.8  # the space between the legend line and legend text
    # mpl.rcParams['legend.borderaxespad'] = 0.5  # the border between the axes and legend edge
    # mpl.rcParams['legend.columnspacing'] = 8.0  # column separation


def fontParam():
    # CONFIGURACIÓN GENERAL
    # latex modo math
    # Should be: 'dejavusans' (default), 'dejavuserif', 'cm' (Computer Modern),
    #             'stix', 'stixsans' or 'custom'
    mpl.rcParams['mathtext.fontset'] = 'cm'
    mpl.rcParams['mathtext.fallback'] = 'cm'

    # latex modo text
    # Should be: serif, sans-serif, cursive, fantasy, monospace
    mpl.rcParams['font.family'] = 'serif'
    cmfont = font_manager.FontProperties(fname=mpl.get_data_path()
                                         + '/fonts/ttf/cmr10.ttf')
    mpl.rcParams['font.serif'] = cmfont.get_name()
    mpl.rcParams['font.size'] = 16  # size of the text

    # latex
    mpl.rcParams['text.usetex'] = True
    mpl.rcParams['pgf.rcfonts'] = False
    mpl.rcParams['text.latex.preamble'] = r'\usepackage{amssymb}'  # , \usepackage{txfonts}
    mpl.rcParams['pgf.preamble'] = r'\usepackage{amssymb}'