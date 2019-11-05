#%% Imports
from imports import *
import numpy as np
from stretch_time import stretch_time
from scipy.optimize import least_squares
from scipy.optimize import minimize_scalar
from sklearn.neighbors import RadiusNeighborsRegressor
import collections
import fucci_plotting
import operator
from mpl_toolkits.axes_grid1 import make_axes_locatable

#%% Read in the protein data
# Idea: read in the protein data to compare with the RNA seq data
# Exec: pandas
# Output: fucci plot from the immunofluorescence data
print("reading protein IF data")
plate = np.load("output/plate.filterNegStain.npy", allow_pickle=True)
u_plate = np.load("output/u_plate.filterNegStain.npy", allow_pickle=True)
well_plate=np.load("output/well_plate.filterNegStain.npy", allow_pickle=True)
imgnb=np.load("output/imgnb.filterNegStain.npy", allow_pickle=True)
u_well_plates=np.load("output/u_well_plates.filterNegStain.npy", allow_pickle=True)
ab_objnum=np.load("output/ab_objnum.filterNegStain.npy", allow_pickle=True)
ab_nuc=np.load("output/ab_nuc.filterNegStain.npy", allow_pickle=True)
ab_cyto=np.load("output/ab_cyto.filterNegStain.npy", allow_pickle=True)
ab_cell=np.load("output/ab_cell.filterNegStain.npy", allow_pickle=True)
mt_cell=np.load("output/mt_cell.filterNegStain.npy", allow_pickle=True)
green_fucci=np.load("output/green_fucci.filterNegStain.npy", allow_pickle=True)
red_fucci=np.load("output/red_fucci.filterNegStain.npy", allow_pickle=True)
log_green_fucci_zeroc=np.load("output/log_green_fucci_zeroc.filterNegStain.npy", allow_pickle=True)
log_red_fucci_zeroc=np.load("output/log_red_fucci_zeroc.filterNegStain.npy", allow_pickle=True)
log_green_fucci_zeroc_rescale=np.load("output/log_green_fucci_zeroc_rescale.filterNegStain.npy", allow_pickle=True)
log_red_fucci_zeroc_rescale=np.load("output/log_red_fucci_zeroc_rescale.filterNegStain.npy", allow_pickle=True)
wp_cell_kruskal_gaussccd_adj = np.load("output/wp_cell_kruskal_gaussccd_adj.filterNegStain.npy", allow_pickle=True)
wp_nuc_kruskal_gaussccd_adj = np.load("output/wp_nuc_kruskal_gaussccd_adj.filterNegStain.npy", allow_pickle=True)
wp_cyto_kruskal_gaussccd_adj = np.load("output/wp_cyto_kruskal_gaussccd_adj.filterNegStain.npy", allow_pickle=True)
wp_pass_gaussccd_bh_cell = np.load("output/wp_pass_gaussccd_bh_cell.filterNegStain.npy", allow_pickle=True)
wp_pass_gaussccd_bh_nuc = np.load("output/wp_pass_gaussccd_bh_nuc.filterNegStain.npy", allow_pickle=True)
wp_pass_gaussccd_bh_cyto = np.load("output/wp_pass_gaussccd_bh_cyto.filterNegStain.npy", allow_pickle=True)
fucci_data = np.load("output/fucci_data.filterNegStain.npy", allow_pickle=True)

wp_ensg = np.load("output/wp_ensg.filterNegStain.npy", allow_pickle=True) 
wp_prev_ccd = np.load("output/wp_prev_ccd.filterNegStain.npy", allow_pickle=True) 
wp_prev_notccd = np.load("output/wp_prev_notccd.filterNegStain.npy", allow_pickle=True) 
wp_prev_negative = np.load("output/wp_prev_negative.filterNegStain.npy", allow_pickle=True) 
prev_ccd_ensg = np.load("output/prev_ccd_ensg.filterNegStain.npy", allow_pickle=True) 
prev_notccd_ensg = np.load("output/prev_notccd_ensg.filterNegStain.npy", allow_pickle=True) 
prev_negative_ensg = np.load("output/prev_negative_ensg.filterNegStain.npy", allow_pickle=True)

u_well_plates_old = np.load("output/u_well_plates.devin.npy", allow_pickle=True)
perc_var_compartment_old = np.load("output/perc_var_compartment.devin.npy", allow_pickle=True)
perc_var_cell_old = np.load("output/perc_var_cell.devin.npy", allow_pickle=True)
perc_var_nuc_old = np.load("output/perc_var_nuc.devin.npy", allow_pickle=True)
perc_var_cyto_old = np.load("output/perc_var_cyto.devin.npy", allow_pickle=True)
print("loaded")

#%% 
# Idea: Calculate the polar coordinates and other stuff
# Exec: Devin's calculations
# Output: fucci plot with polar coordinates

NBINS = 150 #number of bins, arbitrary choice for now

def calc_R(xc, yc, x, y):
    """ calculate the distance of each 2D points from the center (xc, yc) """
    return np.sqrt((x-xc)**2 + (y-yc)**2)

def f_2(c,x,y):
    """ calculate the algebraic distance between the data points and the mean circle centered at c=(xc, yc) """
    print(c)
    Ri = calc_R(c[0],c[1],x,y)
    return Ri - Ri.mean()

def cart2pol(x, y):
    rho = np.sqrt(x**2 + y**2)
    phi = np.arctan2(y, x)
    return(rho, phi)

# Center data
x0 = np.ones(5)
x = fucci_data[:,0]
y = fucci_data[:,1]
center_estimate = np.mean(fucci_data[:,0]), np.mean(fucci_data[:,1])
center_2 = least_squares(f_2, center_estimate, args=(x, y))
xc_2, yc_2 = center_2.x
Ri_2       = calc_R(*center_2.x,x,y)
R_2        = Ri_2.mean()
residu_2   = sum((Ri_2 - R_2)**2)
centered_data = fucci_data-center_2.x

# Convert data to polar
pol_data = cart2pol(centered_data[:,0],centered_data[:,1])
pol_sort_inds = np.argsort(pol_data[1])
pol_sort_rho = pol_data[0][pol_sort_inds]
pol_sort_phi = pol_data[1][pol_sort_inds]
centered_data_sort0 = centered_data[pol_sort_inds,0]
centered_data_sort1 = centered_data[pol_sort_inds,1]

# Sort data by polar coordinates
def pol_sort(inds, nuc, cyto, cell, mt):
    return nuc[inds], cyto[inds], cell[inds], mt[inds]
well_plate_sort = well_plate[pol_sort_inds]
ab_nuc_sort, ab_cyto_sort, ab_cell_sort, mt_cell_sort = pol_sort(pol_sort_inds,ab_nuc,ab_cyto,ab_cell,mt_cell)

# Rezero to minimum --reasoning, cells disappear during mitosis, so we should have the fewest detected cells there
bins = plt.hist(pol_sort_phi,NBINS)
start_phi = bins[1][np.argmin(bins[0])]

# Move those points to the other side
more_than_start = np.greater(pol_sort_phi,start_phi)
less_than_start = np.less_equal(pol_sort_phi,start_phi)
def pol_reord(arr):
    return np.concatenate((arr[more_than_start],arr[less_than_start]))

pol_sort_well_plate = pol_reord(well_plate_sort)
# gene, antibody, Uniprot, ENSG
pol_sort_rho_reorder = pol_reord(pol_sort_rho)
pol_sort_inds_reorder = pol_reord(pol_sort_inds)
pol_sort_phi_reorder = np.concatenate((pol_sort_phi[more_than_start],pol_sort_phi[less_than_start]+np.pi*2))
pol_sort_ab_nuc, pol_sort_ab_cyto, pol_sort_ab_cell, pol_sort_mt_cell = pol_reord(ab_nuc_sort), pol_reord(ab_cyto_sort), pol_reord(ab_cell_sort), pol_reord(mt_cell_sort)
pol_sort_centered_data0, pol_sort_centered_data1 = pol_reord(centered_data_sort0), pol_reord(centered_data_sort1)

#shift and re-scale "time"; reverse "time" since the cycle goes counter-clockwise wrt the fucci plot
pol_sort_shift = pol_sort_phi_reorder+np.abs(np.min(pol_sort_phi_reorder))
pol_sort_norm = pol_sort_shift/np.max(pol_sort_shift)
pol_sort_norm_rev = 1-pol_sort_norm
pol_sort_norm_rev = stretch_time(pol_sort_norm_rev)

#apply uniform radius (rho) and convert back
def pol2cart(rho, phi):
    x = rho * np.cos(phi)
    y = rho * np.sin(phi)
    return(x, y)

cart_data_ur = pol2cart(np.repeat(R_2,len(centered_data)), pol_data[1])

def fucci_hist2d(centered_data,cart_data_ur,start_pt,nbins=200):
    fig, ax1 = plt.subplots(figsize=(10,10))
    mycmap = plt.cm.gray_r
    mycmap.set_under(color='w',alpha=None)
    ax1.hist2d(centered_data[:,0],centered_data[:,1],bins=nbins,alpha=1,cmap=mycmap)
    hist, xbins, ybins = np.histogram2d(cart_data_ur[0],cart_data_ur[1], bins=nbins, normed=True)
    extent = [xbins.min(),xbins.max(),ybins.min(),ybins.max()]
    im = ax1.imshow(
            np.ma.masked_where(hist == 0, hist).T,
            interpolation='nearest',
            origin='lower',
            extent=extent,
            cmap='plasma')
    plt.scatter(start_pt[0],start_pt[1],c='c',linewidths=4)
    plt.scatter(0,0,c='m',linewidths=4)
    plt.xlabel(r'$\propto log_{10}(GMNN_{fucci})$',size=20,fontname='Arial')
    plt.ylabel(r'$\propto log_{10}(CDT1_{fucci})$',size=20,fontname='Arial')
    plt.tight_layout()
    plt.savefig(os.path.join('figures/masked_polar_hist.pdf'),transparent=True)
    plt.close()

#visualize that result
start_pt = pol2cart(R_2,start_phi)
fucci_hist2d(centered_data,cart_data_ur,start_pt)

#%% Filter for variation (log values)
# Idea: Filter for the proteins that show variation
# Execution: Use the levene test for unequal variances for each protein to check whether there is more variation than microtubules @ 5% FDR
#      Use the natural numbers or log transformed, and use the median levene test, which works for skewed distributions like intensities
#      Use one-tailed test and check for greater variance
# Output: list of proteins that show variation

# benjimini-hochberg multiple testing correction
# source: https://www.statsmodels.org/dev/_modules/statsmodels/stats/multitest.html
def _ecdf(x):
    '''no frills empirical cdf used in fdrcorrection'''
    nobs = len(x)
    return np.arange(1,nobs+1)/float(nobs)

def benji_hoch(alpha, pvals):
    pvals = np.nan_to_num(pvals, nan=1) # fail the ones with not enough data
    pvals_sortind = np.argsort(pvals)
    pvals_sorted = np.take(pvals, pvals_sortind)
    ecdffactor = _ecdf(pvals_sorted)
    reject = pvals_sorted <= ecdffactor*alpha
    reject = pvals_sorted <= ecdffactor*alpha
    if reject.any():
        rejectmax = max(np.nonzero(reject)[0])
        reject[:rejectmax] = True
    pvals_corrected_raw = pvals_sorted / ecdffactor
    pvals_corrected = np.minimum.accumulate(pvals_corrected_raw[::-1])[::-1]
    del pvals_corrected_raw
    pvals_corrected[pvals_corrected>1] = 1
    pvals_corrected_BH = np.empty_like(pvals_corrected)

    # deal with sorting
    pvals_corrected_BH[pvals_sortind] = pvals_corrected
    del pvals_corrected
    reject_BH = np.empty_like(reject)
    reject_BH[pvals_sortind] = reject
    return pvals_corrected_BH, reject_BH

# Filter for variation based on microtubules
use_log = False
var_cell, var_nuc, var_cyto, var_mt = [],[],[],[] # mean intensity variances per antibody
var_cell_test_p, var_nuc_test_p, var_cyto_test_p = [],[],[]
for well in u_well_plates:
    curr_well_inds = pol_sort_well_plate==well
    curr_ab_cell = pol_sort_ab_cell[curr_well_inds] if not use_log else np.log10(pol_sort_ab_cell[curr_well_inds])
    curr_ab_nuc = pol_sort_ab_nuc[curr_well_inds] if not use_log else np.log10(pol_sort_ab_nuc[curr_well_inds])
    curr_ab_cyto = pol_sort_ab_cyto[curr_well_inds] if not use_log else np.log10(pol_sort_ab_cyto[curr_well_inds])
    curr_mt_cell = pol_sort_mt_cell[curr_well_inds] if not use_log else np.log10(pol_sort_mt_cell[curr_well_inds])
    
    var_cell.append(np.var(curr_ab_cell))
    var_nuc.append(np.var(curr_ab_nuc))
    var_cyto.append(np.var(curr_ab_cyto))
    var_mt.append(np.var(curr_mt_cell))

    w, p = scipy.stats.levene(curr_mt_cell, curr_ab_cell, center="median")
    var_cell_test_p.append(p*2)
    w, p = scipy.stats.levene(curr_mt_cell, curr_ab_nuc, center="median")
    var_nuc_test_p.append(p*2)
    w, p = scipy.stats.levene(curr_mt_cell, curr_ab_cyto, center="median")
    var_cyto_test_p.append(p*2)

var_cell, var_nuc, var_cyto = np.array(var_cell), np.array(var_nuc), np.array(var_cyto)

alphaa = 0.05
wp_cell_levene_gtvariability_adj, wp_pass_gtvariability_levene_bh_cell = benji_hoch(alphaa, var_cell_test_p)
wp_nuc_levene_gtvariability_adj, wp_pass_gtvariability_levene_bh_nuc = benji_hoch(alphaa, var_nuc_test_p)
wp_cyto_levene_gtvariability_adj, wp_pass_gtvariability_levene_bh_cyto = benji_hoch(alphaa, var_cyto_test_p)
wp_isvariable_cell = (var_cell > var_mt) & wp_pass_gtvariability_levene_bh_cell
wp_isvariable_nuc = (var_nuc > var_mt) & wp_pass_gtvariability_levene_bh_nuc
wp_isvariable_cyto = (var_cyto > var_mt) & wp_pass_gtvariability_levene_bh_cyto
wp_isvariable_any = wp_isvariable_cell | wp_isvariable_nuc | wp_isvariable_cyto
print(f"{sum(wp_isvariable_cell)}: # proteins showing variation, cell, log vals tested")
print(f"{sum(wp_isvariable_nuc)}: # proteins showing variation, nuc, log vals tested")
print(f"{sum(wp_isvariable_cyto)}: # proteins showing variation, cyto, log vals tested")
print(f"{sum(wp_isvariable_any)}: # total proteins showing variation, any, log vals tested")
print()
print(f"{sum(wp_isvariable_cell) / len(wp_ensg)}: # proteins showing variation, cell, log vals tested")
print(f"{sum(wp_isvariable_nuc) / len(wp_ensg)}: # proteins showing variation, nuc, log vals tested")
print(f"{sum(wp_isvariable_cyto) / len(wp_ensg)}: # proteins showing variation, cyto, log vals tested")
print(f"{sum(wp_isvariable_any) / len(wp_ensg)}: # total proteins showing variation, any, log vals tested")

pd.DataFrame({
    "well_plate":u_well_plates,
    "var_cell_test_p":var_cell_test_p,
    "var_nuc_test_p":var_nuc_test_p,
    "var_cyto_test_p":var_cyto_test_p,
    "wp_cell_levene_gtvariability_adj":wp_cell_levene_gtvariability_adj,
    "wp_nuc_levene_gtvariability_adj":wp_nuc_levene_gtvariability_adj,
    "wp_cyto_levene_gtvariability_adj":wp_cyto_levene_gtvariability_adj,
    }).to_csv(f"output/pvalsforvariability{'loggg' if use_log else 'natural'}.csv")

    
#%% Figure out the compartment information
# Idea: Read in location information for each well_plate and decide which compartment to test
# Execution: Use a dictionary of the unique locations etc. Group compartments into metacompartments.
#     For whole cell compartments, don't make any small compartment tip the scale to cell
# Output: array of whether to use tests in cell/nuc/cyto
location_dict = dict([
    # compartment, metacompartment, is it big?
    ("Cytosol",("Cytosol", True)), ### cytosol
    ("Nucleoplasm",("Nucleus", True)), ### nucleus
    ("Nucleus",("Nucleus", True)),
    ("Nuclear speckles",("Nucleus", True)),
    ("Nuclear membrane",("Nucleus", True)),
    ("Nucleoli fibrillar center",("Nucleus", True)),
    ("Nucleoli",("Nucleus", True)),
    ("Nuclear bodies",("Nucleus", True)),
    ("Mitotic chromosome",("Nucleus", True)),
    ("Mitochondria",("Cell", True)), ### cell
    ("Plasma membrane",("Cell", True)),
    ("Intermediate filaments",("Cell", True)),
    ("Actin filaments",("Cell", True)),
    ("Golgi apparatus",("Cell", True)),
    ("Vesicles",("Cell", True)),
    ("Endoplasmic reticulum",("Cell", True)),
    ("Microtubules",("Cell", True)),
    ("Cell Junctions",("Cell", True)),
    ("Microtubule organizing center",("Cell", False)), ### cell, but small stuff
    ("Centrosome",("Cell", False)),
    ("Focal adhesion sites",("Cell", False)),
    ("Aggresome",("Cell", False)),
    ("Cytoplasmic bodies",("Cell", False)),
    ("Midbody ring",("Cell", False)),
    ("Midbody",("Cell", False)),
    ("Lipid droplets",("Cell", False)),
    ("Peroxisomes",("Cell", False)),
    ("Centriolar satellite",("Cell", False)),
    ("Mitotic spindle",("Cell", False)),
    ("Cytokinetic bridge",("Cell", False)),
    ("Microtubule ends",("Cell", False)),
    ("Rods & Rings",("Cell", False))])

wp_location_df = pd.read_csv("input/WellPlateAntibodyLocations.csv")
well_plate_location = list(wp_location_df["well_plate"])
u_well_plates_list = list(u_well_plates)
wp_sort_inds = [well_plate_location.index(wp) for wp in u_well_plates]
wp_main_location = np.array(wp_location_df["IF main antibody location"])
wp_alt_location = np.array(wp_location_df["IF additional antibody location"])
wp_ab_state_pass = np.array([wp_main_location[i] != "nan" and wp_alt_location[i] != "nan" for i, loc in enumerate(wp_main_location)])
wp_iscell, wp_isnuc, wp_iscyto = [],[],[]
for i, wp in enumerate(u_well_plates):
    loc_idx = wp_sort_inds[i]
    ab_state_pass = wp_ab_state_pass[loc_idx]
    iscell, isnuc, iscyto = ab_state_pass, ab_state_pass, ab_state_pass
    if ab_state_pass:
        locs = str(wp_main_location[loc_idx]).split(";")
        locs.extend(str(wp_alt_location[loc_idx]).split(";"))
        isnuc = all([location_dict[loc][0] == "Nucleus" for loc in locs if loc in location_dict])
        iscyto = all([location_dict[loc][0] == "Cytosol" for loc in locs if loc in location_dict])
        nocell = sum([location_dict[loc][0] == "Cell" for loc in locs if loc in location_dict]) == 0
        iscell = not isnuc and not iscyto
        justonevariable = iscell and nocell and wp_isvariable_nuc[i] != wp_isvariable_cyto[i]
        if justonevariable:
            isnuc = wp_isvariable_nuc[i]
            iscyto = wp_isvariable_cyto[i]
            iscell = False
        justsmallcellcompartments = iscell and all([location_dict[loc][0] != "Cell" or not location_dict[loc][1] for loc in locs if loc in location_dict])
        if justsmallcellcompartments: # ignore the cell annotations
            isnuc = all([location_dict[loc][0] == "Nucleus" for loc in locs if loc in location_dict and location_dict[loc][0] != "Cell"])
            iscyto = all([location_dict[loc][0] == "Cytosol" for loc in locs if loc in location_dict and location_dict[loc][0] != "Cell"])
            iscell = not isnuc and not iscyto

    wp_iscell.append(iscell)
    wp_isnuc.append(isnuc)
    wp_iscyto.append(iscyto)
wp_iscell,wp_isnuc,wp_iscyto = np.array(wp_iscell),np.array(wp_isnuc),np.array(wp_iscyto)

anncompartment_df = pd.read_csv("input/WellPlateAntibodyManualAnnCompartments.csv")
anncompartment_dict = dict([(anncompartment_df["well_plate"][i], anncompartment_df["Compartments"][i]) for i in range(len(anncompartment_df))])
wp_ann = np.array([anncompartment_dict[wp] if wp in anncompartment_dict else "" for wp in u_well_plates])
wp_ann_agrees = [wp_iscell[i] and ann.lower() == "cell" or wp_isnuc[i] and ann.lower() == "nucleus" or wp_iscyto[i] and ann.lower() == "cytosol" for i, ann in enumerate(wp_ann) if len(ann) > 0]

print(f"{sum(wp_iscell)}: # proteins localized to cell")
print(f"{sum(wp_isnuc)}: # proteins localized to nuc")
print(f"{sum(wp_iscyto)}: # proteins localized to cyto")
print(f"{sum(wp_ann_agrees) / len(wp_ann_agrees)}: fraction of manual annotations in agreement")
print(f"{sum(~np.array(wp_ab_state_pass))}: # proteins with failed IF staining states")
pd.DataFrame({
    "well_plate":u_well_plates,
    "wp_iscell":wp_iscell,
    "wp_isnuc":wp_isnuc,
    "wp_iscyto":wp_iscyto,
    "wp_ann":wp_ann}).to_csv("output/iscellcytonuc.csv")

wp_cell_var_and_loc = wp_iscell & wp_isvariable_cell
wp_nuc_var_and_loc = wp_isnuc & wp_isvariable_nuc
wp_cyto_var_and_loc = wp_iscyto & wp_isvariable_cyto
wp_logany_var_and_loc = wp_cell_var_and_loc | wp_nuc_var_and_loc | wp_cyto_var_and_loc
print(f"{sum(wp_cell_var_and_loc)}: # proteins showing variation, cell, and localized there")
print(f"{sum(wp_nuc_var_and_loc)}: # proteins showing variation, nuc, and localized there")
print(f"{sum(wp_cyto_var_and_loc)}: # proteins showing variation, cyto, and localized there")
print(f"{sum(wp_cell_var_and_loc|wp_nuc_var_and_loc|wp_cyto_var_and_loc)}: # total proteins showing variation and localized there")
variable_logdontmatch = (wp_cell_var_and_loc|wp_nuc_var_and_loc|wp_cyto_var_and_loc) & ~(wp_pass_gtvariability_levene_bh_cell|wp_pass_gtvariability_levene_bh_nuc|wp_pass_gtvariability_levene_bh_cyto)
print(f"{sum(variable_logdontmatch)}: variable in compartment but not any compartment")

var_comp_test_p = np.empty_like(var_cell_test_p)
var_comp_test_p[wp_iscell] = np.array(var_cell_test_p)[wp_iscell]
var_comp_test_p[wp_isnuc] = np.array(var_nuc_test_p)[wp_isnuc]
var_comp_test_p[wp_iscyto] = np.array(var_cyto_test_p)[wp_iscyto]
wp_comp_levene_gtvariability_adj = np.empty_like(wp_nuc_levene_gtvariability_adj)
wp_comp_levene_gtvariability_adj[wp_iscell] = np.array(wp_cell_levene_gtvariability_adj)[wp_iscell]
wp_comp_levene_gtvariability_adj[wp_isnuc] = np.array(wp_nuc_levene_gtvariability_adj)[wp_isnuc]
wp_comp_levene_gtvariability_adj[wp_iscyto] = np.array(wp_cyto_levene_gtvariability_adj)[wp_iscyto]
adjp_sort_inds = np.argsort(wp_comp_levene_gtvariability_adj)
pd.DataFrame({
    "well_plate":u_well_plates[adjp_sort_inds],
    "variability_compartment_p":np.array(var_cell_test_p)[adjp_sort_inds],
    "variability_compartment_adj_p":np.array(wp_cell_levene_gtvariability_adj)[adjp_sort_inds],
    }).to_csv(f"output/pvalsforvariability{'loggg' if use_log else 'natural'}_bycompartment.csv")

#%%
# Idea: process the well data
# Exec: use Devin's code
# Output: the moving average plots for each gene studied
PSIN_INIT = [np.nan,1,1,np.nan]
PSIN_BOUNDS = ((0, 1/6, 1/2, 0), (1, 100, 100, 1))
OUTLIER_NAMES = ['KIAA2026_HPA002109',
                'FEN1_HPA006581',
                'FASN_HPA006461',
                'EMP2_HPA014711',
                'CYTIP_HPA007191',
                'KREMEN2_HPA003223',
                'NXNL2_HPA045526',
                'CTU2_HPA041894',
                'GMNN_HPA054597']
PERCVAR_CUT = 0.1 #Min % of the variance explained by the cell cycle.
FDR_CUT = 0.05 #False discovery rate we will tolerate
WINDOW = 20 #Number of points for moving average window, arbitrary choice
DO_PLOTS = True #flag of whether to plot each well and save the plot
TPLOT_MODE = 'avg' #can have values of: 'avg', 'psin'
HIGHLIGHTS = ['ORC6','DUSP19','BUB1B','DPH2', 'FLI1']

def mvavg_perc_var(yvals,mv_window):
    yval_avg = np.convolve(yvals,np.ones((mv_window,))/mv_window, mode='valid')
    return np.var(yval_avg)/np.var(yvals), yval_avg

def temporal_mov_avg(curr_pol, curr_ab_norm, curr_mt_norm, outname, outsuff):
    plt.close()
    outfile = os.path.join(outname,outsuff+'_mvavg.pdf')
    if os.path.exists(outfile): return
    #plot data
    bin_size = WINDOW
    df = pd.DataFrame({
            "time" : curr_pol, 
            "intensity" : curr_ab_norm,
            "mt_intensity": curr_mt_norm})
    plt.figure(figsize=(5,5))
    plt.plot(
            df["time"],
            df["intensity"].rolling(bin_size).mean(),
            color="blue")
    plt.plot(
            df["time"],
            df["mt_intensity"].rolling(bin_size).mean(),
            color="red")
    plt.fill_between(
            df["time"], 
            df["intensity"].rolling(bin_size).quantile(0.10),
            df["intensity"].rolling(bin_size).quantile(0.90),
            color="lightsteelblue",
            label="10th & 90th Percentiles")
    plt.scatter(
            curr_pol,
            curr_ab_norm,
            c='c')
#    plt.ylim([0,1])
#    plt.xlim([0,1])
    plt.xlabel('Pseudotime')
    plt.ylabel(outsuff.split('_')[0] + ' Protein Expression')
    plt.xticks(size=14)
    plt.yticks(size=14)
    # plt.legend(fontsize=14)
    plt.tight_layout()
    if not os.path.exists(os.path.dirname(outfile)):
        os.mkdir(os.path.join(os.getcwd(), os.path.dirname(outfile)))
    plt.savefig(outfile)
    plt.close()

x_fit = np.linspace(0,1,num=200)
ccd_coeff_list = []
not_ccd_coeff_list = []
xvals = np.linspace(0,1,num=21)
ccd_pvals = []
not_ccd_pvals = []

perc_var_cell, perc_var_nuc, perc_var_cyto, perc_var_mt = [],[],[],[] # percent variance attributed to cell cycle (mean POI intensities)
mvavgs_cell, mvavgs_nuc, mvavgs_cyto, mvavgs_mt = [],[],[],[] # moving average y values
ccd_var_cell_levenep, ccd_var_nuc_levenep, ccd_var_cyto_levenep = [],[],[] # two-tailed p values for equal variance of mvavg and raw values
cell_counts = []

for i, well in enumerate(u_well_plates):
#    print(well)
    plt.close('all')
#    well = 'H05_55405991'#GMNN well, used for testing
    curr_well_inds = pol_sort_well_plate==well
    curr_pol = pol_sort_norm_rev[curr_well_inds]
    curr_ab_cell = pol_sort_ab_cell[curr_well_inds]
    curr_ab_nuc = pol_sort_ab_nuc[curr_well_inds]
    curr_ab_cyto = pol_sort_ab_cyto[curr_well_inds]
    curr_mt_cell = pol_sort_mt_cell[curr_well_inds]
    
    # Normalize mean intensities, normalized for display
    curr_ab_cell_norm = curr_ab_cell / np.max(curr_ab_cell) 
    curr_ab_nuc_norm = curr_ab_nuc / np.max(curr_ab_nuc)
    curr_ab_cyto_norm = curr_ab_cyto / np.max(curr_ab_cyto) 
    curr_mt_cell_norm  = curr_mt_cell / np.max(curr_mt_cell)
    
    # Original method from Devin's work
    perc_var_cell_val, mvavg_cell = mvavg_perc_var(curr_ab_cell_norm, WINDOW)
    perc_var_nuc_val, mvavg_nuc = mvavg_perc_var(curr_ab_nuc_norm, WINDOW)
    perc_var_cyto_val, mvavg_cyto = mvavg_perc_var(curr_ab_cyto_norm, WINDOW)
    perc_var_mt_val, mvavg_mt = mvavg_perc_var(curr_mt_cell_norm, WINDOW)
    perc_var_xvals_val, mvavg_xvals = mvavg_perc_var(curr_pol, WINDOW)

#    # Compute percent variance due to the cell cycle (mean intensities)
#    # Compute Percent var, # if WINDOW>0: # always true for this use case, so I removed the other case
#    perc_var_cell_val, mvavg_cell = mvavg_perc_var(np.log10(curr_ab_cell), WINDOW)
#    perc_var_nuc_val, mvavg_nuc = mvavg_perc_var(np.log10(curr_ab_nuc), WINDOW)
#    perc_var_cyto_val, mvavg_cyto = mvavg_perc_var(np.log10(curr_ab_cyto), WINDOW)
#    perc_var_mt_val, mvavg_mt = mvavg_perc_var(np.log10(curr_mt_cell), WINDOW)
#    perc_var_xvals_val, mvavg_xvals = mvavg_perc_var(curr_pol, WINDOW)
    
    # Levene test for different variance over cell cycle compared to mt (one-tailed)
    # Tried it on the natural intensities, but the variation is probably in the log scale, since it's normal in the log scale
    # So comparing the microtubule to antibody intensities in the log scale may make more sense
    w, p = scipy.stats.levene(np.asarray(mvavg_cell), np.asarray(mvavg_mt), center="median")
    ccd_var_cell_levenep.append(2*p)
    w, p = scipy.stats.levene(np.asarray(mvavg_nuc), np.asarray(mvavg_mt), center="median")
    ccd_var_nuc_levenep.append(2*p)
    w, p = scipy.stats.levene(np.asarray(mvavg_cyto), np.asarray(mvavg_mt), center="median")
    ccd_var_cyto_levenep.append(2*p)
    
    # What about testing for percent variance being higher for each well than the microtubules?
    # What about testing if the variances of the residuals is less than the variance overall (the fit is adding something...)
    
    # Test for equal variances of the moving averages and raw values
    perc_var_cell.append(perc_var_cell_val)
    perc_var_nuc.append(perc_var_nuc_val)
    perc_var_cyto.append(perc_var_cyto_val)
    perc_var_mt.append(perc_var_mt_val)
    
    mvavgs_cell.append(mvavg_cell)
    mvavgs_nuc.append(mvavg_nuc)
    mvavgs_cyto.append(mvavg_cyto)
    mvavgs_mt.append(mvavg_mt)
    
    cell_counts.append(len(curr_pol))
    percvar = perc_var_cell_val if wp_iscell[i] else perc_var_nuc_val if wp_isnuc[i] else perc_var_cyto_val
    if wp_prev_ccd[i] and percvar < 0.16:
        outname = "figures/191101CCDProteins"
        outstuff = wp_ensg[i]
        outfile = os.path.join(outname,outstuff+'_mvavg.pdf')
#        if os.path.exists(outfile): return
        df = pd.DataFrame({
                "time" : curr_pol, 
                "intensity" :  curr_ab_cell_norm if wp_iscell[i] else curr_ab_nuc_norm if wp_isnuc[i] else curr_ab_cyto_norm,
                "mt_intensity": curr_mt_cell_norm})
        plt.figure(figsize=(5,5))
        plt.plot(
                df["time"],
                df["intensity"].rolling(WINDOW).mean(),
                color="blue")
        plt.plot(
                df["time"],
                df["mt_intensity"].rolling(WINDOW).mean(),
                color="red")
        plt.fill_between(
                df["time"], 
                df["intensity"].rolling(WINDOW).quantile(0.10),
                df["intensity"].rolling(WINDOW).quantile(0.90),
                color="lightsteelblue",
                label="10th & 90th Percentiles")
        plt.scatter(
                curr_pol,
                curr_ab_cell_norm)
    #    plt.ylim([0,1])
    #    plt.xlim([0,1])
        plt.xlabel('Pseudotime')
        plt.ylabel(outstuff.split('_')[0] + ' Protein Expression')
        plt.xticks(size=14)
        plt.yticks(size=14)
        # plt.legend(fontsize=14)
        plt.tight_layout()
        if not os.path.exists(os.path.dirname(outfile)):
            os.mkdir(os.path.join(os.getcwd(), os.path.dirname(outfile)))
        plt.savefig(outfile)
        plt.close()
    
alpha_ccd = 0.01
perc_var_cell, perc_var_nuc, perc_var_cyto, perc_var_mt = np.array(perc_var_cell),np.array(perc_var_nuc),np.array(perc_var_cyto),np.array(perc_var_mt) # percent variance attributed to cell cycle (mean POI intensities)
wp_cell_levene_eq_ccdvariability_adj, wp_pass_eq_ccdvariability_levene_bh_cell = benji_hoch(alpha_ccd, ccd_var_cell_levenep)
wp_nuc_levene_eq_ccdvariability_adj, wp_pass_eq_ccdvariability_levene_bh_nuc = benji_hoch(alpha_ccd, ccd_var_nuc_levenep)
wp_cyto_levene_eq_ccdvariability_adj, wp_pass_eq_ccdvariability_levene_bh_cyto = benji_hoch(alpha_ccd, ccd_var_cyto_levenep)

eqccdvariability_levene_comp_p = np.empty_like(ccd_var_cell_levenep)
eqccdvariability_levene_comp_p[wp_iscell] = np.array(ccd_var_cell_levenep)[wp_iscell]
eqccdvariability_levene_comp_p[wp_isnuc] = np.array(ccd_var_nuc_levenep)[wp_isnuc]
eqccdvariability_levene_comp_p[wp_iscyto] = np.array(ccd_var_cyto_levenep)[wp_iscyto]
wp_comp_levene_eq_ccdvariability_adj, wp_pass_eq_ccdvariability_levene_bh_comp = benji_hoch(alpha_ccd, eqccdvariability_levene_comp_p)

# BenjiHoch is actually pretty liberal for this dataset. What about bonferroni?
# bonferroni MTC
def bonf(alpha, pvals):
    pvals = np.nan_to_num(pvals, nan=1) # fail the ones with not enough data
    pvals_sortind = np.argsort(pvals)
    pvals_sorted = np.take(pvals, pvals_sortind)
    alphaBonf = alpha / float(len(pvals))
    rejectBonf = pvals_sorted <= alphaBonf
    pvals_correctedBonf = pvals_sorted * float(len(pvals))
    pvals_correctedBonf_unsorted = np.empty_like(pvals_correctedBonf) 
    pvals_correctedBonf_unsorted[pvals_sortind] = pvals_correctedBonf
    rejectBonf_unsorted = np.empty_like(rejectBonf)
    rejectBonf_unsorted[pvals_sortind] = rejectBonf
    return pvals_correctedBonf_unsorted, rejectBonf_unsorted

wp_comp_levene_eq_ccdvariability_bonfadj, wp_bonfpass_eq_ccdvariability_levene_bh_comp = bonf(alpha_ccd, eqccdvariability_levene_comp_p)


#%% Do the percent variance values match up with what we measured before for the genes?
# Idea: take the perc var values from Devin's analysis and compare them to the ones now
# Execution: run old code and save the data
# Output: plot of percvar vs percvar
perc_var_comp = np.empty_like(perc_var_cell)
perc_var_comp[wp_iscell] = perc_var_cell[wp_iscell]
perc_var_comp[wp_isnuc] = perc_var_nuc[wp_isnuc]
perc_var_comp[wp_iscyto] = perc_var_cyto[wp_iscyto]

wp_comp_kruskal_adj = np.empty_like(wp_cell_kruskal_gaussccd_adj)
wp_comp_kruskal_adj[wp_iscell] = wp_cell_kruskal_gaussccd_adj[wp_iscell]
wp_comp_kruskal_adj[wp_isnuc] = wp_nuc_kruskal_gaussccd_adj[wp_isnuc]
wp_comp_kruskal_adj[wp_iscyto] = wp_cyto_kruskal_gaussccd_adj[wp_iscyto]

u_plates_old_idx = np.array([u_well_plates_list.index(wp) for wp in u_well_plates_old if wp in u_well_plates])
old_notfiltered = np.isin(u_well_plates_old, u_well_plates)
plt.scatter(perc_var_compartment_old[old_notfiltered], perc_var_comp[u_plates_old_idx], c=wp_comp_kruskal_adj[u_plates_old_idx])
plt.xlabel("percent variance old")
plt.ylabel("percent variance new")
cb = plt.colorbar()
cb.set_label("FDR for Cell Cycle Dependence")
plt.savefig("figures/PercVarAgreement.png")
plt.show()
plt.close()

#%% Calculate the cutoffs for total intensity and percent variance attributed to the cell cycle
# Idea: create cutoffs for percent variance and 
# Execution: create cutoffs for perc_var and total variance per compartment and for integrated intensity and mean intensity
# Output: Graphs that illustrate the cutoffs (integrated, mean)
# Output: Overlap of the total variance cutoffs with the original filtering done manually

perc_var_mt_valid = perc_var_mt[~np.isinf(perc_var_mt) & ~np.isnan(perc_var_mt)]
percent_var_cutoff = 0.1#np.mean(perc_var_mt_valid) + 1 * np.std(perc_var_mt_valid)
print(f"{percent_var_cutoff}: cutoff for percent of total variance due to cell cycle")

wp_cell_ccd = wp_cell_var_and_loc & (perc_var_cell >= percent_var_cutoff)
wp_nuc_ccd = wp_nuc_var_and_loc & (perc_var_nuc >= percent_var_cutoff)
wp_cyto_ccd = wp_cyto_var_and_loc & (perc_var_cyto >= percent_var_cutoff)
wp_cell_ccd_levene = wp_cell_var_and_loc & (var_cell > var_mt) & wp_pass_eq_ccdvariability_levene_bh_cell
wp_nuc_ccd_levene = wp_nuc_var_and_loc & (var_nuc > var_mt) & wp_pass_eq_ccdvariability_levene_bh_nuc
wp_cyto_ccd_levene = wp_cyto_var_and_loc & (var_cyto > var_mt) & wp_pass_eq_ccdvariability_levene_bh_cyto

var_comp = np.empty_like(var_cell)
var_comp[wp_iscell] = var_cell[wp_iscell]
var_comp[wp_isnuc] = var_nuc[wp_isnuc]
var_comp[wp_iscyto] = var_cyto[wp_iscyto]

var_pass_comp = np.empty_like(wp_cell_var_and_loc)
var_pass_comp[wp_iscell] = wp_cell_var_and_loc[wp_iscell]
var_pass_comp[wp_isnuc] = wp_nuc_var_and_loc[wp_isnuc]
var_pass_comp[wp_iscyto] = wp_cyto_var_and_loc[wp_iscyto]

eqccdvariability_levene_comp = np.empty_like(wp_cell_levene_eq_ccdvariability_adj)
eqccdvariability_levene_comp[wp_iscell] = wp_cell_levene_eq_ccdvariability_adj[wp_iscell]
eqccdvariability_levene_comp[wp_isnuc] = wp_nuc_levene_eq_ccdvariability_adj[wp_isnuc]
eqccdvariability_levene_comp[wp_iscyto] = wp_cyto_levene_eq_ccdvariability_adj[wp_iscyto]

ccd_levene_comp = np.empty_like(wp_cell_ccd_levene)
ccd_levene_comp[wp_iscell] = wp_cell_ccd_levene[wp_iscell]
ccd_levene_comp[wp_isnuc] = wp_nuc_ccd_levene[wp_isnuc]
ccd_levene_comp[wp_iscyto] = wp_cyto_ccd_levene[wp_iscyto]

wp_comp_ccd = var_pass_comp & (perc_var_comp >= percent_var_cutoff)
print(f"{sum(wp_cell_ccd)}: # proteins showing CCD variation, cell, percvar")
print(f"{sum(wp_nuc_ccd)}: # proteins showing CCD variation, nuc, percvar")
print(f"{sum(wp_cyto_ccd)}: # proteins showing CCD variation, cyto, percvar")
print(f"{sum(wp_comp_ccd)}: # proteins showing CCD variation, comp, percvar")
    
wp_comp_ccd_levene = var_pass_comp & (var_comp > var_mt) & (eqccdvariability_levene_comp < alphaa)
print(f"{sum(wp_cell_ccd_levene)}: # proteins showing CCD variation, cell, levene")
print(f"{sum(wp_nuc_ccd_levene)}: # proteins showing CCD variation, nuc, levene")
print(f"{sum(wp_cyto_ccd_levene)}: # proteins showing CCD variation, cyto, levene")
print(f"{sum(wp_comp_ccd_levene)}: # proteins showing CCD variation, comp, levene")
print(f"{sum(wp_cell_ccd_levene) / sum(wp_cell_var_and_loc)}: fraction of variable proteins showing CCD variation, cell, levene")
print(f"{sum(wp_nuc_ccd_levene) / sum(wp_nuc_var_and_loc)}: fraction of variable proteins showing CCD variation, nuc, levene")
print(f"{sum(wp_cyto_ccd_levene) / sum(wp_cyto_var_and_loc)}: fraction of variable proteins showing CCD variation, cyto, levene")
print(f"{sum(wp_comp_ccd_levene) / sum(var_pass_comp)}: fraction of variable proteins showing CCD variation, comp, levene")

wp_any_ccd_kruskal_adj = (wp_cell_kruskal_gaussccd_adj < alphaa) | (wp_nuc_kruskal_gaussccd_adj < alphaa) | (wp_cyto_kruskal_gaussccd_adj < alphaa)
plt.scatter(var_comp[var_pass_comp], perc_var_comp[var_pass_comp], c=wp_comp_kruskal_adj[var_pass_comp])
# plt.vlines(total_var_cutoff, 0, 0.9)
plt.hlines(percent_var_cutoff, 0, 0.1)
plt.xlabel("Total Variance of Protein Expression")
plt.ylabel("Fraction of Variance Due to Cell Cycle")
cb = plt.colorbar()
cb.set_label("FDR for Cell Cycle Dependence")
plt.title("Compartment - Fraction of Variance Due to Cell Cycle")
plt.savefig("figures/CompartmentProteinFractionVariance.png")
plt.show()
plt.close()
wp_comp_ccd_percvaronly = var_pass_comp & (perc_var_comp >= percent_var_cutoff)
print(f"{sum(wp_comp_ccd_percvaronly)}: # proteins showing CCD variation (mvavg), respective compartment")
wp_comp_ccd = var_pass_comp & (perc_var_comp >= percent_var_cutoff) & (wp_comp_kruskal_adj < alphaa)
print(f"{sum(wp_comp_ccd)}: # proteins showing CCD variation (mvavg & gauss), respective compartment")

plt.scatter(var_comp[var_pass_comp], -np.log10(wp_comp_levene_eq_ccdvariability_bonfadj[var_pass_comp]), c=wp_comp_kruskal_adj[var_pass_comp])
# plt.vlines(total_var_cutoff, 0, 0.9)
plt.hlines(-np.log10(0.01), 0, 0.1)
plt.xlabel("Total Variance of Protein Expression")
plt.ylabel("FDR")
cb = plt.colorbar()
cb.set_label("FDR for Cell Cycle Dependence")
plt.title("Compartment - Fraction of Variance Due to Cell Cycle")
plt.savefig("figures/CompartmentProteinFractionVariance.png")
plt.show()
plt.close()

#plt.scatter(var_cell, perc_var_cell, c=wp_cell_kruskal_adj)
## plt.vlines(total_var_cutoff, 0, 0.9)
#plt.hlines(percent_var_cutoff, 0, 0.1)
#plt.xlabel("Total Variance of Protein Expression")
#plt.ylabel("Fraction of Variance Due to Cell Cycle")
#cb = plt.colorbar()
#cb.set_label("FDR for Cell Cycle Dependence")
#plt.title("Cell - Fraction of Variance Due to Cell Cycle")
#plt.savefig("figures/CellProteinFractionVariance.png")
#plt.show()
#plt.close()
#plt.scatter(var_cyto, perc_var_cyto, c=wp_cyto_kruskal_adj)
## plt.vlines(total_var_cutoff, 0, 0.9)
#plt.hlines(percent_var_cutoff, 0, 0.1)
#plt.xlabel("Total Variance of Protein Expression")
#plt.ylabel("Fraction of Variance Due to Cell Cycle")
#cb = plt.colorbar()
#cb.set_label("FDR for Cell Cycle Dependence")
#plt.title("Cytoplasm - Fraction of Variance Due to Cell Cycle")
#plt.savefig("figures/CytoProteinFractionVariance.png")
#plt.show()
#plt.close()
#plt.scatter(var_nuc, perc_var_nuc, c=wp_nuc_kruskal_adj)
## plt.vlines(total_var_cutoff, 0, 0.9)
#plt.hlines(percent_var_cutoff, 0, 0.1)
#plt.xlabel("Total Variance of Protein Expression")
#plt.ylabel("Fraction of Variance Due to Cell Cycle")
#cb = plt.colorbar()
#cb.set_label("FDR for Cell Cycle Dependence")
#plt.title("Nucleoplasm - Fraction of Variance Due to Cell Cycle")
#plt.savefig("figures/NucProteinFractionVariance.png")
#plt.show()
#plt.close()

# Output a list of the genes that show variation
name_df = pd.read_csv("input\\Fucci_staining_summary_first_plates.csv")
wppp1, ensggg1, abbb1 = list(name_df["well_plate"]), list(name_df["ENSG"]), list(name_df["Antibody"])
name_df2 = pd.read_csv("input\\Fucci_staining_review_variation_check.csv")
wppp2, ensggg2, abbb2 = list(name_df2["well_plate"]), list(name_df2["ENSG"]), list(name_df2["Antibody"])
wppp, ensggg, abbb = wppp1 + wppp2, ensggg1 + ensggg2, abbb1 +  abbb2

ensg_dict = dict([(wppp[i], ensggg[i]) for i in range(len(wppp))])
ab_dict = dict([(wppp[i], abbb[i]) for i in range(len(wppp))])
ENSG = np.asarray([ensg_dict[wp] if wp in ensg_dict else "" for wp in well_plate])
antibody = np.asarray([ab_dict[wp] if wp in ab_dict else "" for wp in well_plate])

alpha = 0.05
does_tot_vary_cell = wp_cell_var_and_loc
does_tot_vary_nuc = wp_nuc_var_and_loc
does_tot_vary_cyto = wp_cyto_var_and_loc
does_perc_vary_cell = np.array(perc_var_cell) >= percent_var_cutoff
does_perc_vary_nuc = np.array(perc_var_nuc) >= percent_var_cutoff
does_perc_vary_cyto = np.array(perc_var_cyto) >= percent_var_cutoff
does_perc_vary_any = does_perc_vary_cell | does_perc_vary_nuc | does_perc_vary_cyto
ccd_cell = does_tot_vary_cell & does_perc_vary_cell & (wp_cell_kruskal_gaussccd_adj < alpha)
ccd_cyto = does_tot_vary_cyto & does_perc_vary_cyto & (wp_cyto_kruskal_gaussccd_adj < alpha)
ccd_nuc = does_tot_vary_nuc & does_perc_vary_nuc & (wp_nuc_kruskal_gaussccd_adj < alpha)
ccd_any = ccd_cell | ccd_cyto | ccd_nuc
ccd_comp = wp_comp_ccd
nonccd_cell = does_tot_vary_cell & ~ccd_cell
nonccd_cyto = does_tot_vary_cyto & ~ccd_cyto
nonccd_nuc = does_tot_vary_nuc & ~ccd_nuc
nonccd_any = nonccd_cell | nonccd_cyto | nonccd_nuc
nonccd_comp = var_pass_comp & ~ccd_comp

n_tot_variable = sum(wp_pass_gtvariability_levene_bh_cell|wp_pass_gtvariability_levene_bh_nuc|wp_pass_gtvariability_levene_bh_cyto)
n_tot_variable_comp = sum(wp_cell_var_and_loc|wp_nuc_var_and_loc|wp_cyto_var_and_loc)
print(f"{n_tot_variable}: # total proteins showing variation")
print(f"{n_tot_variable_comp}: # total proteins showing variation in compartment")
print(f"{len([ensg for ensg in ensggg1 if ensg in wp_ensg[wp_pass_gtvariability_levene_bh_cell|wp_pass_gtvariability_levene_bh_nuc|wp_pass_gtvariability_levene_bh_cyto]]) / len(ensggg1)}: # fraction of proteins annotated as variable still annotated as such")
print(f"{len([ensg for ensg in ensggg1 if ensg in wp_ensg[wp_cell_var_and_loc|wp_nuc_var_and_loc|wp_cyto_var_and_loc]]) / len(ensggg1)}: # fraction of proteins annotated as variable still annotated as such in selected metacompartment")

print(f"{sum(wp_prev_ccd & ccd_any) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg & gauss, any)")
print(f"{sum(wp_prev_ccd & wp_any_ccd_kruskal_adj) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (gauss, any)")
print(f"{sum(wp_prev_ccd & wp_logany_var_and_loc & does_perc_vary_any) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg, any)")
print(f"{sum(wp_prev_ccd & ccd_comp) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg & gauss, comp)")
print(f"{sum(wp_prev_ccd & (wp_comp_kruskal_adj < alphaa)) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (gauss, comp)")
print(f"{sum(wp_prev_ccd & (var_pass_comp & (perc_var_comp >= percent_var_cutoff))) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg, comp)")

print(f"{sum(wp_prev_ccd & ccd_any) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg & gauss, any)")
print(f"{sum(wp_prev_ccd & wp_any_ccd_kruskal_adj) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (gauss, any)")
print(f"{sum(wp_prev_ccd & wp_logany_var_and_loc & does_perc_vary_any) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg, any)")
print(f"{sum(wp_prev_ccd & ccd_comp) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg & gauss, comp)")
print(f"{sum(wp_prev_ccd & (wp_comp_kruskal_adj < alphaa)) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (gauss, comp)")
print(f"{sum(wp_prev_ccd & (var_pass_comp & (perc_var_comp >= percent_var_cutoff))) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg, comp)")

print(f"{sum(wp_prev_ccd & (var_pass_comp & (perc_var_comp >= percent_var_cutoff))) / len(prev_ccd_ensg)}: fraction of previously annotated CCD genes called CCD (mvavg)")
print(f"{len([ensg for ensg in wp_ensg[wp_comp_ccd] if ensg in ensggg1 and ensg in prev_ccd_ensg]) / len(wp_ensg[wp_comp_ccd])}: fraction of CCD genes that are previously annotated CCD genes (mvavg & gauss)")
print(f"{len([ensg for ensg in wp_ensg[wp_comp_kruskal_adj < alphaa] if ensg in ensggg1 and ensg in prev_ccd_ensg]) / len(wp_ensg[wp_comp_kruskal_adj < alphaa])}: fraction of CCD genes that are previously annotated CCD genes (gauss)")
print(f"{len([ensg for ensg in wp_ensg[var_pass_comp & (perc_var_comp >= percent_var_cutoff)] if ensg in ensggg1 and ensg in prev_ccd_ensg]) / len(wp_ensg[var_pass_comp & (perc_var_comp >= percent_var_cutoff)])}: fraction of CCD genes that are previously annotated CCD genes (mvavg)")
print(f"{sum(ccd_comp)}: CCD variable proteins (mvavg & gauss)")
print(f"{sum(wp_comp_kruskal_adj < alphaa)}: CCD variable proteins (gauss)")
print(f"{sum(var_pass_comp & (perc_var_comp >= percent_var_cutoff))}: CCD variable proteins (mvavg)")
print(f"{len(prev_ccd_ensg)}: CCD variable proteins (previous)")
print(f"{sum(nonccd_comp)}: non-CCD variable proteins")

examples=np.loadtxt("input/ensgexamplesfrompaper.txt", dtype=str)
print(f"{sum(~np.isin(examples,wp_ensg[ccd_any]))}: number of examples missing of {len(examples)}, which includes 1 negative control (mvavg & gauss, any)")
print(f"{sum(~np.isin(examples,wp_ensg[wp_any_ccd_kruskal_adj]))}: number of examples missing of {len(examples)}, which includes 1 negative control (gauss, any)")
print(f"{sum(~np.isin(examples,wp_ensg[wp_logany_var_and_loc & does_perc_vary_any]))}: number of examples missing of {len(examples)}, which includes 1 negative control (mvavg, any)")
print(f"{sum(~np.isin(examples,wp_ensg[ccd_any]))}: number of examples missing of {len(examples)}, which includes 1 negative control (mvavg & gauss, any)")
print(f"{sum(~np.isin(examples,wp_ensg[ccd_comp]))}: number of examples missing of {len(examples)}, which includes 1 negative control, (mvavg & gauss, comp)")
print(examples[~np.isin(examples,wp_ensg[ccd_comp])])

pd.DataFrame({
    "well_plate" : u_well_plates, 
    "ENSG": wp_ensg,
    "var_cell":var_cell,
    "var_cyto":var_cyto,
    "var_nuc":var_nuc,
    "perc_var_cell":perc_var_cell,
    "perc_var_cyto":perc_var_cyto,
    "perc_var_nuc":perc_var_nuc,
    "perc_var_comp":perc_var_comp,
    "wp_cell_kruskal_gaussccd_adj":wp_cell_kruskal_gaussccd_adj,
    "wp_cyto_kruskal_gaussccd_adj":wp_cyto_kruskal_gaussccd_adj,
    "wp_nuc_kruskal_gaussccd_adj":wp_nuc_kruskal_gaussccd_adj,
    "ccd_cell":ccd_cell,
    "ccd_cyto":ccd_cyto,
    "ccd_nuc":ccd_nuc,
    "ccd_any":ccd_any,
    "ccd_comp":ccd_comp,
    "nonccd_cell":nonccd_cell,
    "nonccd_cyto":nonccd_cyto,
    "nonccd_nuc":nonccd_nuc,
    "nonccd_any":nonccd_any,
    "nonccd_comp":nonccd_comp,
    "in_firstbatch":np.isin(wp_ensg, ensggg1),
    "in_secondbatch":np.isin(wp_ensg, ensggg2),
    "is_variable":wp_pass_gtvariability_levene_bh_cell|wp_pass_gtvariability_levene_bh_nuc|wp_pass_gtvariability_levene_bh_cyto,
    "is_variable_comp":wp_cell_var_and_loc|wp_nuc_var_and_loc|wp_cyto_var_and_loc,
    "wp_prev_ccd":wp_prev_ccd,
    "is_newccd":ccd_comp,
    }).to_csv("output/CellCycleVariationSummary.csv")
    
pd.DataFrame({"ENSG":wp_ensg[wp_prev_ccd & ~ccd_comp]}).to_csv("output/DianaCCDMissingProteins.csv")
pd.DataFrame({"ENSG":wp_ensg[~wp_prev_ccd & ccd_comp]}).to_csv("output/NewToDianaCCDProteins.csv")


#%% Pickle the results needed later
np.save("output/pol_sort_well_plate.npy", pol_sort_well_plate, allow_pickle=True)
np.save("output/pol_sort_norm_rev.npy", pol_sort_norm_rev, allow_pickle=True)
np.save("output/pol_sort_ab_nuc.npy", pol_sort_ab_nuc, allow_pickle=True)
np.save("output/pol_sort_ab_cyto.npy", pol_sort_ab_cyto, allow_pickle=True)
np.save("output/pol_sort_ab_cell.npy", pol_sort_ab_cell, allow_pickle=True)
np.save("output/pol_sort_mt_cell.npy", pol_sort_mt_cell, allow_pickle=True)
np.save("output/wp_iscell.npy", wp_iscell, allow_pickle=True)
np.save("output/wp_isnuc.npy", wp_isnuc, allow_pickle=True)
np.save("output/wp_iscyto.npy", wp_iscyto, allow_pickle=True)
np.save("output/ccd_comp.npy", ccd_comp, allow_pickle=True)
np.save("output/nonccd_comp.npy", ccd_comp, allow_pickle=True)
np.save("output/wp_ensg.npy", wp_ensg, allow_pickle=True)
np.savetxt("output/ccd_compartment_ensg.txt", wp_ensg[ccd_comp], fmt="%s", delimiter="\t")
np.savetxt("output/nonccd_compartment_ensg.txt", wp_ensg[nonccd_comp], fmt="%s", delimiter="\t")

