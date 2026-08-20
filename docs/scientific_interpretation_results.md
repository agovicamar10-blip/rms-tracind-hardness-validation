# Scientific Interpretation of the RMS Hardness-Measurement Results

## 1. Overview of the Obtained Results

The completed analysis evaluates manual and automatic hardness-related measurements for Vickers, Micro-Vickers, Brinell and Knoop data recorded in `Hardness_measurement_results.xlsx`. The numerical interpretation below is based on the exported workbook `outputs/analysis_results.xlsx`, the CSV tables in `outputs/tables/`, the analytical figures in `outputs/figures/`, and the diagnostic image overlays in `outputs/diagnostic_images/`.

The dataset contains 60 valid Vickers individual observations grouped into 20 complete three-indentation series, 54 Micro-Vickers observations grouped into 18 complete series, 36 Brinell observations grouped into 12 complete series, and 33 Knoop observations grouped into 11 complete series. Vickers, Micro-Vickers and Brinell contain paired manual and automatic measurements. Knoop contains manual long-diagonal data but no usable paired automatic hardness or automatic diagonal data, so it is retained as a cleaned source table but excluded from method-agreement, E_n and paired-validation conclusions.

The central scientific result is that the UME automatic system and the manual measurements show strong agreement for Vickers and Micro-Vickers indentation dimensions, and acceptable agreement for Brinell when the reported expanded uncertainties are considered. The mean dimensional difference, defined as automatic minus manual, is -0.026 um for Vickers, -0.057 um for Micro-Vickers, and +11.893 um for Brinell. In relative terms this corresponds to -0.029% for Vickers, -0.125% for Micro-Vickers and +0.789% for Brinell. Thus, the Vickers and Micro-Vickers automatic measurements are practically coincident with the manual measurements at the scale of the measured diagonals, while Brinell shows a larger absolute dimensional bias because its indentations are much larger. This interpretation follows the standard hardness-testing distinction between Vickers/Knoop diagonal measurement and Brinell impression-diameter measurement [1-6].

For hardness values, the sign reverses in the expected way: a larger measured indentation produces a lower calculated hardness. Consequently, the Brinell automatic hardness is on average 4.745 HBW lower than the manual value, even though the automatic diameter is larger. The Vickers automatic hardness is on average 0.636 HV higher, and the Micro-Vickers automatic hardness is on average 2.764 HV higher. These hardness differences are small compared with the hardness ranges represented by the reference blocks, especially for Vickers and Brinell. The inverse relation between hardness number and indentation size is the basic physical basis of indentation hardness testing [11,12].

The E_n analysis confirms this interpretation. All 12 Brinell series and all 20 Vickers series satisfy |E_n| <= 1. Micro-Vickers has 17 of 18 series within |E_n| <= 1; the only nonconforming series is `Micro-Vickers|SN=709-293|scale=HV 1|F=9.81N|mag=50X`, where the manual series mean hardness is 911.072 HV and the automatic series mean hardness is 941.148 HV, giving E_n = +1.548. This use of E_n follows the interlaboratory/proficiency-testing convention that agreement is assessed against the combined expanded uncertainties [7,8].

The independent Python image-analysis section should be interpreted separately from the UME automatic measurements. It was an external full-frame image-processing attempt, not the validated UME automatic algorithm. Out of 31 exactly matched image records, only 2 were classified as suitable for unattended automatic measurement by this independent routine, 5 were conditionally suitable, and 24 were rejected. This does not mean that the indentations were unsuitable for UME measurement. It means that the independent general-purpose Python routine did not reproduce the UME/manual dimensions robustly from the exported BMP images alone.

## 2. Analysis and Interpretation of the Workbook Tables

### README

The README sheet documents the purpose, sign convention and units for the exported sheets. Its most important role is metrological traceability of interpretation: dimensional differences are defined as automatic minus manual, dimensions are in micrometres, hardness is reported in the native hardness scale, and E_n is dimensionless. This sign convention is essential because hardness is inversely related to indentation size: a positive dimensional bias normally leads to a negative hardness bias.

### Data_Quality

The Data_Quality sheet records the completeness and consistency of the source data. The workbook contains complete three-position series for Vickers, Micro-Vickers, Brinell and Knoop. There are no missing individual manual or automatic dimension values for Vickers, Micro-Vickers and Brinell. The apparent missing values in series-level columns occur because the raw workbook stores series mean and uncertainty information only on one row of each three-indentation series; these are structural blanks rather than missing individual measurements.

The image inventory shows 8 Vickers Picture IDs, 20 Micro-Vickers Picture IDs and 3 Brinell Picture IDs in the workbook. Knoop has no workbook Picture IDs, so Knoop images cannot be linked to paired records. Sixty-one indentation BMP files and two calibration BMP files are present. Thirty image files have no exact workbook Picture ID match and are therefore excluded from image-linked analysis. This exclusion is scientifically appropriate because using unmatched images would break traceability between a measured indentation and its recorded manual/automatic value.

### Clean_Vickers

The Vickers table contains 60 valid paired measurements across 20 complete series. The manual series mean hardness ranges from 161.427 HV to 910.130 HV, and the automatic series mean hardness ranges from 161.397 HV to 914.857 HV. The manual series mean diagonal ranges from 78.174 um to 1069.236 um, while the automatic series mean diagonal ranges from 77.975 um to 1069.524 um.

The Vickers data cover HV 3, HV 20, HV 50 and HV 100 loads. The average hardness is stable for the medium-hardness blocks over HV 20, HV 50 and HV 100, with group mean manual hardness values around 514-518 HV. This is consistent with the Vickers principle: because the Vickers indenter is geometrically self-similar, a homogeneous material should produce approximately load-independent hardness except at very low loads, very small diagonals, or when material heterogeneity and surface effects become important. ASTM E92 explicitly notes that Vickers hardness is expected to remain essentially constant across forces for homogeneous material except at very low forces or very small indentations [5].

### Clean_Micro_Vickers

The Micro-Vickers table contains 54 valid paired measurements across 18 complete series. The manual series mean hardness ranges from 49.419 HV to 981.837 HV, and the automatic series mean hardness ranges from 49.107 HV to 980.475 HV. The manual series mean diagonal ranges from 20.849 um to 189.316 um, while the automatic series mean diagonal ranges from 20.886 um to 189.658 um.

The Micro-Vickers measurements include very small indentations, particularly at HV 0.05 where the group mean diagonal is about 31 um and individual diagonals approach the lower practical optical-measurement range. This is important scientifically because microindentation results are more sensitive to optical resolution, surface preparation, tip geometry and local microstructural heterogeneity than macroindentation results. ASTM E384 emphasizes that microindentation testing is useful for small regions and gradients but that a single value may not represent bulk hardness; it also warns that very small indents can suffer from optical-measurement imprecision [6]. This is also consistent with the indentation-size-effect literature for microindentation [11].

### Clean_Brinell

The Brinell table contains 36 valid paired measurements across 12 complete series. The manual series mean hardness ranges from 129.590 HBW to 578.167 HBW, and the automatic series mean hardness ranges from 125.954 HBW to 576.049 HBW. The manual series mean indentation diameter ranges from 116.992 um to 4840.787 um; the automatic series mean diameter ranges from 117.927 um to 4861.091 um.

The Brinell data include both 1 mm ball tests and 10 mm ball tests. The 10 mm ball series naturally produce millimetre-scale diameters, while the 1 mm ball series produce sub-millimetre diameters. A larger absolute dimensional difference in Brinell is therefore expected to some extent, because the measurand itself is much larger. The relevant question is not only the absolute micrometre difference but also the relative difference and whether the hardness difference is covered by the reported uncertainty. The E_n results show that all Brinell series satisfy |E_n| <= 1. This is consistent with Brinell being a ball-indentation method in which hardness is calculated from the measured impression diameter [2,4,11,12].

### Clean_Knoop

The Knoop table contains 33 manual long-diagonal observations across 11 complete series. The measured long diagonal ranges from 28.275 um to 533.922 um. Grouped by test condition, the mean manual diagonal is 48.554 um for HK 0.05 at 50X, 371.950 um for HK 1 at 10X, 223.611 um for HK 1 at 20X, 532.008 um for HK 2 at 10X, and 318.363 um for HK 2 at 20X.

No paired automatic Knoop values or Knoop hardness values were available in the cleaned workbook. Therefore, the Knoop data are not used for agreement or E_n conclusions. Scientifically, this is the correct conservative treatment. ISO 4545-1 specifies Knoop testing for long diagonals of at least 0.020 mm; the available Knoop diagonals are above this limit, but without paired automatic measurements no method-comparison conclusion can be drawn [3].

### Series_Summary

The Series_Summary sheet aggregates the three individual indentations in each series. This is the appropriate level for interpreting hardness as a reported result, because hardness standards and good practice normally use repeated indentations to reduce the effect of local scatter. Across the series, Vickers has the largest hardness range, from approximately 161 HV to 910 HV, reflecting the different reference blocks rather than a single material trend. Micro-Vickers also spans a wide hardness interval, from approximately 49 HV to 982 HV. Brinell spans approximately 130 HBW to 578 HBW.

The large hardness range means that the analysis is primarily a method-comparison study across several hardness levels, not a study of one material undergoing a heat treatment or microstructural change. Therefore, it would be inappropriate to attribute the hardness differences between serial-numbered blocks to grain size, phase composition, residual stress or work hardening without independent material information.

### Paired_Summary

The Paired_Summary sheet summarizes individual paired differences. For Vickers, n = 60 and the mean dimensional difference is -0.026 um, with SD = 0.367 um, RMSE = 0.365 um and MAE = 0.301 um. The paired t-test p-value is 0.586 and the Wilcoxon p-value is 0.686, so there is no evidence of a systematic dimensional offset between manual and automatic Vickers measurements.

For Micro-Vickers, n = 54 and the mean dimensional difference is -0.057 um, with SD = 0.278 um, RMSE = 0.281 um and MAE = 0.205 um. The paired t-test p-value is 0.141 and the Wilcoxon p-value is 0.488. Again, the average dimensional offset is very small and not statistically significant at conventional levels.

For Brinell, n = 36 and the mean dimensional difference is +11.893 um, with SD = 15.270 um, RMSE = 19.187 um and MAE = 11.922 um. The paired t-test p-value is 0.000043 and the Wilcoxon p-value is approximately 2.0e-10. This indicates a statistically detectable positive dimensional offset: the automatic Brinell diameter is larger than the manual diameter. However, the relative mean difference is only +0.789%, and all Brinell E_n values remain within acceptance limits. The statistical significance therefore reflects high consistency of a small systematic difference, not necessarily practical non-equivalence.

### Paired_By_Force

The Paired_By_Force table shows how dimensional bias varies with load and magnification. Vickers dimensional bias is small at all tested loads: +0.142 um at 29.43 N/20X, -0.240 um at 29.43 N/50X, -0.078 um at 196.2 N, -0.025 um at 490.5 N, and +0.010 um at 981 N. These values are negligible relative to Vickers diagonals from about 78 um to 1069 um.

Micro-Vickers bias is also small in absolute terms but more sensitive to test condition because the indentations are smaller. The largest group mean dimensional bias is -0.413 um for HV 1 at 50X, corresponding to -0.785% symmetric relative difference. This is still below 1% but is more visible than in macro Vickers because the diagonal is smaller.

Brinell shows increasing absolute bias with larger indentation scale. The group mean dimensional bias is +0.986 um for HBW 1/5, +0.930 um for HBW 1/30, +27.744 um for HBW 10/500 at 20X, +35.537 um for HBW 10/500 at 10X, and +15.315 um for HBW 10/3000. The larger micrometre differences are associated with larger Brinell impressions and lower magnification. This is consistent with the greater difficulty of defining the boundary of a large ball indentation, especially when optical magnification is lower or the edge contrast changes across the field.

### Bland_Altman

The Bland_Altman sheet gives agreement statistics for both indentation dimension and hardness. For dimensions, the Vickers bias is -0.026 um with 95% limits of agreement from -0.745 um to +0.693 um. Micro-Vickers has bias -0.057 um with limits from -0.602 um to +0.489 um. Brinell has bias +11.893 um with limits from -18.035 um to +41.821 um. Bland-Altman analysis is appropriate here because method agreement is determined from paired differences rather than from correlation alone [9].

The relative Bland-Altman results are more directly comparable across methods. Vickers has relative bias -0.029% with limits from -0.465% to +0.407%. Micro-Vickers has relative bias -0.125% with limits from -1.173% to +0.923%. Brinell has relative bias +0.789% with limits from -1.022% to +2.601%. Thus, even though Brinell has the largest absolute dimensional offset, the relative agreement remains within a few percent.

For hardness, the Brinell bias is -4.745 HBW with limits from -19.549 HBW to +10.060 HBW. Micro-Vickers has hardness bias +2.764 HV with limits from -13.346 HV to +18.875 HV. Vickers has hardness bias +0.636 HV with limits from -5.799 HV to +7.072 HV. These results reflect the nonlinear inverse relationship between hardness and indentation size: small dimensional differences at small diagonals can produce larger hardness differences than the same dimensional difference at large diagonals.

### Bland_Altman_Points

The Bland_Altman_Points sheet contains the point-level data used to draw the Bland-Altman diagrams. Each point stores the pair mean, difference, method, representation, series identifier, magnification, hardness scale, hardness level and force. This table is important because it allows the agreement plots to be audited and stratified by load, hardness level or magnification. The main observation is that Vickers and Micro-Vickers differences remain tightly clustered around zero, while Brinell has a larger spread and a visible positive dimensional offset.

### Deming

The Deming regression table assesses linear agreement while allowing measurement error in both manual and automatic measurements. For individual dimensions with lambda = 1, the slopes are 1.000433 for Vickers, 1.002153 for Micro-Vickers and 1.004677 for Brinell. These slopes are very close to unity. The residual standard deviation is 0.350 um for Vickers, 0.264 um for Micro-Vickers and 13.491 um for Brinell. Deming-type errors-in-variables regression is preferred over ordinary least squares in method-comparison settings when both axes contain measurement error [13].

For series mean hardness with lambda = 1, the slopes are 1.004171 for Vickers, 1.012060 for Micro-Vickers and 0.987913 for Brinell. The Vickers slope is very close to unity but statistically slightly above unity in the exported confidence interval. Micro-Vickers has a slope above unity, consistent with the one high-hardness Micro-Vickers E_n outlier. Brinell has a slope slightly below unity, consistent with automatic Brinell hardness being lower when automatic diameters are larger.

### ODR_Series_Hardness

The weighted orthogonal-distance regression confirms the same pattern at series level. The weighted ODR slopes are 1.002448 for Vickers, 1.006967 for Micro-Vickers and 0.998043 for Brinell. The residual variance is low for Vickers (0.057) and Brinell (0.047), and higher for Micro-Vickers (0.686). This supports the conclusion that the series-level automatic and manual hardness values are nearly collinear, with Micro-Vickers showing the largest remaining method-dependent deviation.

### En_Results

The E_n table is the strongest metrological comparison because it evaluates the difference between automatic and manual series mean hardness relative to the combined expanded uncertainties. Vickers has 20 of 20 series with |E_n| <= 1, maximum |E_n| = 0.334 and mean |E_n| = 0.094. Brinell has 12 of 12 series with |E_n| <= 1, maximum |E_n| = 0.371 and mean |E_n| = 0.175. Micro-Vickers has 17 of 18 series with |E_n| <= 1, maximum |E_n| = 1.548 and mean |E_n| = 0.302. E_n should be interpreted with the stated expanded uncertainties, not with the repeatability standard deviation alone [7,8].

The only E_n failure is the Micro-Vickers HV 1, 9.81 N, 50X series for SN 709-293. The automatic series mean hardness is 941.148 HV compared with the manual value 911.072 HV. Because E_n uses the reported expanded uncertainties, this failure means that the observed difference is not covered by the stated uncertainty budgets for that series. It does not identify the physical cause. Possible causes include local material heterogeneity, diagonal-reading differences, surface contrast, operator selection of the corner, or an uncertainty budget that is too small for that particular condition.

### Repeatability

The Repeatability sheet provides within-series statistics for each three-indentation series, separately for manual and automatic sources. This is repeatability under the short-term conditions of the dataset, not full reproducibility across operators, instruments, days or laboratories. Vickers repeatability is strong: for 20X measurements, the mean within-series SD is 0.705 um for manual and 0.763 um for automatic data, with mean CV values of 0.155% and 0.166%, respectively. Micro-Vickers repeatability is also good but relatively more sensitive to magnification and indentation size; for 50X measurements, mean SD is 0.358 um manually and 0.437 um automatically, with mean CV values of 0.679% and 0.856%. The interpretation follows the NIST measurement-process distinction between short-term repeatability and broader reproducibility or uncertainty components [10].

Brinell repeatability has the largest absolute SD because Brinell impressions are much larger. For 20X Brinell, mean within-series SD is 2.693 um manually and 5.657 um automatically. The single 10X automatic Brinell series has SD = 21.395 um and CV = 1.726%, making it the largest repeatability contributor in the dataset. This is consistent with the lower pixel resolution per indentation diameter at 10X and the greater difficulty of defining a broad Brinell boundary.

### Repeatability_Summary

The Repeatability_Summary sheet condenses the repeatability results by method, source and magnification. It confirms that Vickers is the most repeatable in relative terms, Micro-Vickers has slightly higher relative scatter because its diagonals are smaller, and Brinell has the largest absolute scatter. The comparison of manual and automatic repeatability also shows that automatic repeatability is not uniformly superior; for example, automatic Brinell at 20X has higher mean SD than manual Brinell at 20X. This does not necessarily indicate poorer automatic measurement; it may reflect how the automatic system consistently detects real boundary variations that a manual operator smooths or interprets differently.

### Calibration

The Calibration sheet reports two horizontal stage-micrometer calibrations. The 20X image gives 0.243902 um/px using 11 detected ticks over 100 um, with residual SD = 0.00000 um. The 50X image gives 0.097649 um/px using 51 detected ticks over 100 um, with residual SD = 0.03215 um. Both calibrations are classified as reliable.

The scientific limitation is that only horizontal calibration images were available. Therefore, the analysis assumes equal x and y pixel size and cannot quantify vertical scale error, field distortion, lens distortion toward image edges or magnification-dependent distortion away from the calibration line. This limitation mainly affects the independent Python image analysis, not the UME automatic measurements stored in the workbook.

### Calibration_Ticks

The Calibration_Ticks sheet gives the individual tick positions and fit residuals used to derive the pixel scale. This table demonstrates that the pixel-size calibration was not simply assumed from file names; it was fitted from detected ruler ticks. The residuals are negligible for 20X and small for 50X, supporting the internal consistency of the calibration images. However, because the stage micrometer certificate was not available, the calibration is nominal and does not include a certified stage-micrometer uncertainty contribution.

### Image_Measurements

The Image_Measurements sheet contains the independent Python image-processing results for the 31 matched image records. It includes detected contours, geometry metrics, Python dimensions and Python hardness values where available. The results must be interpreted as a diagnostic remeasurement attempt, not as a replacement for the UME automatic system.

Several Python measurements differ strongly from both manual and UME automatic values. For example, the Vickers image `216-610_701_HV_3_1_50X` produced a Python mean diagonal of only 7.638 um, whereas the manual and automatic means are about 87.157 um and 86.631 um. This is clearly a failed independent image detection, not a true hardness result. The rejection rule correctly prevents such values from entering the metrological conclusions.

### Image_Quality

The Image_Quality sheet summarizes why images were classified as reliable, conditionally reliable or rejected by the independent algorithm. The largest rejection class is "all configured image checks passed; excessive agreement difference", meaning that the image contour looked geometrically plausible to the Python routine but the resulting dimension did not agree with the existing manual and UME automatic measurements. This indicates that full-frame threshold/contour detection can select the wrong optical boundary even when a validated measurement system can measure the same indentation successfully.

### Classification

The Classification sheet translates the image-quality results into suitability classes. Vickers has 2 suitable, 2 conditionally suitable and 4 unsuitable images. Micro-Vickers has 3 conditionally suitable and 17 unsuitable images. Brinell has 3 unsuitable images. These classifications apply only to unattended external Python remeasurement of the exported BMP images. They should not be reported as evidence that the physical indentations were unsuitable for UME automatic measurement.

### Exclusions

The Exclusions sheet lists 30 image files without exact workbook Picture ID matches. This mainly affects the image-analysis subset. It does not affect the primary manual-automatic agreement analysis because the workbook measurements themselves are complete. Scientifically, the exclusions limit any image-analysis conclusion to the subset of matched images and prevent generalization to all available BMP files.

### Source_Files

The Source_Files sheet documents the input basis of the analysis: one workbook, two DOCX documents, two PDF documents, two calibration BMP files and 61 indentation BMP files. This is important for reproducibility and for defining what evidence was actually available.

### Image_Dimensions

The Image_Dimensions sheet shows that all indentation and calibration images are 1056 x 896 pixel BMP files in paletted mode. The common image geometry supports consistent image handling, but it does not by itself prove optical scale uniformity across the field of view.

## 3. Interpretation of Each Figure and Diagram

### bias_by_force.png

This bar chart shows mean dimensional bias, automatic minus manual, grouped by applied force. The dominant feature is the large positive Brinell bias at 4905 N and 29430 N, reaching approximately +30 um and +15 um, respectively. Vickers and Micro-Vickers biases remain close to zero on the same axis. The scientific meaning is that Brinell diameter reading is more sensitive in absolute micrometres because the impression is much larger; a few tens of micrometres correspond to only a small relative difference. The graph should therefore be interpreted together with the relative Bland-Altman results and E_n values [4,8,9].

### bias_by_hardness_level.png

This chart groups mean dimensional bias by nominal hardness level. The largest visible bar occurs for Brinell at hardness level 10, caused by 10 mm ball Brinell measurements. This does not indicate that high hardness itself causes bias; hardness level and test geometry are confounded here because Brinell level 10 corresponds to large-ball tests. Vickers and Micro-Vickers remain near zero, supporting the conclusion that their automatic and manual diagonal readings are consistent across the tested hardness levels.

### bias_by_magnification.png

This chart shows mean dimensional bias by magnification. Brinell at 10X has the largest bias, followed by Brinell at 20X. Vickers and Micro-Vickers are close to zero. This supports a measurement-related interpretation: lower optical magnification and larger Brinell impressions increase the absolute uncertainty of boundary definition. Because the dataset contains only one Brinell 10X series, the 10X conclusion should be treated cautiously.

### Brinell_ba_absolute_dimension.png

The Brinell absolute Bland-Altman plot displays automatic minus manual diameter against the pair mean diameter. The bias line is at +11.893 um and the 95% limits of agreement are -18.035 to +41.821 um. The plot shows mostly positive differences, especially at larger diameters, meaning that the automatic system tends to measure a slightly larger Brinell impression than the manual method. Because Brinell hardness decreases as measured diameter increases, this dimensional bias explains the negative Brinell hardness bias.

### Brinell_ba_log_ratio_dimension.png

The Brinell log-ratio Bland-Altman plot expresses agreement multiplicatively. The mean log-ratio is 0.007894, corresponding to a small positive automatic/manual diameter ratio. The limits are approximately -0.0102 to +0.0260 in log units. This representation shows that the relative disagreement is modest despite the large absolute micrometre differences at large diameters.

### Brinell_ba_relative_percent_dimension.png

This plot shows symmetric percent dimensional difference. The Brinell relative bias is +0.789%, with limits from -1.022% to +2.601%. The largest positive points are associated with the 10X/larger-diameter region. Scientifically, this means that the Brinell automatic diameter reading is systematically larger, but typically by less than about 3% at the individual-measurement level.

### Brinell_d1_d2_asymmetry.png

This scatter plot compares manual and automatic d1-d2 asymmetry. Ideally, both axes would be near zero for circular impressions measured by two perpendicular diameters. Most points are near the origin, but several automatic values show larger positive or negative asymmetry. This indicates that the Brinell impression boundary may not be perfectly circular or that the automatic and manual systems define the boundary differently. It may also reflect optical effects, edge contrast variation or specimen surface condition. The plot does not by itself prove material anisotropy.

### Brinell_deming_dimension.png

The Brinell Deming regression plot shows automatic diameter against manual diameter. Points lie close to the identity line, and the lambda = 1 Deming slope is 1.004677 with intercept 4.901 um. This indicates strong linear agreement over the full Brinell diameter range, with a small positive automatic offset. The residual SD is 13.491 um, which is large relative to Vickers/Micro-Vickers but small relative to millimetre-scale Brinell diameters.

### Brinell_difference_distribution.png

The Brinell paired-difference histogram is right-skewed and centred above zero. The mean difference is +11.893 um. The distribution confirms that the Brinell offset is not driven by a single point only; rather, most differences are positive, with a tail toward larger positive automatic-minus-manual diameter values. This supports a systematic measurement-method effect.

### Brinell_En.png

The Brinell E_n plot shows all Brinell series between -1 and +1, with maximum |E_n| = 0.371. Although automatic Brinell diameters are larger on average, the resulting hardness differences are covered by the stated expanded uncertainties. From a proficiency-style metrological standpoint, the Brinell manual and automatic series results are therefore compatible.

### Brinell_scatter_dimension.png

The Brinell manual-versus-automatic scatter plot shows near-perfect collinearity across the full diameter range. The identity line and regression line are visually almost coincident. This demonstrates that the automatic system follows the same scaling as the manual method from small 1 mm ball impressions to large 10 mm ball impressions. The primary difference is a small positive offset rather than a nonlinear failure.

### En_all_methods.png

This plot shows E_n values for all Vickers, Micro-Vickers and Brinell series, with red lines at +/-1. Vickers and Brinell remain fully inside the acceptance interval. Micro-Vickers contains one point above +1, corresponding to the HV 1, 9.81 N, 50X series for SN 709-293. The figure demonstrates that the overall method comparison is satisfactory, with one localized Micro-Vickers exception.

### Micro-Vickers_ba_absolute_dimension.png

The Micro-Vickers absolute Bland-Altman plot has bias -0.057 um and limits of agreement from -0.602 to +0.489 um. Most differences are within about half a micrometre. Because Micro-Vickers diagonals range from about 21 um to 190 um, even sub-micrometre errors can have a visible effect on calculated hardness, especially at the smallest loads. The absence of a large systematic offset supports good dimensional agreement.

### Micro-Vickers_ba_log_ratio_dimension.png

The Micro-Vickers log-ratio plot shows mean log-ratio -0.001249 and limits from -0.011731 to +0.009233. The most negative points occur in the smaller-to-intermediate diagonal range. This suggests that relative error, not absolute error, is the relevant interpretation for microindentation. The trend is consistent with the known sensitivity of small indents to optical and boundary-definition errors.

### Micro-Vickers_ba_relative_percent_dimension.png

The Micro-Vickers relative Bland-Altman plot has bias -0.125% and limits from -1.173% to +0.923%. The result indicates sub-percent average agreement, with occasional differences approaching about +/-2%. This is scientifically acceptable for a comparison of optical diagonal readings, but the E_n outlier shows that one series-level hardness difference still exceeds its uncertainty allowance.

### Micro-Vickers_d1_d2_asymmetry.png

This plot compares manual and automatic d1-d2 asymmetry for Micro-Vickers. Most points cluster within approximately +/-1 um, with a positive association between manual and automatic asymmetry. This indicates that both methods often observe the same non-ideal indentation shape rather than independent random noise. Such asymmetry may arise from local surface condition, anisotropic plastic flow, imperfect focus, or difficulty identifying the true corner position. The available data do not identify which mechanism dominates.

### Micro-Vickers_deming_dimension.png

The Micro-Vickers Deming regression plot shows very strong linear agreement, with slope 1.002153 and intercept -0.204 um for lambda = 1. The confidence interval for the slope includes values very close to unity. This supports interchangeability of the dimensional readings over most of the Micro-Vickers range, while still allowing a localized series-level E_n exception.

### Micro-Vickers_difference_distribution.png

The paired-difference histogram is centred close to zero, with mean -0.057 um and a spread of about 0.278 um SD. The distribution is not dominated by a single extreme value. This supports the conclusion that the manual and automatic Micro-Vickers diagonal measurements are generally consistent at the individual indentation level.

### Micro-Vickers_En.png

The Micro-Vickers E_n plot shows one nonconforming point at E_n = +1.548. Positive E_n means the automatic hardness is higher than the manual hardness for that series. Since hardness is inversely related to diagonal length, this corresponds to the automatic method measuring a slightly smaller effective diagonal than the manual method for that series. The nonconformity should be investigated at the series level rather than interpreted as a general Micro-Vickers failure.

### Micro-Vickers_scatter_dimension.png

The scatter plot shows automatic and manual Micro-Vickers diagonals lying close to the identity line from about 20 um to 190 um. This confirms strong proportional agreement. The largest practical risk is not global calibration but local optical or operator-dependent corner definition at small indentation sizes.

### repeatability_comparison.png

This box plot compares within-series standard deviations by method and source. Brinell has the highest absolute repeatability scatter, especially for automatic measurements, while Vickers and Micro-Vickers have much smaller SD values. This is expected because Brinell impressions are much larger and their boundary is less sharply defined than Vickers corners. However, relative CV values remain modest, and the E_n results indicate that the reported uncertainties cover these effects.

### Vickers_ba_absolute_dimension.png

The Vickers absolute Bland-Altman plot shows bias -0.026 um with limits from -0.745 to +0.693 um. Points are tightly distributed around zero over a wide diagonal range, from approximately 78 um to 1069 um. This is strong evidence that the automatic Vickers diagonal measurement agrees with manual measurement across the tested hardness/load range.

### Vickers_ba_log_ratio_dimension.png

The Vickers log-ratio plot has mean -0.000290 and limits from -0.004655 to +0.004074. The small log-ratio confirms that proportional differences are very small. A few 50X points at small pair means show larger relative deviations, which is expected because small indentation diagonals amplify the relative effect of sub-micrometre reading differences.

### Vickers_ba_relative_percent_dimension.png

The Vickers relative Bland-Altman plot shows bias -0.029% and limits from -0.465% to +0.407%. This is the strongest relative agreement among the methods. The result supports the use of the automatic system for Vickers diagonal measurement in this dataset.

### Vickers_d1_d2_asymmetry.png

The Vickers d1-d2 asymmetry plot shows a clear relationship between manual and automatic asymmetry. Most points lie near zero, but a few small-load/small-diagonal points show larger negative asymmetry. This indicates that the two systems observe similar deviations from ideal square-pyramid geometry. Such deviations may arise from true indentation asymmetry, surface preparation, local microstructure, optical contrast or corner-selection differences. The data show the existence of asymmetry but do not identify its cause.

### Vickers_deming_dimension.png

The Vickers Deming regression plot has slope 1.000433 and intercept -0.198 um for individual dimensions. The line is almost identical to the identity line. This indicates no meaningful scale error between the manual and automatic Vickers dimensional systems.

### Vickers_difference_distribution.png

The Vickers paired-difference distribution is approximately centred at zero, with mean -0.026 um and SD 0.367 um. The distribution is fairly symmetric compared with Brinell. This supports absence of systematic Vickers dimensional bias.

### Vickers_En.png

All Vickers E_n points are between -1 and +1, with maximum |E_n| = 0.334. The series-level hardness agreement is therefore satisfactory for every Vickers series. This is the strongest metrological validation result in the analysis.

### Vickers_scatter_dimension.png

The Vickers scatter plot shows automatic and manual dimensions on the identity line over the full measured range. This visually confirms the Deming and Bland-Altman results. The automatic method reproduces the manual diagonal scale without evident curvature or load-dependent failure.

### Diagnostic indentation overlays

The diagnostic overlays show detected contours, corner order and calculated diagonals for the independent Python image routine. Reliable Vickers examples show contours aligned with the dark pyramidal indentation and diagonals crossing the expected corners. Rejected examples show either no suitable contour, contour selection at the wrong optical boundary, excessive Python/manual disagreement, or unstable Brinell boundary geometry. These overlays should be used as evidence of the limitations of the independent external image algorithm, not as evidence against the UME automatic measurements.

### Calibration overlays

The 20X and 50X stage-micrometer overlays show detected tick positions on the ruler scale. The 20X overlay identifies 11 ticks over a 100 um span, and the 50X overlay identifies 51 ticks over a 100 um span. The fitted scales are internally consistent. Their limitation is that they validate only the visible calibration orientation and do not quantify field distortion across the entire camera image.

## 4. Statistical and Measurement Analysis

The paired analyses, Bland-Altman plots and regression models answer different questions and should not be conflated. The paired mean difference estimates systematic offset. The standard deviation of paired differences estimates scatter in the difference between methods. The confidence interval around the bias estimates uncertainty in the mean bias, not the uncertainty of a single future measurement. The limits of agreement estimate the interval in which most individual method differences are expected to fall. Measurement uncertainty, as used in E_n, is a metrological quantity associated with reported series results and must not be replaced by the sample standard deviation alone [7-10,13].

The statistical evidence supports three main conclusions. First, Vickers dimensional agreement is excellent: bias -0.026 um, relative bias -0.029%, Deming slope 1.000433 and all |E_n| <= 1. Second, Micro-Vickers dimensional agreement is also strong on average, but one series exceeds the E_n criterion, indicating a localized measurement or uncertainty issue. Third, Brinell shows a statistically significant positive dimensional bias, but this bias is small in relative terms and all Brinell E_n values remain acceptable.

The repeatability results show that scatter increases in absolute micrometres with indentation size. Brinell therefore has larger SD values than Vickers or Micro-Vickers. However, this does not automatically mean that Brinell is less acceptable; the correct assessment must consider the measurement scale, the hardness equation, and the expanded uncertainty. The E_n results demonstrate that the Brinell differences are covered by the uncertainty budgets.

Surface preparation, edge clarity, indentation spacing, specimen thickness and distance from specimen edges are relevant to hardness testing, but the available dataset does not contain direct evidence for these factors. Therefore, they should be discussed as possible influences only, not as confirmed causes. The most defensible measurement-related explanations are optical boundary definition, magnification, indentation size, local heterogeneity and uncertainty coverage.

## 5. Comparison with Scientific Literature and Standards

The results are consistent with established hardness-testing principles. Hardness is an empirical indentation measure related to resistance to permanent deformation and plastic flow beneath the indenter. The large differences between serial-numbered blocks represent different hardness levels, not necessarily a single physical mechanism. Without metallography, chemical composition, heat treatment history or residual-stress measurements, it is not possible to attribute the hardness differences to grain size, phases, heat treatment, work hardening or residual stress.

The Vickers interpretation agrees with ISO 6507-1:2023 and ASTM E92. ISO 6507-1 specifies Vickers testing for diagonal lengths between 0.020 mm and 1.400 mm and warns that smaller indentations suffer from optical-measurement and tip-geometry limitations. The measured Vickers diagonals in this dataset, approximately 0.078 mm to 1.069 mm, are within that ISO range. ASTM E92 states that Vickers hardness should be essentially force-independent for homogeneous materials except at very low forces or very small indents. The observed Vickers agreement across HV 20, HV 50 and HV 100 is consistent with that principle.

The Micro-Vickers interpretation agrees with ASTM E384 and the indentation-size-effect literature. ASTM E384 emphasizes that microindentation is useful for small regions and hardness gradients, but it also notes that individual microindentation values may not represent bulk hardness and that very small indents are vulnerable to optical imprecision. Broitman's review of indentation hardness also explains that micro- and nanoscale hardness can be affected by indentation size effects, surface preparation, elastic recovery, pile-up and microstructural heterogeneity. In the present data, these mechanisms are possible contributors to the single Micro-Vickers E_n outlier, but they cannot be confirmed without additional physical evidence.

The Brinell interpretation agrees with ISO 6506-1 and ASTM E10. Brinell hardness is based on measuring the diameter of a ball indentation and calculating hardness from the contact geometry. Because the automatic system measured slightly larger diameters, the resulting Brinell hardness is slightly lower, exactly as expected from the Brinell equation. The relative difference remains modest and all E_n values pass.

The Knoop treatment agrees with ISO 4545-1 and ASTM E92. Knoop uses a long diagonal and is especially useful for gradients and thin/small regions, but the present workbook lacks paired automatic Knoop results. Therefore, no method-agreement conclusion is made for Knoop.

The E_n interpretation follows ISO 13528-style proficiency/statistical comparison logic, where |E_n| <= 1 indicates agreement within the combined expanded uncertainties. The general treatment of uncertainty follows the GUM principle that measurement uncertainty expresses the quality of a measurement result and must be evaluated from all relevant components, not only repeatability.

## 6. Discussion

The results support the conclusion that the UME automatic measurement system and manual measurement are mutually consistent for the primary Vickers and Brinell series and almost all Micro-Vickers series. The agreement is strongest for Vickers, where the self-similar diamond-pyramid geometry produces clear diagonal endpoints and very small relative method differences. Micro-Vickers remains highly consistent on average, but the smaller indentation dimensions increase the sensitivity to optical resolution, surface condition and corner selection. This explains why a single Micro-Vickers series can fail E_n even when the overall Micro-Vickers bias is small.

Brinell behaves differently because the measurement is based on a circular or near-circular boundary of a much larger ball impression. The automatic system tends to read the Brinell diameter slightly larger than the manual method. This may reflect different definitions of the transition between the deformed indentation boundary and the surrounding surface, or different sensitivity to contrast at the edge of the impression. Since all Brinell E_n values are within limits, the difference is metrologically acceptable in this dataset.

The independent image-analysis results should be presented carefully. They do not show that automatic measurement is impossible. They show that the external, unattended Python routine developed in this work is not equivalent to the UME automatic system. A validated instrument algorithm may use better-controlled illumination, calibrated optics, region-of-interest selection, edge-profile analysis, subpixel fitting and operator confirmation. The external routine used exported full-frame images and general contour detection. Therefore, its rejections are best interpreted as evidence that robust automatic hardness image measurement depends strongly on acquisition conditions, ROI selection and validated edge-detection rules.

Operator influence remains scientifically relevant. In manual and semi-automatic hardness measurement, the operator may influence focusing, illumination, selection of the measurement region, identification of corners or boundary points, and rejection of visually unsuitable detections. The strong agreement between manual and UME automatic values suggests that operator-guided or validated automatic measurement was effective. The failure of the independent full-frame routine highlights the same issue from another direction: without the correct region and edge definition, a generic algorithm can measure the wrong optical boundary.

The available results are insufficient to establish microstructural causes of the hardness levels. The data do not include composition, heat treatment, micrographs, grain size, phase identification, residual stress, edge distances, indentation spacing coordinates or specimen thickness. Therefore, mechanisms such as grain refinement, phase transformation, case hardening or work hardening should not be presented as confirmed explanations. They may be mentioned only as general factors that hardness testing can be sensitive to, not as conclusions from this dataset.

## 7. Key Findings

1. Vickers manual and automatic measurements agree very closely: mean dimensional bias -0.026 um, relative bias -0.029%, Deming slope 1.000433 and all 20 series with |E_n| <= 1.

2. Micro-Vickers shows strong average agreement: mean dimensional bias -0.057 um and relative bias -0.125%. One series, SN 709-293 at HV 1, has E_n = +1.548 and should be investigated.

3. Brinell shows a statistically significant positive automatic-minus-manual diameter bias of +11.893 um, but this corresponds to only +0.789% relative dimensional bias. All 12 Brinell series satisfy |E_n| <= 1.

4. Brinell automatic hardness is lower on average by 4.745 HBW because larger measured diameters produce lower calculated Brinell hardness.

5. Repeatability is best in relative terms for Vickers, somewhat more sensitive for Micro-Vickers, and largest in absolute micrometres for Brinell.

6. The calibration images provide reliable nominal 20X and 50X pixel scales, but do not quantify vertical scale error, field distortion or certified stage-micrometer uncertainty.

7. Knoop data are cleaned and documented but cannot support paired method comparison because automatic Knoop values are missing.

8. The external Python image routine is not a substitute for the validated UME automatic measurement system. Its image rejections should be described as limitations of unattended external remeasurement from exported BMP images, not as evidence that the UME system could not measure the indentations.

## 8. References

1. ISO 6507-1:2023. Metallic materials - Vickers hardness test - Part 1: Test method. International Organization for Standardization. https://www.iso.org/standard/83898.html

2. ISO 6506-1:2014. Metallic materials - Brinell hardness test - Part 1: Test method. International Organization for Standardization. https://www.iso.org/standard/59671.html

3. ISO 4545-1:2023. Metallic materials - Knoop hardness test - Part 1: Test method. International Organization for Standardization. https://www.iso.org/standard/83897.html

4. ASTM E10-23. Standard Test Method for Brinell Hardness of Metallic Materials. ASTM International. DOI: 10.1520/E0010-23. https://store.astm.org/standards/e10

5. ASTM E92-17. Standard Test Methods for Vickers Hardness and Knoop Hardness of Metallic Materials. ASTM International. DOI: 10.1520/E0092-17. https://store.astm.org/e0092-17.html

6. ASTM E384-17. Standard Test Method for Microindentation Hardness of Materials. ASTM International. DOI: 10.1520/E0384-17. https://store.astm.org/e0384-17.html

7. JCGM 100:2008. Evaluation of measurement data - Guide to the expression of uncertainty in measurement. DOI: 10.59161/JCGM100-2008E. https://www.bipm.org/en/doi/10.59161/jcgm100-2008e

8. ISO 13528:2022. Statistical methods for use in proficiency testing by interlaboratory comparison. International Organization for Standardization. https://www.iso.org/standard/78879.html

9. Bland, J. M., and Altman, D. G. 1986. Statistical methods for assessing agreement between two methods of clinical measurement. The Lancet 327(8476), 307-310. DOI: 10.1016/S0140-6736(86)90837-8.

10. Croarkin, C. M. 2003. NIST/SEMATECH Engineering Statistics Handbook, Chapter 2: Measurement Process Characterization. National Institute of Standards and Technology. https://www.nist.gov/publications/nistsematech-engineering-statistics-handbook-chapter-2-measurement-process

11. Broitman, E. 2017. Indentation Hardness Measurements at Macro-, Micro-, and Nanoscale: A Critical Overview. Tribology Letters 65, 23. DOI: 10.1007/s11249-016-0805-5.

12. Tabor, D. 1951/2000. The Hardness of Metals. Oxford University Press. DOI: 10.1093/oso/9780198507765.001.0001.

13. Linnet, K. 1993. Evaluation of regression procedures for methods comparison studies. Clinical Chemistry 39(3), 424-432. DOI: 10.1093/clinchem/39.3.424.
