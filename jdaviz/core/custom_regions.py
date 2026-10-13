import operator

from specutils import SpectralRegion, CompoundSpectralRegion

class RangeRegion(SpectralRegion):
    '''
    This class just wraps `~specutils.SpectralRegion` so that we can use its
    machinery (which is mostly unit agnostic) for general range regions without
    confusing the user by returning something with "Spectral" in the name.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _info(self):
        info_str = super()._info()
        return info_str.replace('Spectral', 'Range')

    def __add__(self, other):
        """
        Ability to add two RangeRegion classes together.
        """
        return RangeRegion(self._subregions + other._subregions)

    def __getslice__(self, item):
        """
        Enable slicing of the RangeRegion list.
        """
        return RangeRegion(self._subregions[item])

    def __getitem__(self, item):
        """
        Enable slicing or extracting the RangeRegion.
        """
        if isinstance(item, slice):
            return self.__getslice__(item)
        else:
            return RangeRegion([self._subregions[item]])

    def intersection(self, other):
        """
        Return a region representing the intersection of this region
        with ``other``.

        Parameters
        ----------
        other : `~specutils.SpectralRegion`
            The other region to use for the intersection.
        """
        return CompoundRangeRegion(region1=self, region2=other,
                                   op=operator.and_)

    def symmetric_difference(self, other):
        """
        Return the union of the two regions minus any areas contained in
        the intersection of the two regions.

        Parameters
        ----------
        other : `~specutils.SpectralRegion`
            The other region to use for the symmetric difference.
        """
        return CompoundRangeRegion(region1=self, region2=other,
                                   op=operator.xor)

    def union(self, other):
        """
        Return a region representing the union of this region with
        ``other``.

        Parameters
        ----------
        other : `~specutils.SpectralRegion`
            The other region to use for the union.
        """
        return CompoundRangeRegion(region1=self, region2=other,
                                   op=operator.or_)


class CompoundRangeRegion(CompoundSpectralRegion):
    def __init__(*args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_subregions(self):
        # Turn the SpectralRegion returned by super() into a RangeRegion
        return RangeRegion(super().to_subregions(self)._subregions)