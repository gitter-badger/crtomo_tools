# *-* coding: utf-8 *-*
"""Manage measurement configurations and corresponding measurements.

Literature
----------

* Noel, Mark and Biwen Xu; Archaeological investigation by electrical
    resistivity tomography: a preliminary study. Geophys J Int 1991; 107 (1):
    95-102. doi: 10.1111/j.1365-246X.1991.tb01159.x
* Stummer, Peter, Hansruedi Maurer, and Alan G. Green. “Experimental Design:
  Electrical Resistivity Data Sets That Provide Optimum Subsurface
  Information.” Geophysics 69, no. 1 (January 1, 2004): 120–120.
  doi:10.1190/1.1649381.

"""
import itertools
from crtomo.mpl_setup import *
import scipy.interpolate as si

import numpy as np
import edf.utils.filter_config_types as fT


class ConfigManager(object):
    """The class`ConfigManager` manages four-point measurement configurations.
    Measurements can be saved/loaded from CRMod/CRTomo files, and new
    configurations can be created.
    """

    def __init__(self, nr_of_electrodes=None):
        # store the configs as a Nx4 numpy array
        self.configs = None
        # store measurements in a list of size N arrays
        self.measurements = {}
        # each measurement can store additional data here
        self.metadata = {}
        # global counter for measurements
        self.meas_counter = - 1
        # number of electrodes
        self.nr_electrodes = nr_of_electrodes

    def _get_next_index(self):
        self.meas_counter += 1
        return self.meas_counter

    @property
    def nr_of_configs(self):
        """Return number of configurations

        Returns
        -------
        nr_of_configs: int
            number of configurations stored in this instance

        """
        if self.configs is None:
            return 0
        else:
            return self.configs.shape[0]

    def add_noise(self, cid, **kwargs):
        """Add noise to a data set and return a new cid for the noised data.

        Parameters
        ----------
        cid: int
            ID for the data set to add noise to
        positive: bool
            if True, then set measurements to np.nan that are negative
        seed: int, optional
            set the seed used to initialize the random number generator
        relative: float
            standard deviation of error
        absolute: float
            mean value of normal distribution


        Returns
        -------
        cid_noise: int
            ID pointing to noised data set

        """
        pass

    def add_measurements(self, measurements):
        """Add new measurements to this instance

        Parameters
        ----------
        measurements: numpy.ndarray
            one or more measurement sets. It must either be 1D or 2D, with the
            first dimension the number of measurement sets (K), and the second
            the number of measurements (N): K x N

        Returns
        -------
        mid: int
            measurement ID used to extract the measurements later on

        Examples
        --------
        >>> import numpy as np
            import crtomo.configManager as CRconfig
            config = CRconfig.ConfigManager(nr_of_electrodes=10)
            config.gen_dipole_dipole(skipc=0)
            # generate some random noise
            random_measurements = np.random.random(config.nr_of_configs)
            mid = config.add_measurements(random_measurements)
            # retrieve using mid
            print(config.measurements[mid])

        """
        subdata = np.atleast_2d(measurements)

        if self.configs is None:
            raise Exception(
                'must read in configuration before measurements can be stored'
            )

        # we try to accommodate transposed input
        if subdata.shape[1] != self.configs.shape[0]:
            if subdata.shape[0] == self.configs.shape[0]:
                subdata = subdata.T
            else:
                raise Exception(
                    'Number of measurements does not match number of configs'
                )

        return_ids = []
        for dataset in subdata:
            cid = self._get_next_index()
            self.measurements[cid] = dataset.copy()
            return_ids.append(cid)

        if len(return_ids) == 1:
            return return_ids[0]
        else:
            return return_ids

    def _crmod_to_abmn(self, configs):
        """convert crmod-style configurations to a Nx4 array

        CRMod-style configurations merge A and B, and M and N, electrode
        numbers into one large integer each:

        .. math ::

            AB = A \cdot 10^4 + B\\
            MN = M \cdot 10^4 + N

        Parameters
        ----------
        configs: numpy.ndarray
            Nx2 array holding the configurations to convert

        Examples
        --------

        >>> import numpy as np
            import crtomo.configManager as CRconfig
            config = CRconfig.ConfigManager(nr_of_electrodes=5)
            # generate some CRMod-style configurations
            crmod_configs = np.array((
                (10002, 40003),
                (10010, 30004),
            ))
            abmn = config._crmod_to_abmn(crmod_configs)
            print(abmn)
        [[  2.   1.   3.   4.]
         [ 10.   1.   4.   3.]]

        """
        A = configs[:, 0] % 1e4
        B = np.floor(configs[:, 0] / 1e4).astype(int)
        M = configs[:, 1] % 1e4
        N = np.floor(configs[:, 1] / 1e4).astype(int)
        ABMN = np.hstack((
            A[:, np.newaxis],
            B[:, np.newaxis],
            M[:, np.newaxis],
            N[:, np.newaxis]
        ))
        return ABMN

    def load_crmod_config(self, filename):
        """Load a CRMod configuration file

        Parameters
        ----------
        filename: string
            absolute or relative path to a crmod config.dat file

        """
        with open(filename, 'r') as fid:
            nr_of_configs = int(fid.readline().strip())
            configs = np.loadtxt(fid)
            print('loaded configs:', configs.shape)
            if nr_of_configs != configs.shape[0]:
                raise Exception(
                    'indicated number of measurements does not equal ' +
                    'to actual number of measurements'
                )
            ABMN = self._crmod_to_abmn(configs[:, 0:2])
            self.configs = ABMN

    def load_crmod_volt(self, filename):
        """Load a CRMod measurement file (commonly called volt.dat)

        Parameters
        ----------
        filename: string
            path to filename

        Returns
        -------
        list
            list of measurement ids
        """
        with open(filename, 'r') as fid:
            nr_of_configs = int(fid.readline().strip())
            measurements = np.loadtxt(fid)
            if nr_of_configs != measurements.shape[0]:
                raise Exception(
                    'indicated number of measurements does not equal ' +
                    'to actual number of measurements'
                )
        ABMN = self._crmod_to_abmn(measurements[:, 0:2])
        if self.configs is None:
            self.configs = ABMN
        else:
            # check that configs match
            if not np.all(ABMN == self.configs):
                raise Exception(
                    'previously stored configurations do not match new ' +
                    'configurations'
                )

        # add data
        cid_mag = self.add_measurements(measurements[:, 2])
        cid_pha = self.add_measurements(measurements[:, 3])
        return [cid_mag, cid_pha]

    def _get_crmod_abmn(self):
        """return a Nx2 array with the measurement configurations formatted
        CRTomo style
        """
        ABMN = np.vstack((
            self.configs[:, 0] * 1e4 + self.configs[:, 1],
            self.configs[:, 2] * 1e4 + self.configs[:, 3],
        )).T.astype(int)
        return ABMN

    def write_crmod_volt(self, filename, mid):
        """Write the measurements to the output file in the volt.dat file
        format that can be read by CRTomo.

        Parameters
        ----------
        filename: string
            output filename
        mid: int or [int, int]
            measurement ids of magnitude and phase measurements. If only one ID
            is given, then the phase column is filled with zeros

        """
        ABMN = self._get_crmod_abmn()

        if isinstance(mid, (list, tuple)):
            mag_data = self.measurements[mid[0]]
            pha_data = self.measurements[mid[1]]
        else:
            mag_data = self.measurements[mid]
            pha_data = np.zeros(mag_data.shape)

        all_data = np.hstack((
            ABMN,
            mag_data[:, np.newaxis],
            pha_data[:, np.newaxis]
        ))

        with open(filename, 'wb') as fid:
            fid.write(
                bytes(
                    '{0}\n'.format(ABMN.shape[0]),
                    'utf-8',
                )
            )
            np.savetxt(fid, all_data, fmt='%i %i %f %f')

    def write_crmod_config(self, filename):
        """Write the configurations to a configuration file in the CRMod format
        All configurations are merged into one previor to writing to file

        Parameters
        ----------
        filename: string
            absolute or relative path to output filename (usually config.dat)
        """
        ABMN = self._get_crmod_abmn()

        with open(filename, 'wb') as fid:
            fid.write(
                bytes(
                    '{0}\n'.format(ABMN.shape[0]),
                    'utf-8',
                )
            )
            np.savetxt(fid, ABMN.astype(int), fmt='%i %i')

    def gen_dipole_dipole(
            self, skipc, skipv=None, stepc=1, stepv=1, nr_voltage_dipoles=10,
            before_current=False, start_skip=0, N=None):
        """Generate dipole-dipole configurations

        Parameters
        ----------
        skip: int
            number of electrode positions that are skipped between electrodes
            of a given dipole
        step: int
            steplength between subsequent current dipoles. A steplength of 0
            will produce increments by one, i.e., 3-4, 4-5, 5-6 ...
        nr_voltage_dipoles: int
            the number of voltage dipoles to generate for each current
            injection dipole
        skipv: int
            steplength between subsequent voltage dipoles. A steplength of 0
            will produce increments by one, i.e., 3-4, 4-5, 5-6 ...
        before_current: bool, optional
            if set to True, also generate voltage dipoles in front of current
            dipoles.
        N: int, optional
            number of electrodes, must be given if not already known by the
            config instance

        Examples
        --------

        .. plot::
            :include-source:

            import crtomo.configManager as CRconfig
            config = CRconfig.ConfigManager(nr_of_electrodes=10)
            config.gen_dipole_dipole(skipc=2)
            config.plot_pseudodepths()

        """
        if N is None and self.nr_electrodes is None:
            raise Exception('You must provide the number of electrodes')
        elif N is None:
            N = self.nr_electrodes

        # by default, current voltage dipoles have the same size
        if skipv is None:
            skipv = skipc

        configs = []
        # current dipoles
        for a in range(0, N - skipv - skipc - 3, stepc):
            b = a + skipc + 1
            nr = 0
            # potential dipoles before current injection
            if before_current:
                for n in range(a - start_skip - 1, -1, -stepv):
                    nr += 1
                    if nr > nr_voltage_dipoles:
                        continue
                    m = n - skipv - 1
                    if m < 0:
                        continue
                    quadpole = np.array((a, b, m, n)) + 1
                    configs.append(quadpole)

            # potential dipoles after current injection
            nr = 0
            for m in range(b + start_skip + 1, N - skipv - 1, stepv):
                nr += 1
                if nr > nr_voltage_dipoles:
                    continue
                n = m + skipv + 1
                quadpole = np.array((a, b, m, n)) + 1
                configs.append(quadpole)

        configs = np.array(configs)
        # now add to the instance
        if self.configs is None:
            self.configs = configs
        else:
            self.configs = np.vstack((self.configs, configs))
        return configs

    def _pseudodepths_dd_simple(self, configs, spacing=1, grid=None):
        """Given distances between electrodes, compute dipole-dipole pseudo
        depths for the provided configuration

        """
        if grid is None:
            xpositions = (configs - 1) * spacing + 1
        else:
            xpositions = grid.get_electrode_positions()[configs - 1, 0]

        z = np.abs(
            np.max(xpositions, axis=1) - np.min(xpositions, axis=1)
        ) * -0.195
        x = np.mean(xpositions, axis=1)
        return x, z

    def plot_pseudodepths(self, spacing=1, grid=None):
        """Plot pseudodepths for the measurements. If grid is given, then the
        actual electrode positions are used, and the parameter 'spacing' is
        ignored'

        Parameters
        ----------
        spacing: float
            assumed distance between electrodes
        grid: crtomo.grid.crt_grid instance
            grid instance. Used to infer real electrode positions

        Returns
        -------
        figs: matplotlib.figure.Figure instance or list of Figure instances
            if only one type was plotted, then the figure instance is return.
            Otherwise, return a list of figure instances.
        axes: axes object or list of axes ojects
            plot axes

        """
        results = fT.filter(
            self.configs,
            settings={
                'only_types': ['dd', ],
            }
        )
        # loop through all measurement types
        # TODO: will break for non-dipole-dipole measurements
        figs = []
        axes = []
        for key in sorted(results.keys()):
            if key == 'not_sorted':
                continue
            ddc = self.configs[results[key]['indices']]
            px, pz = self._pseudodepths_dd_simple(ddc, spacing, grid)

            fig, ax = plt.subplots(figsize=(15 / 2.54, 5 / 2.54))
            ax.scatter(px, pz, color='k', alpha=0.5)
            ax.set_aspect('equal')
            ax.set_xlabel('x [m]')
            ax.set_ylabel('x [z]')
            fig.tight_layout()
            figs.append(fig)
            axes.append(ax)

        if len(figs) == 1:
            return figs[0], axes[0]
        else:
            return figs, axes

    def plot_pseudosection(self, cid, spacing=1, grid=None):
        """Create a pseudosection plot for a given measurement
        """
        # for now sort data and only plot dipole-dipole
        results = fT.filter(
            self.configs,
            settings={
                'only_types': ['dd', ],
            },
        )

        figs = []
        for key in sorted(results.keys()):
            if key == 'not_sorted':
                continue
            indices = results[key]['indices']
            # dipole-dipole configurations
            ddc = self.configs[indices]
            px, pz = self._pseudodepths_dd_simple(ddc, spacing, grid)

            # take 200 points for the new grid in every direction. Could be
            # adapted to the actual ratio
            xg = np.linspace(px.min(), px.max(), 200)
            zg = np.linspace(pz.min(), pz.max(), 200)

            x, z = np.meshgrid(xg, zg)

            plot_data = self.measurements[cid][indices]
            image = si.griddata((px, pz), plot_data, (x, z), method='linear')

            cmap = mpl.cm.get_cmap('jet_r')

            fig, ax = plt.subplots()

            im = ax.imshow(
                image[::-1],
                extent=(xg.min(), xg.max(), zg.min(), zg.max()),
                interpolation='none',
                aspect='auto',
                # vmin=10,
                # vmax=300,
                cmap=cmap,
            )

            # ax.scatter(px, pz, color='k', alpha=0.5)
            ax.set_aspect('equal')
            fig.tight_layout()
            figs.append((fig, ax, im))

        if len(figs) == 1:
            return figs[0]
        else:
            return figs

    def gen_gradient(self, skip=0, step=1, vskip=0, vstep=1):
        """Generate gradient measurements

        Parameters
        ----------
        skip: int
            distance between current electrodes
        step: int
            steplength between subsequent current dipoles
        vskip: int
            distance between voltage electrodes
        vstep: int
            steplength between subsequent voltage dipoles

        """
        N = self.nr_electrodes
        quadpoles = []
        for a in range(1, N - skip, step):
            b = a + skip + 1
            for m in range(a + 1, b - vskip - 1, vstep):
                n = m + vskip + 1
                quadpoles.append((a, b, m, n))

        configs = np.array(quadpoles)
        if configs.size == 0:
            return None

        self.add_to_configs(configs)
        return configs

    def gen_all_voltages_for_injections(self, injections):
        """
        """
        N = self.nr_electrodes
        all_quadpoles = []
        for idipole in injections:
            # sort current electrodes and convert to array indices
            I = np.sort(idipole) - 1

            # voltage electrodes
            velecs = list(range(1, N + 1))

            # remove current electrodes
            del(velecs[I[1]])
            del(velecs[I[0]])

            # permutate remaining
            voltages = itertools.permutations(velecs, 2)
            for voltage in voltages:
                all_quadpoles.append(
                    (idipole[0], idipole[1], voltage[0], voltage[1])
                )
        configs_unsorted = np.array(all_quadpoles)
        # sort AB and MN
        configs_sorted = np.hstack((
            np.sort(configs_unsorted[:, 0:2], axis=1),
            np.sort(configs_unsorted[:, 2:4], axis=1),
        ))
        configs = self.remove_duplicates(configs_sorted)

        self.add_to_configs(configs)
        return configs

    def gen_all_current_dipoles(self):
        """Generate all possible current dipoles for the given number of
        electrodes (self.nr_electrodes).

        Returns
        -------
        configs: Nx2 numpy.ndarray
            all possible current dipoles A-B
        """
        N = self.nr_electrodes
        celecs = list(range(1, N + 1))
        AB_list = itertools.permutations(celecs, 2)
        AB = np.array([ab for ab in AB_list])
        AB.sort(axis=1)

        # now we need to filter duplicates
        AB = np.unique(
            AB.view(AB.dtype.descr * 2)
        ).view(AB.dtype).reshape(-1, 2)

        return AB

    def remove_duplicates(self, configs=None):
        """remove duplicate entries from 4-point configurations. If no
        configurations are provided, then use self.configs. Unique
        configurations are only returned if configs is not None.

        Parameters
        ----------
        configs: Nx4 numpy.ndarray, optional
            remove duplicates from these configurations instead from
            self.configs.

        Returns
        -------
        configs_unique: Kx4 numpy.ndarray
            unique configurations. Only returned if configs is not None

        """
        if configs is None:
            c = self.configs
        else:
            c = configs
        struct = c.view(c.dtype.descr * 4)
        configs_unique = np.unique(struct).view(c.dtype).reshape(-1, 4)
        if configs is None:
            self.configs = configs_unique
        else:
            return configs_unique

    def gen_schlumberger(self, M, N):
        """generate one Schlumberger sounding configuration, that is, one set
        of configurations for one potential dipole M-N.

        Parameters
        ----------
        M: int
            electrode number for the first potential electrode
        N: int
            electrode number for the second potential electrode

        Returns
        -------
        configs: Kx4 numpy.ndarray
            array holding the configurations

        """
        a = np.abs(M - N)
        nr_of_steps_left = int(min(M, N) - 1 / a)
        nr_of_steps_right = int((self.nr_electrodes - max(M, N)) / a)
        configs = []
        for i in range(0, min(nr_of_steps_left, nr_of_steps_right)):
            A = min(M, N) - (i + 1) * a
            B = max(M, N) + (i + 1) * a
            configs.append(
                (A, B, M, N)
            )
        configs = np.array(configs)
        self.add_to_configs(configs)
        return configs

    def gen_wenner(self, a):
        """generate Wenner measurement configurations

        Parameters
        ----------
        a: int
            distance (in electrodes) between subsequent electrodes of each
            four-point configuration.

        Returns
        -------
        configs: Kx4 numpy.ndarray
            array holding the configurations
        """
        configs = []
        for i in range(1, self.nr_electrodes - 3 * a + 1):
            configs.append(
                (i, i + a, i + 2 * a, i + 3 * a),
            )
        configs = np.array(configs)
        self.add_to_configs(configs)
        return configs

    def add_to_configs(self, configs):
        """Add one or more measurement configurations to the stored
        configurations

        Parameters
        ----------
        configs: list or numpy.ndarray
            list or array of configurations

        Returns
        -------
        configs: Kx4 numpy.ndarray
            array holding all configurations of this instance
        """
        if len(configs) == 0:
            return None

        if self.configs is None:
            self.configs = configs
        else:
            configs = np.atleast_2d(configs)
            self.configs = np.vstack((self.configs, configs))
        return self.configs

    def split_into_normal_and_reciprocal(self, pad=False):
        """Split the stored configurations into normal and reciprocal
        measurements

        ** *Rule 1: the normal configuration contains the smallest electrode
        number of the four involved electrodes in the current dipole* **

        Parameters
        ----------
        pad: bool
            if True, add numpy.nan values to the reciprocals for non-existent
            measuremnts

        Returns
        -------
        normal: numpy.ndarray
            Nnx4 array. If pad is True, then Nn == N (total number of
            unique measurements). Otherwise Nn is the number of normal
            measurements.
        reciprocal: numpy.ndarray
            Nrx4 array. If pad is True, then Nr == N (total number of
            unique measurements). Otherwise Nr is the number of reciprocal
            measurements.

        """
        # for simplicity, we create an array where AB and MN are sorted
        configs = np.hstack((
            np.sort(self.configs[:, 0:2], axis=1),
            np.sort(self.configs[:, 2:4], axis=1)
        ))

        ab_min = configs[:, 0]
        mn_min = configs[:, 2]

        # rule 1
        indices_normal = np.where(ab_min < mn_min)[0]

        # now look for reciprocals
        indices_used = []
        normal = []
        reciprocal = []
        duplicates = []
        for index in indices_normal:
            indices_used.append(index)
            normal.append(self.configs[index, :])

            # look for reciprocal configuration
            index_rec = np.where(
                # A == M, B == N, M == A, N == B
                (configs[:, 0] == configs[index, 2]) &
                (configs[:, 1] == configs[index, 3]) &
                (configs[:, 2] == configs[index, 0]) &
                (configs[:, 3] == configs[index, 1])
            )[0]
            if len(index_rec) == 0 and pad:
                reciprocal.append(np.ones(4) * np.nan)
            elif len(index_rec) == 1:
                reciprocal.append(self.configs[index_rec[0], :])
                indices_used.append(index_rec[0])
            elif len(index_rec > 1):
                # take the first one
                reciprocal.append(self.configs[index_rec[0], :])
                duplicates += list(index_rec[1:])
                indices_used += list(index_rec)

        # now determine all reciprocal-only parameters
        set_all_indices = set(list(range(0, configs.shape[0])))
        set_used_indices = set(indices_used)
        reciprocal_only_indices = set_all_indices - set_used_indices
        for index in reciprocal_only_indices:
            if pad:
                normal.append(np.ones(4) * np.nan)
            reciprocal.append(self.configs[index, :])

        normals = np.array(normal)
        reciprocals = np.array(reciprocal)

        return normals, reciprocals
