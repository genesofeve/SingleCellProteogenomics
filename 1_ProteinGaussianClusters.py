#%% Imports
from imports import *
import numpy as np
from stretch_time import stretch_time
from scipy.optimize import least_squares
from scipy.optimize import minimize_scalar
from sklearn.neighbors import RadiusNeighborsRegressor
from sklearn.mixture import GaussianMixture
from mpl_toolkits.axes_grid1 import make_axes_locatable

#%% Read in the protein data
# Idea: read in the protein data to compare with the RNA seq data
#       use the mean intensity and integrated intensity for different cutoffs (ab and microtubules)
# Exec: pandas
# Output: fucci plot from the immunofluorescence data

# Some wells in the last plate didn't have anything.
emptywells = set(["B11_6745","C11_6745","D11_6745","E11_6745","F11_6745","G11_6745","H11_6745",
    "A12_6745","B12_6745","C12_6745","D12_6745","E12_6745","F12_6745","G12_6745"])

print("reading protein IF data")
my_df1 = pd.read_csv("..\\CellCycleSingleCellRNASeq\\fucci_screen\\nuc_predicted_prob_phases_mt_all_firstbatch_plates.csv")
my_df2 = pd.read_csv("..\\CellCycleSingleCellRNASeq\\fucci_screen\\nuc_predicted_prob_phases_190909.csv")
my_df = pd.concat((my_df1, my_df2), sort=True)
print(f"{len(my_df)}: number of cells before filtering empty wells")
my_df = my_df[~my_df.well_plate.isin(emptywells)]
print(f"{len(my_df)}: number of cells after filtering empty wells")
print("loaded")


#def get_fld_num(plate, imgnb):
##    well_columns = ["A","B","C","D","E","F","G","H"]
##    well_rows = [f"{rr:02d}" for rr in np.arange(1, 13)] 
##    wells = [f"{ww}{rr}" for ww in well_columns for rr in well_rows]
#    if plate != 6720:
#        return (imgnb - 1) % 6 + 1
#    else:
#        return (imgnb - 1) % 4 + 1
    
def read_sample_info(df):
    '''Get the metadata for all the samples'''
    plate = np.asarray(df.plate)
    u_plate = np.unique(plate)
    well_plate = np.asarray(df.well_plate)
    imgnb = np.asarray(df.ImageNumber)
    well_plate_imgnb = np.asarray([f"{wp}_{imgnb[i]}" for i,wp in enumerate(well_plate)])
    u_well_plates = np.unique(well_plate)
    ab_objnum = np.asarray(df.ObjectNumber)
    area_cell = np.asarray(df.Area_cell)
    area_nuc = np.asarray(df.AreaShape_Area)
    area_cyto = np.asarray(df.Area_cyto)
    name_df = pd.read_csv("input\\Fucci_staining_summary_first_plates.csv")
    wppp1, ensggg1, abbb1, rrrr = list(name_df["well_plate"]), list(name_df["ENSG"]), list(name_df["Antibody"]), list(name_df["Results_final_update"])
    name_df2 = pd.read_csv("input\\Fucci_staining_review_variation_check.csv")
    wppp2, ensggg2, abbb2 = list(name_df2["well_plate"]), list(name_df2["ENSG"]), list(name_df2["Antibody"])
    wppp, ensggg, abbb = wppp1 + wppp2, ensggg1 + ensggg2, abbb1 +  abbb2
    ensg_dict = dict([(wppp[i], ensggg[i]) for i in range(len(wppp))])
    ab_dict = dict([(wppp[i], abbb[i]) for i in range(len(wppp))])
    result_dict = dict([(wppp[i], rrrr[i]) for i in range(len(wppp1))])
    ENSG = np.asarray([ensg_dict[wp] if wp in ensg_dict else "" for wp in well_plate])
    antibody = np.asarray([ab_dict[wp] if wp in ab_dict else "" for wp in well_plate])
    result = np.asarray([result_dict[wp] if wp in result_dict else "" for wp in well_plate])
    return plate, u_plate, well_plate, well_plate_imgnb, u_well_plates, ab_objnum, area_cell, area_nuc, area_cyto, ensg_dict, ab_dict, result_dict, ENSG, antibody, result

def previous_results(u_well_plates, result_dict, ensg_dict):
    '''Process the results metadata into lists of previously annotated CCD proteins'''
    wp_ensg = np.asarray([ensg_dict[wp] if wp in ensg_dict else "" for wp in u_well_plates])
    wp_prev_ccd = np.asarray([wp in result_dict and result_dict[wp] == "ccd" for wp in u_well_plates])
    wp_prev_notccd = np.asarray([wp in result_dict and result_dict[wp] == "notccd" for wp in u_well_plates])
    wp_prev_negative = np.asarray([wp in result_dict and result_dict[wp] == "negative" for wp in u_well_plates])
    prev_ccd_ensg = wp_ensg[wp_prev_ccd]
    prev_notccd_ensg = wp_ensg[wp_prev_notccd]
    prev_negative_ensg = wp_ensg[wp_prev_negative]
    return wp_ensg, wp_prev_ccd, wp_prev_notccd, wp_prev_negative, prev_ccd_ensg, prev_notccd_ensg, prev_negative_ensg

# 0: use mean, 
# 1: use integrated,
# 2: use the product of integrated * mean
mean_integrated_ratio = 1 # small cells are often brighter and this is just because they have rounded up and are thicker
def read_sample_data(df):
    # Antibody data (mean intensity)
    ab_nuc = np.asarray([df.Intensity_MeanIntensity_ResizedAb, df.Intensity_IntegratedIntensity_ResizedAb, df.Intensity_MeanIntensity_ResizedAb / df.Intensity_IntegratedIntensity_ResizedAb][mean_integrated_ratio])
    ab_cyto = np.asarray([df.Mean_ab_Cyto, df.Integrated_ab_cyto, df.Mean_ab_Cyto / df.Integrated_ab_cyto][mean_integrated_ratio])
    ab_cell = np.asarray([df.Mean_ab_cell, df.Integrated_ab_cell, df.Mean_ab_cell / df.Integrated_ab_cell][mean_integrated_ratio])
    mt_cell = np.asarray([df.Mean_mt_cell, df.Integrated_mt_cell, df.Mean_mt_cell / df.Integrated_mt_cell][mean_integrated_ratio])

    # Fucci data (mean intensity)
    green_fucci = np.asarray(df.Intensity_MeanIntensity_CorrResizedGreenFUCCI)
    red_fucci = np.asarray(df.Intensity_MeanIntensity_CorrResizedRedFUCCI)
    return ab_nuc, ab_cyto, ab_cell, mt_cell, green_fucci, red_fucci

plate, u_plate, well_plate, well_plate_imgnb, u_well_plates, ab_objnum, area_cell, area_nuc, area_cyto, ensg_dict, ab_dict, result_dict, ENSG, antibody, result = read_sample_info(my_df)
wp_ensg, wp_prev_ccd, wp_prev_notccd, wp_prev_negative, prev_ccd_ensg, prev_notccd_ensg, prev_negative_ensg = previous_results(u_well_plates, result_dict, ensg_dict)
ab_nuc, ab_cyto, ab_cell, mt_cell, green_fucci, red_fucci = read_sample_data(my_df)

#%% Negative staining (mean intensity max per image) not zero center (testing to make sure this negative staining filter works well)
# Negative staining (mean intensity sum per image)
ab_cell_h12_max, ab_cell_h12_max_wp = [], []
ab_cell_neg_max, ab_cell_neg_max_wp = [], []
ab_cell_all_max, ab_cell_all_max_wp = [], []
ab_cell_max, ab_cell_max_wp = [], []
ab_cell_max_p = {} # keep track of the max values for each plate to median center
for wp in u_well_plates:
    p = wp.split("_")[1]
    image_max_cell = np.log10(np.max(ab_cell[well_plate == wp]))
    if wp.startswith("H12"):
        ab_cell_h12_max.append(image_max_cell)
        ab_cell_h12_max_wp.append(wp)
    if wp in result_dict and not wp.startswith("H12"):
        ab_cell_all_max.append(image_max_cell)
        ab_cell_all_max_wp.append(wp)
        if p in ab_cell_max_p: 
            ab_cell_max_p[p].append(image_max_cell)
        else: 
            ab_cell_max_p[p] = [image_max_cell]
        if result_dict[wp].startswith("neg"):
            ab_cell_neg_max.append(image_max_cell)
            ab_cell_neg_max_wp.append(wp)
        else:
            ab_cell_max.append(image_max_cell)
            ab_cell_max_wp.append(wp)

# zero centering
ab_cell_max_zeroc = np.array(ab_cell_max)
ab_cell_all_max_zeroc = np.array(ab_cell_all_max)
ab_cell_neg_max_zeroc = np.array(ab_cell_neg_max)
ab_cell_h12_max_zeroc = np.array(ab_cell_h12_max)[np.nonzero([wp.split("_")[1] in ab_cell_max_p for wp in ab_cell_h12_max_wp])]
ab_cell_max_zeroc -= np.asarray([np.median(ab_cell_max_p[wp.split("_")[1]]) for wp in ab_cell_max_wp])
ab_cell_all_max_zeroc -= np.asarray([np.median(ab_cell_max_p[wp.split("_")[1]]) for wp in ab_cell_all_max_wp])
ab_cell_neg_max_zeroc -= np.asarray([np.median(ab_cell_max_p[wp.split("_")[1]]) for wp in ab_cell_neg_max_wp])
ab_cell_h12_max_zeroc -= np.asarray([np.median(ab_cell_max_p[wp.split("_")[1]]) for wp in ab_cell_h12_max_wp if wp.split("_")[1] in ab_cell_max_p])

upper_neg_max_cutoff = np.mean(ab_cell_neg_max_zeroc) #+ 0.5 * np.std(ab_cell_neg_max_zeroc)
lower_neg_max_cutoff = np.mean(ab_cell_neg_max_zeroc) #- 0.5 * np.std(ab_cell_neg_max_zeroc)

# except that we just need H12 for each plate
bins = plt.hist(ab_cell_h12_max_zeroc, bins=100, alpha=0.5, label="H12s")
bins = plt.hist(ab_cell_neg_max_zeroc, bins=100, alpha=0.5, label="Negative Staining")
bins = plt.hist(ab_cell_max_zeroc, bins=100, alpha=0.5, label="Positive Staining")
plt.legend()
plt.vlines(upper_neg_max_cutoff, 0, np.max(bins[0]))
plt.title("Staining (log10 max mean intensity per image, zero centered per plate)")
plt.savefig("figures/negativeStainingFilter_withH12.png")
plt.show()
plt.close()

print("filtering with just the H12, not zero centered")
h12dict_p = dict((wp.split("_")[1], ab_cell_h12_max[i]) for i, wp in enumerate(ab_cell_h12_max_wp))
num_neg_removed = sum(np.array(ab_cell_neg_max) - np.array([h12dict_p[wp.split("_")[1]] for wp in ab_cell_neg_max_wp]) < 0)
num_pos_removed = sum(np.array(ab_cell_max) - np.array([h12dict_p[wp.split("_")[1]] for wp in ab_cell_max_wp]) < 0)
num_ccd_removed = sum((np.array(ab_cell_max) - np.array([h12dict_p[wp.split("_")[1]] for wp in ab_cell_max_wp]) < 0) & np.isin(ab_cell_max_wp, wp_prev_ccd))
neg_now_were_pos = (np.array(ab_cell_all_max) - np.array([h12dict_p[wp.split("_")[1]] for wp in ab_cell_all_max_wp]) < 0) & ~np.isin(ab_cell_all_max_wp, ab_cell_neg_max_wp)
were_neg_now_pos = (np.array(ab_cell_all_max) - np.array([h12dict_p[wp.split("_")[1]] for wp in ab_cell_all_max_wp]) >= 0) & np.isin(ab_cell_all_max_wp, ab_cell_neg_max_wp)
print(f"{num_neg_removed / len(ab_cell_neg_max_zeroc)}: percent of neg stains removed")
print(f"{num_pos_removed / len(ab_cell_max_zeroc)}: percent of pos stains removed")
print(f"{num_ccd_removed / len(ab_cell_max_zeroc)}: percent of ccd stains removed")
print(f"{len(ab_cell_neg_max_zeroc) / (len(ab_cell_neg_max_zeroc) + len(ab_cell_max_zeroc))}: percent of all that were negative before")
print(f"{sum(ab_cell_max_zeroc < upper_neg_max_cutoff) / (len(ab_cell_max_zeroc) + len(ab_cell_neg_max_zeroc))}: percent of all that are negative with this cutoff")
pd.DataFrame({"well_plate":np.array(ab_cell_all_max_wp)[neg_now_were_pos]}).to_csv("output/neg_now_were_pos.csv")
pd.DataFrame({"well_plate":np.array(ab_cell_all_max_wp)[were_neg_now_pos]}).to_csv("output/were_neg_now_pos.csv")
print()

print("filtering based on annotated negative filterings, zero centered (using this one, so keep it second)")
num_neg_removed = sum(ab_cell_neg_max_zeroc < upper_neg_max_cutoff)
num_pos_removed = sum(ab_cell_max_zeroc < upper_neg_max_cutoff)
num_ccd_removed = sum((ab_cell_max_zeroc < upper_neg_max_cutoff) & np.isin(ab_cell_max_wp, wp_prev_ccd))
neg_now_were_pos = (ab_cell_all_max_zeroc < upper_neg_max_cutoff) & ~np.isin(ab_cell_all_max_wp, ab_cell_neg_max_wp)
were_neg_now_pos = (ab_cell_all_max_zeroc >= upper_neg_max_cutoff) & np.isin(ab_cell_all_max_wp, ab_cell_neg_max_wp)
print(f"{num_neg_removed / len(ab_cell_neg_max_zeroc)}: percent of neg stains removed")
print(f"{num_pos_removed / len(ab_cell_max_zeroc)}: percent of pos stains removed")
print(f"{num_ccd_removed / len(ab_cell_max_zeroc)}: percent of ccd stains removed")
print(f"{len(ab_cell_neg_max_zeroc) / (len(ab_cell_neg_max_zeroc) + len(ab_cell_max_zeroc))}: percent of all that were negative before")
print(f"{sum(ab_cell_max_zeroc < upper_neg_max_cutoff) / (len(ab_cell_max_zeroc) + len(ab_cell_neg_max_zeroc))}: percent of all that are negative with this cutoff")
pd.DataFrame({"well_plate":np.array(ab_cell_all_max_wp)[neg_now_were_pos]}).to_csv("output/neg_now_were_pos.csv")
pd.DataFrame({"well_plate":np.array(ab_cell_all_max_wp)[were_neg_now_pos]}).to_csv("output/were_neg_now_pos.csv")
print()

#%% Looking at nucleus area
# plot the areas
def plot_areas(areas, title):
    bins = plt.hist(areas, bins=100, alpha=0.5)
    plt.vlines(np.mean(areas), 0, np.max(bins[0]))
    plt.vlines(np.mean(areas) - 2 * np.std(areas), 0, np.max(bins[0]))
    plt.vlines(np.mean(areas) + 2 * np.std(areas), 0, np.max(bins[0]))
    plt.title(title)
    plt.savefig(f"figures/areas{title}.png")
    plt.show()
    plt.close()

plot_areas(area_cell, "area_cell")
plot_areas(area_nuc, "area_nuc")
plot_areas(area_cyto, "area_cyto")

# filter the super big nuclei
upper_nucleus_cutoff = np.mean(area_nuc) + 2 * np.std(area_nuc)

#%% Filter based on annotations (needs to be done after filtering negative staining because H12s used above are filtered here)
my_df_filtered = my_df
print("filtering out of focus")
oof = pd.read_csv("input\outoffocusimages.txt", header=None)[0]
well_plate = np.asarray(my_df_filtered.well_plate)
imgnb = np.asarray(my_df_filtered.ImageNumber)
well_plate_imgnb = np.asarray([f"{wp}_{imgnb[i]}" for i,wp in enumerate(well_plate)])
print(f"{len(my_df_filtered)}: number of cells before filtering out of focus images")
my_df_filtered = my_df_filtered[~np.isin(well_plate_imgnb, oof)]
print(f"{len(my_df_filtered)}: number of cells after filtering out of focus images")
print("finished filtering")

print("filtering bad fields of view")
filterthese = pd.read_csv("input/FOV_ImgNum_Lookup.csv")
badfov = filterthese["well_plate_imgnb"][filterthese["UseImage"] == 0]
well_plate = np.asarray(my_df_filtered.well_plate)
imgnb = np.asarray(my_df_filtered.ImageNumber)
well_plate_imgnb = np.asarray([f"{wp}_{imgnb[i]}" for i,wp in enumerate(well_plate)])
print(f"{len(my_df_filtered)}: number of cells before filtering out of focus images")
my_df_filtered = my_df_filtered[~np.isin(well_plate_imgnb, badfov)]
print(f"{len(my_df_filtered)}: number of cells after filtering out of focus images")
print("finished filtering")

print("filtering super big nuclei")
cell_passes_nucleus_filter = my_df_filtered.AreaShape_Area < upper_nucleus_cutoff
my_df_filtered = my_df_filtered[cell_passes_nucleus_filter]
print(f"{len(my_df_filtered)}: number of cells after filtering out super big nuclei")
plot_areas(my_df_filtered.AreaShape_Area, "area_nuc_filtered")
print("finished filtering on nuclei")

plate, u_plate, well_plate, well_plate_imgnb, u_well_plates, ab_objnum, area_cell, area_nuc, area_cyto, ensg_dict, ab_dict, result_dict, ENSG, antibody, result = read_sample_info(my_df_filtered)
wp_ensg, wp_prev_ccd, wp_prev_notccd, wp_prev_negative, prev_ccd_ensg, prev_notccd_ensg, prev_negative_ensg = previous_results(u_well_plates, result_dict, ensg_dict)
ab_nuc, ab_cyto, ab_cell, mt_cell, green_fucci, red_fucci = read_sample_data(my_df_filtered)

#%% Filter negative stains from larger dataset
ab_cell_max_negctrl, ab_cell_max_negctrl_wp = [], []
ab_cell_max, ab_cell_max_wp = [], []
ab_cell_max_all, ab_cell_max_all_wp = [], []
ab_cell_max_p = {} # keep track of the max values for each plate to median center
for wp in u_well_plates:
    p = wp.split("_")[1]
    image_max_cell = np.log10(np.max(ab_cell[well_plate == wp]))
    if wp.startswith("H12"):
        ab_cell_max_negctrl.append(image_max_cell)
        ab_cell_max_negctrl_wp.append(wp)
    else:
        ab_cell_max.append(image_max_cell)
        ab_cell_max_wp.append(wp)
    ab_cell_max_all.append(image_max_cell)
    ab_cell_max_all_wp.append(wp)
    if p in ab_cell_max_p: ab_cell_max_p[p].append(image_max_cell)
    else: ab_cell_max_p[p] = [image_max_cell]
ab_cell_max_zeroc = np.array(ab_cell_max)
ab_cell_max_negctrl_zeroc = np.array(ab_cell_max_negctrl)
ab_cell_max_all_zeroc = np.array(ab_cell_max_all)
ab_cell_max_zeroc -= np.asarray([np.median(ab_cell_max_p[wp.split("_")[1]]) for wp in ab_cell_max_wp])
ab_cell_max_negctrl_zeroc -= np.asarray([np.median(ab_cell_max_p[wp.split("_")[1]]) for wp in ab_cell_max_negctrl_wp])
ab_cell_max_all_zeroc -= np.asarray([np.median(ab_cell_max_p[wp.split("_")[1]]) for wp in ab_cell_max_all_wp])

bins = plt.hist(ab_cell_max_negctrl_zeroc, bins=100, alpha=0.5, label="Negative Staining")
bins = plt.hist(ab_cell_max_zeroc, bins=100, alpha=0.5, label="Positive Staining")
plt.vlines(upper_neg_max_cutoff, 0, np.max(bins[0]))
plt.title("Staining (log10 max mean intensity per image, zero centered per plate)")
plt.show()
plt.close()
print(f"{sum(ab_cell_max_negctrl_zeroc < upper_neg_max_cutoff) / len(ab_cell_max_negctrl_zeroc)}: percent of neg stains removed")
print(f"{sum(ab_cell_max_zeroc < upper_neg_max_cutoff) / len(ab_cell_max_zeroc)}: percent of pos stains removed")
print(f"{len(ab_cell_max_negctrl_zeroc) / (len(ab_cell_max_negctrl_zeroc) + len(ab_cell_max_zeroc))}: percent of all that were negative before")
print(f"{sum(ab_cell_max_zeroc < upper_neg_max_cutoff) / (len(ab_cell_max_zeroc) + len(ab_cell_max_negctrl_zeroc))}: percent of all that are negative with this cutoff")

image_passes_neg_staining_filter = (ab_cell_max_all_zeroc >= upper_neg_max_cutoff) & (np.array([not str(wp).startswith("H12") for wp in u_well_plates]))
passing_u_well_plate = set(u_well_plates[image_passes_neg_staining_filter])
cell_passes_neg_staining_filter = [wp in passing_u_well_plate for wp in well_plate]
my_df_filtered = my_df_filtered[cell_passes_neg_staining_filter]
len_temp = len(ab_cell)
plate, u_plate, well_plate, well_plate_imgnb, u_well_plates, ab_objnum, area_cell, area_nuc, area_cyto, ensg_dict, ab_dict, result_dict, ENSG, antibody, result = read_sample_info(my_df_filtered)
wp_ensg, wp_prev_ccd, wp_prev_notccd, wp_prev_negative, prev_ccd_ensg, prev_notccd_ensg, prev_negative_ensg = previous_results(u_well_plates, result_dict, ensg_dict)
ab_nuc, ab_cyto, ab_cell, mt_cell, green_fucci, red_fucci = read_sample_data(my_df_filtered)
print(f"{len_temp > len(ab_cell)}: filter successful")
print(f"{len(ab_cell_max_all) - sum(image_passes_neg_staining_filter)}: images filtered")
print(f"{(len(ab_cell_max_all) - sum(image_passes_neg_staining_filter)) / len(ab_cell_max_all)}: percent of images filtered")
print(f"{len_temp - len(ab_cell)}: cells contained in those images filtered")
print(f"{(len_temp - len(ab_cell)) / len_temp}: percent of cells contained in those images filtered")
print(f"{not any([wp in u_well_plates for wp in emptywells])}: all empty wells were filtered")

#%% Zero center and rescale FUCCI data in the log space
log_green_fucci, log_red_fucci = np.log10(green_fucci), np.log10(red_fucci)
wp_p_dict = dict([(str(p), plate == p) for p in u_plate])
logmed_green_fucci_p = dict([(str(p), np.log10(np.median(green_fucci[wp_p_dict[str(p)]]))) for p in u_plate])
logmed_red_fucci_p = dict([(str(p), np.log10(np.median(red_fucci[wp_p_dict[str(p)]]))) for p in u_plate])
logmed_green_fucci = np.array([logmed_green_fucci_p[wp.split("_")[1]] for wp in well_plate])
logmed_red_fucci = np.array([logmed_red_fucci_p[wp.split("_")[1]] for wp in well_plate])
log_green_fucci_zeroc = np.array(log_green_fucci) - logmed_green_fucci
log_red_fucci_zeroc = np.array(log_red_fucci) - logmed_red_fucci
log_green_fucci_zeroc_rescale = (log_green_fucci_zeroc - np.min(log_green_fucci_zeroc)) / np.max(log_green_fucci_zeroc)
log_red_fucci_zeroc_rescale = (log_red_fucci_zeroc - np.min(log_red_fucci_zeroc)) / np.max(log_red_fucci_zeroc)
fucci_data = np.column_stack([log_green_fucci_zeroc_rescale,log_red_fucci_zeroc_rescale])
plt.hist2d(log_green_fucci_zeroc_rescale,log_red_fucci_zeroc_rescale,bins=200)
plt.savefig("figures/FucciPlotProteinIFData_unfiltered.png")
plt.show()
plt.close()


#%%
# Idea: Gaussian clustering per plate to identify G1/S/G2 and do kruskal test for variance
# Exec: sklearn.mixture.GaussianMixture & scipy.stats.kruskal
# Output: FDR for cell cycle variation per well per compartment
gaussian = GaussianMixture(n_components=3, random_state=1, max_iter=500)
cluster_labels = gaussian.fit_predict(np.array([log_green_fucci_zeroc_rescale, log_red_fucci_zeroc_rescale]).T)
for cluster in range(3):
    plt.hist2d(log_green_fucci_zeroc_rescale[cluster_labels == cluster],log_red_fucci_zeroc_rescale[cluster_labels == cluster],bins=200)
    plt.title(f"Gaussian clustered data, cluster {cluster}")
    plt.savefig(f"figures/FucciPlotProteinIFData_unfiltered_Gauss{cluster}.png")
    plt.show()
    plt.close()

# G1 is cluster 0; S-ph is cluster 1; G2 is cluster 2
wp_cell_kruskal, wp_nuc_kruskal, wp_cyto_kruskal = [],[],[]
g1 = cluster_labels == 0
sph = cluster_labels == 1
g2 = cluster_labels == 2
for wp in u_well_plates:
    curr_wp_g1 = (well_plate == wp) & g1
    curr_wp_sph = (well_plate == wp) & sph
    curr_wp_g2 = (well_plate == wp) & g2
    wp_cell_kruskal.append(scipy.stats.kruskal(ab_cell[curr_wp_g1], ab_cell[curr_wp_sph], ab_cell[curr_wp_g2])[1])
    wp_nuc_kruskal.append(scipy.stats.kruskal(ab_nuc[curr_wp_g1], ab_nuc[curr_wp_sph], ab_nuc[curr_wp_g2])[1])
    wp_cyto_kruskal.append(scipy.stats.kruskal(ab_cyto[curr_wp_g1], ab_cyto[curr_wp_sph], ab_cyto[curr_wp_g2])[1])

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

alphaa = 0.05
wp_cell_kruskal_gaussccd_adj, wp_pass_gaussccd_bh_cell = benji_hoch(alphaa, wp_cell_kruskal)
wp_nuc_kruskal_gaussccd_adj, wp_pass_gaussccd_bh_nuc = benji_hoch(alphaa, wp_nuc_kruskal)
wp_cyto_kruskal_gaussccd_adj, wp_pass_gaussccd_bh_cyto = benji_hoch(alphaa, wp_cyto_kruskal)

print(f"{len(wp_pass_gaussccd_bh_cell)}: number of genes tested")
print(f"{sum(wp_pass_gaussccd_bh_cell)}: number of passing genes at 5% FDR in cell")
print(f"{sum(wp_pass_gaussccd_bh_cyto)}: number of passing genes at 5% FDR in cytoplasm")
print(f"{sum(wp_pass_gaussccd_bh_nuc)}: number of passing genes at 5% FDR in nucleus")

#%% Pickle the results
def np_save_overwriting(fn, arr):
    with open(fn,"wb") as f:    
        np.save(f, arr, allow_pickle=True)

np_save_overwriting("output/u_plate.filterNegStain.npy", u_plate)
np_save_overwriting("output/u_well_plates.filterNegStain.npy", u_well_plates)
np_save_overwriting("output/wp_ensg.filterNegStain.npy", wp_ensg)
np_save_overwriting("output/wp_prev_ccd.filterNegStain.npy", wp_prev_ccd)
np_save_overwriting("output/wp_prev_notccd.filterNegStain.npy", wp_prev_notccd)
np_save_overwriting("output/wp_prev_negative.filterNegStain.npy", wp_prev_negative)
np_save_overwriting("output/prev_ccd_ensg.filterNegStain.npy", prev_ccd_ensg)
np_save_overwriting("output/prev_notccd_ensg.filterNegStain.npy", prev_notccd_ensg)
np_save_overwriting("output/prev_negative_ensg.filterNegStain.npy", prev_negative_ensg)
np_save_overwriting("output/well_plate.filterNegStain.npy", well_plate)
np_save_overwriting("output/ab_nuc.filterNegStain.npy", ab_nuc)
np_save_overwriting("output/ab_cyto.filterNegStain.npy", ab_cyto)
np_save_overwriting("output/ab_cell.filterNegStain.npy", ab_cell)
np_save_overwriting("output/mt_cell.filterNegStain.npy", mt_cell)
np_save_overwriting("output/green_fucci.filterNegStain.npy", green_fucci)
np_save_overwriting("output/red_fucci.filterNegStain.npy", red_fucci)
np_save_overwriting("output/log_green_fucci_zeroc.filterNegStain.npy", log_green_fucci_zeroc)
np_save_overwriting("output/log_red_fucci_zeroc.filterNegStain.npy", log_red_fucci_zeroc)
np_save_overwriting("output/log_green_fucci_zeroc_rescale.filterNegStain.npy", log_green_fucci_zeroc_rescale)
np_save_overwriting("output/log_red_fucci_zeroc_rescale.filterNegStain.npy", log_red_fucci_zeroc_rescale)
np_save_overwriting("output/wp_cell_kruskal_gaussccd_adj.filterNegStain.npy", wp_cell_kruskal_gaussccd_adj)
np_save_overwriting("output/wp_nuc_kruskal_gaussccd_adj.filterNegStain.npy", wp_nuc_kruskal_gaussccd_adj)
np_save_overwriting("output/wp_cyto_kruskal_gaussccd_adj.filterNegStain.npy", wp_cyto_kruskal_gaussccd_adj)
np_save_overwriting("output/wp_pass_gaussccd_bh_cell.filterNegStain.npy", wp_pass_gaussccd_bh_cell)
np_save_overwriting("output/wp_pass_gaussccd_bh_nuc.filterNegStain.npy", wp_pass_gaussccd_bh_nuc)
np_save_overwriting("output/wp_pass_gaussccd_bh_cyto.filterNegStain.npy", wp_pass_gaussccd_bh_cyto)
np_save_overwriting("output/fucci_data.filterNegStain.npy", fucci_data)
np_save_overwriting("output/neg_now_were_pos.filterNegStain.npy", neg_now_were_pos)
np_save_overwriting("output/were_neg_now_pos.filterNegStain.npy", were_neg_now_pos)
np_save_overwriting("output/ab_cell_all_max_wp.filterNegStain.npy", ab_cell_all_max_wp)
