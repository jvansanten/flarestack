import os
import numpy as np
import sys
from config import scratch_path
from shared import fs_scratch_dir, input_dir, storage_dir, output_dir, \
    log_dir, catalogue_dir, acc_f_dir, pickle_dir, plots_dir, skylab_ref_dir,\
    SoB_spline_dir, analysis_dir, dataset_dir, illustration_dir,\
    transients_dir, bkg_spline_dir
from utils.prepare_catalogue import make_single_sources
from utils.create_acceptance_functions import make_acceptance_f
from utils.reference_sensitivity import download_ref
from utils.make_SoB_splines import make_spline

from data.icecube_gfu_v002_p02 import txs_sample_v2
from data.icecube_northern_tracks_v002_p01 import diffuse_8year

all_data = txs_sample_v2 + diffuse_8year

if __name__ == "__main__":
    print "\n \n"
    print "********************************************************************"
    print "*                                                                  *"
    print "*                Initialising setup for FlareStack                 *"
    print "*                                                                  *"
    print "********************************************************************"
    print "\n"
    print "  Initialising directory for data storage. This could be a scratch  "
    print "                   space or local directory.                        "
    print "\n"

    print "The following parent directory has been found in config.py: \n"
    print "\t", scratch_path
    print
    print "A new data storage directory will be created at: \n"
    print "\t", fs_scratch_dir
    print
    print "Is this correct? (y/n)"

    x = ""

    while x not in ["y", "n"]:
        x = raw_input("")

    if x == "n":
        print "\n"
        print "Please edit config.py to include the correct directory!"
        print "\n"
        sys.exit()

    for dir in [input_dir, storage_dir, output_dir, log_dir, catalogue_dir,
                acc_f_dir, pickle_dir, plots_dir, skylab_ref_dir, livetime_dir,
                SoB_spline_dir, analysis_dir, dataset_dir, illustration_dir,
                transients_dir, bkg_spline_dir]:
        if not os.path.isdir(dir):
            print "Making Directory:", dir
            os.makedirs(dir)
        else:
            print "Found Directory:", dir

    print "\n"
    print "********************************************************************"
    print "*                                                                  *"
    print "*                 Initialising catalogue creation                  *"
    print "*                                                                  *"
    print "********************************************************************"
    print "\n"
    make_single_sources()

    # Check to ensure there is at least one IceCube dataset present

    x = np.sum([os.path.isdir(os.path.dirname(y["mc_path"])) for y in all_data])

    print "********************************************************************"
    print "*                                                                  *"
    print "*                     Checking data directories                    *"
    print "*                                                                  *"
    print "********************************************************************"

    if x == 0:
        print "No IceCube data files found. Tried searching for: \n"
        for y in all_data:
            print "\t", os.path.dirname(y["mc_path"])

        print ""
        print "Download these data files yourself, and save them to: \n"
        print "\t", dataset_dir
        print "\n"
        sys.exit()

    else:
        print "Searched for the following directories: \n"
        for y in all_data:
            print "\t", os.path.dirname(y["mc_path"]),
            print "Found?", os.path.isdir(os.path.dirname(y["mc_path"]))


    print "\n"
    print "********************************************************************"
    print "*                                                                  *"
    print "*                   Making Acceptance Functions                    *"
    print "*                                                                  *"
    print "********************************************************************"
    print "\n"
    make_acceptance_f(all_data)

    print "\n"
    print "********************************************************************"
    print "*                                                                  *"
    print "*    Creating Log(Energy) vs. Sin(Declination) Sig/Bkg splines     *"
    print "*                                                                  *"
    print "********************************************************************"
    print "\n"
    make_spline(all_data)

    print "\n"
    print "********************************************************************"
    print "*                                                                  *"
    print "*      Downloading Reference Point Source Sensitivity (Skylab)     *"
    print "*                                                                  *"
    print "********************************************************************"
    print "\n"
    download_ref()
