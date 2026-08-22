import os
import logging
from collections import defaultdict

from astropy.io import fits
from astropy import units as u

logging.basicConfig(level=logging.DEBUG, format="%(filename)s: %(levelname)8s %(message)s")
log = logging.getLogger('ifcube')
log.setLevel(logging.WARNING)


SPECTRAL_COORD_TYPE_CODES = ["WAVE", "FREQ", "ENER", "WAVN", "VRAD", "VOPT", "ZOPT", "AWAV", "VELO", "BETA"]
NON_LINEAR_ALGORITHM_CODES = ["F2W", "F2V", "F2A", "W2F", "W2V", "W2A", "V2F", "V2W", "V2A", "A2F", "A2W", "A2V", \
                              "LOG", "GRI", "GRA", "TAB"]

COORD_TYPES = ["RA", "DEC", "GLON", "GLAT", "ELON", "ELAT", "SELN"]
PROJECTIONS = ["AZP", "SZP", "TAN", "STG", "SIN", "ARC", "ZPN", "ZEA", "AIR", "CYP", "CEA", "CAR", "MER", "SFL", \
               "PAR", "MOL", "AIT", "COP", "COE", "COD", "COO", "BON", "PCO", "CSC", "TSC", "QCS", "HPX", "XPH", \
               "TPV", "TUV"]


class IFUCube(object):
    """
    Check and correct the IFUCube
    """
    def __init__(self):
        self._fits = None
        self._filename = None
        self._good = True
        self._log_text = defaultdict(lambda: dict())

        self._units = [u.m, u.cm, u.mm, u.um, u.nm, u.AA]
        self._units_titles = list(x.name for x in self._units)

    def open(self, filename, fix=False):
        """
        Check all checkers
        """
        self._filename = filename

        log.debug('In check with filename {} and fix {}'.format(filename, fix))

        # Check existence of the file
        if not os.path.isfile(filename):
            log.warning('File {} does not exist'.format(filename))
            return
        else:
            log.info('File {} exists'.format(filename))

        # Open the file
        try:
            self._fits = fits.open(filename)
        except:
            log.warning('Could not open {} '.format(filename))
            return

        self.check(fix)

        return self._fits

    def check(self, fix=False):
        """
        Check all checkers
        """
        log.debug('In check with filename {} and fix {}'.format(self._filename, fix))
        self._log_text['>front'] = 'Checking filename {}\n'.format(self._filename)

        self.check_data(fix)

        self.check_ctype1(fix)

        self.check_ctype2(fix)

        self.check_ctype3(fix)

        self.check_cunit1(fix)

        self.check_cunit2(fix)

        self.check_cunit3(fix)

        return self._fits

    def check_data(self, fix=False):
        """
        Check CTYPE and make sure it is the correct value

        :param: fits_file: The open fits file
        :param: fix: boolean whether to fix it or not
        :return: boolean whether it is good or not
        """
        log.debug('In check_data')
        good = False
        data_shape = []

        for ii, hdu in enumerate(self._fits):

            # Check the EXTNAME field for this HDU
            if 'EXTNAME' not in self._fits[ii].header:
                log.warning(' HDU {} has no EXTNAME field'.format(ii))
                extname = '{}_{}'.format(self._filename, ii)
                if fix:
                    self._fits[ii].header['EXTNAME'] = extname
                    log.info(' Setting HDU {} EXTNAME field to {}'.format(ii, extname))
                    self._log_text[hdu.name]['data'] = 'Setting HDU {} EXTNAME field to {}\n'.format(ii, extname)
            else:
                extname = self._fits[ii].header['EXTNAME']

            if hasattr(hdu, 'data') and hdu.data is not None and len(hdu.data.shape) == 3:
                good = True
                self.good_check(good)

                log.info('  data exists in HDU ({}, {}) and is of shape {}'.format(
                    ii, extname, hdu.data.shape))

                # Check to see if the same size as the others
                if data_shape and not data_shape == hdu.data.shape:
                    log.warning('  Data are of different shapes (previous was {} and this is {})'.format(data_shape,
                                                                                                         hdu.data.shape))

                data_shape = hdu.data.shape

        if not good:
            self.good_check(False)
            log.error('  Can\'t fix lack of data')
            return False

        return good

    def check_ctype1(self, fix=False):
        # The zeroth index of each 'correct' array should contain the default value
        all_valid_ctype1s = ['RA---TAN'] + ['{}{}{}'.format(c, (8-len(a)-len(c))*'-', a) for c in COORD_TYPES for a in PROJECTIONS]
        self._check_ctype(key='CTYPE1', correct=all_valid_ctype1s, fix=fix)

    def check_ctype2(self, fix=False):
        # The zeroth index of each 'correct' array should contain the default value
        all_valid_ctype2s = ['DEC--TAN'] + ['{}{}{}'.format(c, (8-len(a)-len(c))*'-', a) for c in COORD_TYPES for a in PROJECTIONS]
        self._check_ctype(key='CTYPE2', correct=all_valid_ctype2s, fix=fix)

    def check_ctype3(self, fix=False):
        # The zeroth index of each 'correct' array should contain the default value (S_C_T_C[0] == '[WAVE]')
        all_valid_ctype3s = SPECTRAL_COORD_TYPE_CODES + ['{}{}{}'.format(c, (8-len(a)-len(c))*'-', a) for c in SPECTRAL_COORD_TYPE_CODES for a in NON_LINEAR_ALGORITHM_CODES]
        self._check_ctype(key='CTYPE3', correct=all_valid_ctype3s, fix=fix)

    def check_cunit1(self, fix=False):
        self._check_ctype(key='CUNIT1', correct='deg', fix=fix)

    def check_cunit2(self, fix=False):
        self._check_ctype(key='CUNIT2', correct='deg', fix=fix)

    def check_cunit3(self, fix=False):
        self._check_ctype(key='CUNIT3', correct=self._units_titles, fix=fix)

    def _check_ctype(self, key, correct, fix=False):
        """
        Check the header key and make sure it is the correct value

        :param: fits_file: The open fits file
        :param: fix: boolean whether to fix it or not
        :return: boolean whether it is good or not
        """
        log.debug('In check for {}'.format(key))

        # Creates a list of tuples (originals only), which have the shape: (hdu.header[key], if hdu has 3D data)
        all_hdu_values = list(set([(hdu.header[key], (hasattr(hdu, 'data') and hdu.data is not None and\
                                              len(hdu.data.shape) == 3)) for hdu in self._fits if hasattr(hdu, "header") and key in hdu.header]))

        # Sort by has_data and now you have the hdu.header[key] values which have corresponding data in the first (or
        # first few) indices
        all_hdu_values.sort(key=lambda tup: tup[1], reverse=True)
        log.debug("All hdu values for {}: {}".format(key, all_hdu_values))

        # Check if any of of the hdu.header[key] values are in correct
        all_correct_values = [value for value, has_data in all_hdu_values if value in correct]
        log.debug("All correct values: {}".format(all_correct_values))

        # If there are more than one correct hdu.header[key] values that have corresponding 3D data, use the first one
        correct = all_correct_values[0] if len(all_correct_values) > 0 else correct
        log.debug("Correct value(s) to be used: {}".format(correct))

        for ii, hdu in enumerate(self._fits):
            if ii == 0 or (hasattr(hdu, 'data') and hdu.data is not None and len(hdu.data.shape) == 3):
                if key not in hdu.header:
                    hdu.header[key] = "NONE"
                    self._good_and_fix(hdu, key, correct, fix, ii)
                else:
                    self._good_and_fix(hdu, key, correct, fix, ii)

    def _good_and_fix(self, hdu, key, correct, fix, ii):
        """
        Does as the name implies, checks to see if the hdu.header[key] equals the correct value, if it does not
        and fix is True, the correct value is inserted and passed back to CubeViz
        :param hdu: One of the headers from the original FITS file
        :param key: The header keyword to be checked
        :param correct: The correct value of the header keyword
        :param fix: Whether or not to fix the header to the correct value
        :param ii: The index of the hdu within the FITS file
        :return:
        """
        # (i.e. Angstroms instead of Angstrom will be corrected and added)
        if hdu.header[key] not in correct and len(hdu.header[key]) > 0 and hdu.header[key][:-1] in correct:
            self.good_check(False)
            self._log_text[hdu.name][key] = "{} is {}, setting to {}\n".format(key, hdu.header[key], hdu.header[key][:-1])
            log.info("{} is {}, setting to {} in header[{}]".format(key, hdu.header[key], hdu.header[key][:-1], ii))
            hdu.header[key] = hdu.header[key][:-1]

        elif not hdu.header[key] in correct and fix:
            self.good_check(False)
            if isinstance(correct, list):
                self._log_text[hdu.name][key] = "{} is {}, setting to {}\n".format(key, hdu.header[key], correct[0])
                log.info("{} is {}, setting to {} in header[{}]".format(key, hdu.header[key], correct[0], ii))
                hdu.header[key] = correct[0]
            else:
                self._log_text[hdu.name][key] = "{} is {}, setting to {}\n".format(key, hdu.header[key], correct)
                log.info("{} is {}, setting to {} in header[{}]".format(key, hdu.header[key], correct, ii))
                hdu.header[key] = correct

        elif not hdu.header[key] in correct and not fix:
            if isinstance(correct, list):
                self.good_check(False)
                log.info("{} is {}, should equal {} in header[{}]".format(key, hdu.header[key], correct[0], ii))
                self._log_text[hdu.name][key] = "{} is {}, should equal {}".format(key, hdu.header[key], correct[0])
            else:
                self.good_check(False)
                log.info("{} is {}, should equal {} in header[{}]".format(key, hdu.header[key], correct, ii))
                self._log_text[hdu.name][key] = "{} is {}, should equal {}".format(key, hdu.header[key], correct)

    def get_log_output(self):

        output = self._log_text['>front'] + '\n'

        for log_key, log_value in sorted(self._log_text.items()):
            if log_key == '>front':
                continue

            output += 'HDU {}\n'.format(log_key)

            if isinstance(log_value, str):
                output += '    {}'.format(log_value)
                continue

            for _, log_line in sorted(log_value.items()):
                output += '    {}'.format(log_line)

            output += '\n'

        return output

    def good_check(self, good):
        if good and self._good:
            self._good = True
        if not good:
            self._good = False

    def get_good(self):
        return self._good

    def get_fits(self):
        return self._fits
