# malaysian-trash-annotation > Build-20260418-x1
https://universe.roboflow.com/mta-cx7rs/malaysian-trash-annotation-lzf9c

Provided by a Roboflow user
License: CC BY 4.0

***Malaysian Trash Annotation (MTA)***


[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17862878.svg)](https://doi.org/10.5281/zenodo.17862878)

Check out the Github repository: [Main MTA Repository](https://github.com/lkaixian/malaysian-trash-annotation)

--- Acknowledgement ---
We thank all contributors for their support in data collection and annotation:
Daniel Looi Jun Jie, Darren Lau, Ice019, Ken, Kevin Tan, Kevin Tan Feng Sheng, Lim Li Hong, Nazzy, Ng Lee Pink, Tey KY, Trash, cyarah >~<

--- Introduction ---
Malaysian Trash Annotation or *MTA* in short is a localised instance segmentation dataset designed to address the current issue of waste segregation in Southeast Asia context. Compare with other openly-sourced dataset, *MTA* is heavily designed around real-world situation where it provides polygon masking to capture the exact geometry of the trash.

--- Publication ---
If you use our dataset, please cite us using:
> @dataset{mta2026,
  author = {Larm, K. X.},
  title = {Malaysian Trash Annotation (MTA)},
  year = {2026},
  doi = {10.5281/zenodo.17862878},
  url = {https://github.com/lkaixian/malaysian-trash-annotation}
}

--- Goal ---
To develop a high-accuracy waste segmentation model that can precisely localize objects with mainly account for real-world Malaysian environments.

--- Dataset's Version: Build 20260418 ---

* Classes: 14 (Material-based separation)
* Environment: Supermarkets (clean and ideal condition), Roadside (weathered), Food Courts (occluded/deformed).
* Hardware: Heterogeneous capture using 5 different devices (Oppo, Honor, Samsung, iPhone, Realme).
* Capture Protocol: Aspect Ratio locked at 4:3, Multi-angle (Top, Side, 45-degree) with no AI enhancements and no HDR enabled. 

Note 1:
> We overhaul the dataset's structure to now only support for material-based detection, should you split into 3 different segment in order to reach maximum accuracy of the purpose of detecting the recyclability of the trash, which are material-based, contamination-status, and object-based approach. 
> For more information, please refer to Singapore National Environment Agency guideline [here.](https://www.nea.gov.sg/docs/default-source/our-services/waste-management/list-of-items-that-are-recyclable-and-not.pdf)

Note 2: 
> Partial reference are taken from [Singapore National Environment Agency guideline](https://www.nea.gov.sg/docs/default-source/our-services/waste-management/list-of-items-that-are-recyclable-and-not.pdf) and from [Solid Waste Management and Public Cleansing Corperation (SWCorp) Malaysia](https://www.swcorp.gov.my/asingkan/)

--- Annotation Strategy ---

The dataset is currently structured for material-based detection (Phase 1), as below:
![SOP-Build-20260418](https://raw.githubusercontent.com/lkaixian/malaysian-trash-annotation/refs/heads/main/Recyclable%20Material-2026-04-19-082829.png)

Future extensions include:

Object-level classification
Contamination detection

This modular approach aligns with practical waste classification systems.

--- Taxonomy of dataset ---
m-* (Main Category)
m-composite , refer to such trash has composite material with it 
m-glass , refer to such trash is mainly made out of glass
m-metal , refer to such trash is mainly made out of metal
m-paper , refer to such trash is mainly made out of paper
m-plastic-film , refer to such trash is mainly made out of soft plastic
m-plastic-rigid , refer to such trash is mainly made out of hard plastic 

s-* (Special Category)
s-e-waste , refer to such trash is e-waste
s-hazardous , refer to such trash is e-waste
s-ikat-tepi , refer to such trash is ikat tepi
s-litter , refer to such trash is common trash and can't be recycle whatsoever
s-organic , refer to such trash is organic waste
s-other , refer to such trash can't be categorized or too little to become its own class
s-textile , refer to such trash is made out of textile
s-cigarette-butt , refer to such trash is cigarette butt

--- Devices ---
* Oppo Reno 14 MY Version (OppoReno14)
* Samsung Note 10 MY Version (SamsungNote10)
* Iphone 11 MY Version (Iphone11)
* Honor 200 MY Version (Honor200)
* Realme 5s MY Version (Realme5s)

--- References ---
Singapore National Environment Agency (NEA):
https://www.nea.gov.sg/docs/default-source/our-services/waste-management/list-of-items-that-are-recyclable-and-not.pdf
SWCorp Malaysia:
https://www.swcorp.gov.my/asingkan/

--- Legal & Disclaimer ---
This dataset contains real-world images of public environments. Any trademarks, logos, or brand names visible on objects (e.g., packaging, bottles) are the property of their respective owners.

Such elements are captured incidentally as part of natural scenes and are included solely for research, educational, and computer vision development purposes. The authors do not claim ownership of any third-party trademarks, nor does their inclusion imply any affiliation with or endorsement by the respective rights holders.

The dataset is provided “as is” without warranties, and the authors are not responsible for any misuse of the data.

Notes: 
* Reflections: Contains samples on glass/steel tables; polygons are tightly cropped to the object, excluding ghost reflections.
* Deformation: Includes crushed cans and flattened bottles to simulate end-of-life object states.
* Localization: Features "Ikat Tepi" and "Keropok" wrappers specific to the Malaysian region.

