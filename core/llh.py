import numexpr
import astro
import numpy as np
import scipy.interpolate
from signal_over_background import SoB
from energy_PDFs import EnergyPDF
from time_PDFs import TimePDF


class LLH(SoB):
    """General  LLH class.
    """

    def __init__(self, season, sources, **kwargs):
        print "Initialising LLH for", season["Name"]
        SoB.__init__(self, season, **kwargs)
        self.sources = sources
        # self.mc_weights = self.energy_pdf.weight_mc(self._mc)

        # If a time PDF is to be used, a dictionary must be provided in kwargs
        time_dict = kwargs["LLH Time PDF"]
        if time_dict is not None:
            self.time_pdf = TimePDF.create(time_dict, season)

        self.acceptance_f = self.create_acceptance_function()

    def create_acceptance_function(self):
        """Creates a 2D linear interpolation of the acceptance of the detector
        for the given season, as a function of declination and gamma. Returns
        this interpolation function.

        :return: 2D linear interpolation
        """
        dec_bins = np.load(
            self.season['aw_path'] + '_bins_dec.npy')
        gamma_bins = np.load(
            self.season['aw_path'] + '_bins_gamma.npy')
        values = np.load(self.season['aw_path'] + '_values.npy')
        f = scipy.interpolate.interp2d(
            dec_bins, gamma_bins, values, kind='linear')
        return f

    def acceptance(self, source, params):
        """Calculates the detector acceptance for a given source, using the
        2D interpolation of the acceptance as a function of declination and
        gamma. If gamma IS NOT being fit, uses the default value of gamma for
        weighting (determined in __init__). If gamma IS being fit, it will be
        the last entry in the parameter array, and is the acceptance uses
        this value.

        :param source: Source to be considered
        :param params: Parameter array
        :return: Value for the acceptance of the detector, in the given
        season, for the source
        """
        dec = source["dec"]
        if not self.fit_gamma:
            gamma = self.default_gamma
        else:
            gamma = params[-1]

        return self.acceptance_f(dec, gamma)

    def select_coincident_data(self, data, sources):
        """Checks each source, and only identifies events in data which are
        both spatially and time-coincident with the source. Spatial
        coincidence is defined as a +/- 5 degree box centered on the  given
        source. Time coincidence is determined by the parameters of the LLH
        Time PDF. Produces a mask for the dataset, which removes all events
        which are not coincident with at least one source.

        :param data: Dataset to be tested
        :param sources: Sources to be tested
        :return: Mask to remove
        """
        veto = np.ones_like(data["timeMJD"], dtype=np.bool)

        for source in sources:
            if hasattr(self, "time_pdf"):

                # Sets time mask, based on parameters for LLH Time PDF
                start_time, end_time = self.time_pdf.flare_time_mask(source)
                time_mask = np.logical_and(
                    np.greater(data["timeMJD"], start_time),
                    np.less(data["timeMJD"], end_time)
                )

            else:
                time_mask = np.ones_like(data["timeMJD"], dtype=np.bool)

            # Sets half width of spatial box
            width = np.deg2rad(5.)

            # Sets a declination band 5 degrees above and below the source
            min_dec = max(-np.pi / 2., source['dec'] - width)
            max_dec = min(np.pi / 2., source['dec'] + width)

            # Accepts events lying within a 5 degree band of the source
            dec_mask = np.logical_and(np.greater(data["dec"], min_dec),
                                      np.less(data["dec"], max_dec))

            # Sets the minimum value of cos(dec)
            cos_factor = np.amin(np.cos([min_dec, max_dec]))

            # Scales the width of the box in ra, to give a roughly constant
            # area. However, if the width would have to be greater that +/- pi,
            # then sets the area to be exactly 2 pi.
            dPhi = np.amin([2. * np.pi, 2. * width / cos_factor])

            # Accounts for wrapping effects at ra=0, calculates the distance
            # of each event to the source.
            ra_dist = np.fabs(
                (data["ra"] - source['ra'] + np.pi) % (2. * np.pi) - np.pi)
            ra_mask = ra_dist < dPhi / 2.

            spatial_mask = dec_mask & ra_mask
            coincident_mask = spatial_mask & time_mask

            veto = veto & ~coincident_mask

        # print "Of", len(data), "total events, we consider", np.sum(~veto), \
        #     "events which are coincident with the sources."
        return ~veto

    def create_llh_function(self, data):
        mask = self.select_coincident_data(data, self.sources)

        coincident_data = data[mask]

        n_mask = np.sum(mask)
        n_all = len(data)
        n_sources = len(self.sources)
        
        SoB_spacetime = np.zeros_like(np.zeros([n_sources, n_mask]))

        for i, source in enumerate(self.sources):
            sig = self.signal_pdf(source, coincident_data)
            bkg = self.background_pdf(source, coincident_data)
            SoB_spacetime[i] = sig/bkg
            del sig
            del bkg

        # If an llh energy PDF has been provided, calculate the SoB values
        # for the coincident data, and stores it in a cache.
        if hasattr(self, "energy_pdf"):
            SoB_energy_cache = self.create_SoB_energy_cache(coincident_data)

            # If gamma is not going to be fit, replaces the SoB energy
            # cache with the weight array corresponding to the gamma provided
            # in the llh energy PDF
            if not self.fit_gamma:
                SoB_energy_cache = self.estimate_energy_weights(
                    self.default_gamma, SoB_energy_cache)

        # Otherwise, pass no energy weight information
        else:
            SoB_energy_cache = None

        def test_statistic(params, weights):
            return self.calculate_test_statistic(
                params, weights, n_mask, n_all, SoB_spacetime,
                SoB_energy_cache)

        return test_statistic

    def calculate_test_statistic(self, params, weights, n_mask,
                                 n_all, SoB_spacetime,
                                 SoB_energy_cache=None):
        """Calculates the test statistic, given the parameters. Uses numexpr
        for faster calculations.

        :param params: Parameters from minimisation
        :return: Test Statistic
        """

        # If fitting gamma and calculates the energy weights for the given
        # value of gamma
        if self.fit_gamma:
            n_s = np.array(params[:-1])
            gamma = params[-1]
            SoB_energy = self.estimate_energy_weights(gamma, SoB_energy_cache)

        # If using energy information but with a fixed value of gamma,
        # sets the weights as equal to those for the provided gamma value.
        elif SoB_energy_cache is not None:
            n_s = np.array(params)
            SoB_energy = SoB_energy_cache

        # If not using energy information, assigns a weight of 1. to each event
        else:
            n_s = np.array(params)
            SoB_energy = 1.

        # Calculates the expected number of signal events for each source in
        # the season
        all_n_j = n_s * weights
        
        # Evaluate the likelihood function for neutrinos close to each source
        llh_value = np.sum(np.log1p(
            all_n_j * ((SoB_energy * SoB_spacetime) - 1)/n_all))

        # Account for the events in the veto region, by assuming they have S/B=0
        llh_value += np.sum((n_all - n_mask) * np.log1p(-all_n_j / n_all))

        # Definition of test statistic
        return 2. * llh_value

# ==============================================================================
# Signal PDF
# ==============================================================================

    def signal_pdf(self, source, cut_data):
        """Calculates the value of the signal spatial PDF for a given source
        for each event in the coincident data subsample. If there is a Time PDF
        given, also calculates the value of the signal Time PDF for each event.
        Returns either the signal spatial PDF values, or the product of the
        signal spatial and time PDFs.

        :param source: Source to be considered
        :param cut_data: Subset of Dataset with coincident events
        :return: Array of Signal Spacetime PDF values
        """
        space_term = self.signal_spatial(source, cut_data)

        if hasattr(self, "time_pdf"):
            time_term = self.time_pdf.signal_f(cut_data["timeMJD"], source)
            sig_pdf = space_term * time_term

        else:
            sig_pdf = space_term

        return sig_pdf

    def signal_spatial(self, source, cut_data):
        """Calculates the angular distance between the source and the
        coincident dataset. Uses a Gaussian PDF function, centered on the
        source. Returns the value of the Gaussian at the given distances.

        :param source: Single Source
        :param cut_data: Subset of Dataset with coincident events
        :return: Array of Spatial PDF values
        """
        distance = astro.angular_distance(
            cut_data['ra'], cut_data['dec'], source['ra'], source['dec'])
        space_term = (1. / (2. * np.pi * cut_data['sigma'] ** 2.) *
                      np.exp(-0.5 * (distance / cut_data['sigma']) ** 2.))
        return space_term

# ==============================================================================
# Background PDF
# ==============================================================================

    def background_pdf(self, source, cut_data):
        """Calculates the value of the background spatial PDF for a given
        source for each event in the coincident data subsample. Thus is done
        by calling the self.bkg_spline spline function, which was fitted to
        the Sin(Declination) distribution of the data.

        If there is a signal Time PDF given, then the background time PDF
        is also calculated for each event. This is assumed to be a normalised
        uniform distribution for the season.

        Returns either the background spatial PDF values, or the product of the
        background spatial and time PDFs.

        :param source: Source to be considered
        :param cut_data: Subset of Dataset with coincident events
        :return: Array of Background Spacetime PDF values
        """
        space_term = (1. / (2. * np.pi)) * np.exp(
            self.bkg_spatial(cut_data["sinDec"]))

        if hasattr(self, "time_pdf"):
            time_term = self.time_pdf.background_f(cut_data["timeMJD"], source)
            sig_pdf = space_term * time_term
        else:
            sig_pdf = space_term

        return sig_pdf

# ==============================================================================
# Energy Log(Signal/Background) Ratio
# ==============================================================================

    def create_SoB_energy_cache(self, cut_data):
        """Evaluates the Log(Signal/Background) values for all coincident
        data. For each value of gamma in self.gamma_support_points, calculates
        the Log(Signal/Background) values for the coincident data. Then saves
        each weight array to a dictionary.

        :param cut_data: Subset of the data containing only coincident events
        :return: Dictionary containing SoB values for each event for each
        gamma value.
        """
        energy_SoB_cache = dict()

        for gamma in self.SoB_spline_2Ds.keys():
            energy_SoB_cache[gamma] = self.SoB_spline_2Ds[gamma].ev(
                cut_data["logE"], cut_data["sinDec"])

        return energy_SoB_cache

    def estimate_energy_weights(self, gamma, energy_SoB_cache):
        """Quickly estimates the value of Signal/Background for Gamma.
        Uses pre-calculated values for first and second derivatives.
        Uses a Taylor series to estimate S(gamma), unless SoB has already
        been calculated for a given gamma.

        :param gamma: Spectral Index
        :param energy_SoB_cache: Weight cache
        :return: Estimated value for S(gamma)
        """
        if gamma in energy_SoB_cache.keys():
            val = np.exp(energy_SoB_cache[gamma])
        else:
            g1 = self._around(gamma)
            dg = self.precision

            g0 = self._around(g1 - dg)
            g2 = self._around(g1 + dg)

            # Uses Numexpr to quickly estimate S(gamma)
            S0 = energy_SoB_cache[g0]
            S1 = energy_SoB_cache[g1]
            S2 = energy_SoB_cache[g2]

            val = numexpr.evaluate(
                "exp((S0 - 2.*S1 + S2) / (2. * dg**2) * (gamma - g1)**2" + \
                " + (S2 -S0) / (2. * dg) * (gamma - g1) + S1)"
            )

        return val