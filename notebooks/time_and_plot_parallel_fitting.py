import os
# Ensure worker processes inherit the warning filter; set before other imports.
os.environ['PYTHONWARNINGS'] = 'ignore'

import numpy as np
import timeit

from astropy import units as u
from astropy.modeling import models
from astropy.wcs import WCS
from specutils.spectra import Spectrum

from jdaviz.configs.default.plugins.model_fitting import fitting_backend as fb

import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go

import glob

def build_spectrum(sigma=0.1, spectrum_size=50):
    g1 = models.Gaussian1D(1, 4.6, 0.2)
    g2 = models.Gaussian1D(2.5, 5.5, 0.1)
    g3 = models.Gaussian1D(-1.7, 8.2, 0.1)

    x = np.linspace(0, 10, spectrum_size)
    y = g1(x) + g2(x) + g3(x)

    noise = np.random.normal(4., sigma, x.shape)

    return x, y + noise


def test_cube_fitting_backend(n_cpu,
                              spectrum_size=50,
                              parallel_framework='multiprocessing'):
    np.random.seed(42)

    SIGMA = 0.1  # noise in data
    TOL = 0.4  # test tolerance
    IMAGE_SIZE_X = 15
    IMAGE_SIZE_Y = 14

    # Flux cube oriented as in JWST data. To build a Spectrum
    # instance with this, one need to transpose it so the spectral
    # axis direction corresponds to the last index.
    flux_cube = np.zeros((spectrum_size, IMAGE_SIZE_X, IMAGE_SIZE_Y))

    # Generate list of all spaxels to be fitted
    _spx = [[(x, y) for x in range(IMAGE_SIZE_X)] for y in range(IMAGE_SIZE_Y)]
    spaxels = [item for sublist in _spx for item in sublist]

    # Fill cube spaxels with spectra that differ from
    # each other only by their noise component.
    x, _ = build_spectrum(spectrum_size=spectrum_size)
    for spx in spaxels:
        flux_cube[:, spx[0], spx[1]] = build_spectrum(sigma=SIGMA, spectrum_size=spectrum_size)[1]

    # Transpose so it can be packed in a Spectrum instance.
    flux_cube = flux_cube.transpose(1, 2, 0)  # (15, 14, 200)
    cube_wcs = WCS({
        'WCSAXES': 3, 'RADESYS': 'ICRS', 'EQUINOX': 2000.0,
        'CRPIX3': 38.0, 'CRPIX2': 38.0, 'CRPIX1': 1.0,
        'CRVAL3': 205.4384, 'CRVAL2': 27.004754, 'CRVAL1': 0.0,
        'CDELT3': 0.01, 'CDELT2': 0.01, 'CDELT1': 0.05,
        'CUNIT3': 'deg', 'CUNIT2': 'deg', 'CUNIT1': 'um',
        'CTYPE3': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE1': 'WAVE'})

    # Mask part of the spectral axis to later ensure that it gets propagated through:
    mask = np.zeros_like(flux_cube).astype(bool)
    mask[..., :spectrum_size // 10] = True

    spectrum = Spectrum(flux=flux_cube*u.Jy, wcs=cube_wcs, mask=mask)

    # Initial model for fit.
    g1f = models.Gaussian1D(0.7*u.Jy, 4.65*u.um, 0.3*u.um, name='g1')
    g2f = models.Gaussian1D(2.0*u.Jy, 5.55*u.um, 0.3*u.um, name='g2')
    g3f = models.Gaussian1D(-2.*u.Jy, 8.15*u.um, 0.2*u.um, name='g3')
    zero_level = models.Const1D(1.*u.Jy, name='const1d')

    model_list = [g1f, g2f, g3f, zero_level]
    expression = "g1 + g2 + g3 + const1d"

    _, _ = fb.fit_model_to_spectrum(
        spectrum, model_list, expression, n_cpu=n_cpu, parallel_framework=parallel_framework)


def run_with_framework(n_cpu, spectrum_size, framework):
    test_cube_fitting_backend(n_cpu=n_cpu,
                              spectrum_size=spectrum_size,
                              parallel_framework=framework)


def _write_image_with_fallback(fig, out_html, out_jpg):
    """Write interactive HTML and a JPG image with fallbacks.

    Tries Plotly+kaleido first; if that fails falls back to saving a
    static image via matplotlib (for heatmaps) or logs the failure.
    """
    # Always write interactive HTML
    try:
        fig.write_html(out_html)
    except Exception:
        # If even HTML writing fails, still attempt image export below
        pass

    # Try kaleido for JPG export
    try:
        pio.write_image(fig, out_jpg, format='jpg')
        print(f'Wrote JPG via kaleido: {out_jpg}')
        return
    except Exception:
        print('plotly.kaleido not available or failed; falling back to matplotlib')

    # Fallback for heatmaps/surface-like figures: render via matplotlib if possible
    try:
        import matplotlib.pyplot as plt
        # Try to extract data for simple cases (heatmap in a single trace)
        if hasattr(fig, 'data') and len(fig.data) and hasattr(fig.data[0], 'z'):
            z = fig.data[0].z
            x = getattr(fig.data[0], 'x', None)
            y = getattr(fig.data[0], 'y', None)
            plt.figure(figsize=(8, 6))
            plt.imshow(z, aspect='auto', origin='lower')
            if x is not None:
                plt.xticks(ticks=np.arange(len(x)), labels=list(x))
            if y is not None:
                plt.yticks(ticks=np.arange(len(y)), labels=list(y))
            plt.colorbar(label='avg_time (s)')
            plt.title(fig.layout.title.text if fig.layout and fig.layout.title else '')
            plt.xlabel(getattr(fig.layout.scene.xaxis, 'title', {}).get('text', 'n_cpu'))
            plt.ylabel(getattr(fig.layout.scene.yaxis, 'title', {}).get('text', 'spectrum_size'))
            plt.tight_layout()
            plt.savefig(out_jpg, dpi=150)
            plt.close()
            print(f'Wrote JPG via matplotlib fallback: {out_jpg}')
            return
    except Exception:
        pass

    print(f'Unable to write JPG for {out_html}; interactive HTML was written if possible.')


def plot_heatmap_for_framework(df, framework, out_dir=None):
    """Create and save a heatmap (spectrum_size vs n_cpu) for one framework.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain columns 'spectrum_size', 'n_cpu', 'framework', 'avg_time'.
    framework : str
        Which framework to plot.
    out_dir : str or None
        Directory to write outputs; defaults to home directory.
    """
    if out_dir is None:
        out_dir = os.path.expanduser('~')

    sub = df[df.framework == framework]

    pivot = sub.pivot_table(index='spectrum_size', columns='n_cpu', values='avg_time', aggfunc='mean')
    pivot = pivot.sort_index().sort_index(axis=1)

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=list(pivot.columns.astype(str)),
        y=list(pivot.index.astype(str)),
        colorscale='Viridis',
        colorbar=dict(title='avg_time (s)')
    ))

    spectrum_range = f'{pivot.index.min()}-{pivot.index.max()}'
    fig.update_layout(
        title=f'Heatmap: {framework}',
        xaxis_title='n_cpu',
        yaxis_title='spectrum_size'
    )

    out_html = os.path.join(out_dir, f'heatmap_{framework}_{spectrum_range}.html')
    out_jpg = os.path.join(out_dir, f'heatmap_{framework}_{spectrum_range}.jpg')
    _write_image_with_fallback(fig, out_html, out_jpg)


def plot_animated_lines(df, out_dir=None):
    """Create an animated 2D line plot: avg_time vs n_cpu animated by spectrum_size.

    Writes interactive HTML and per-frame JPGs (kaleido preferred,
    matplotlib fallback). Filenames include the actual spectrum_size
    range present in the DataFrame when available.
    """
    if out_dir is None:
        out_dir = os.path.expanduser('~')

    df2 = df.copy()

    # Convert to string for animation frames to have readable labels
    df2['spectrum_size_str'] = df2['spectrum_size'].astype(str)

    spectrum_range = f'{df2.spectrum_size.min()}-{df2.spectrum_size.max()}'

    fig = px.line(
        df2,
        x='n_cpu',
        y='avg_time',
        color='framework',
        markers=True,
        animation_frame='spectrum_size_str',
        title=f'Animated — SPECTRUM_SIZES {df2.spectrum_size.min()}..{df2.spectrum_size.max()}'
    )
    fig.update_layout(xaxis_title='n_cpu', yaxis_title='avg_time (s)')

    out_html = os.path.join(out_dir, f'animated_lines_{spectrum_range}.html')

    # Save interactive HTML for the full animation
    try:
        fig.write_html(out_html)
        print(f'Wrote animated HTML to: {out_html}')
    except Exception:
        print('Failed to write animated HTML; continuing to write frame images.')

    # Save each animation frame as an individual JPG (kaleido preferred,
    # matplotlib fallback).
    frames = getattr(fig, 'frames', None) or []
    if frames and len(frames) > 0:
        for idx, frame in enumerate(frames):
            frame_name = getattr(frame, 'name', None) or str(idx)
            out_jpg = os.path.join(
                out_dir,
                f'comparison_{spectrum_range}_{frame_name}.jpg'
            )

            # Try kaleido snapshot first
            try:
                snap = go.Figure(data=frame.data, layout=fig.layout)
                pio.write_image(snap, out_jpg, format='jpg')
                print(f'Wrote frame JPG via kaleido: {out_jpg}')
                continue
            except Exception:
                # Fall back to matplotlib
                pass

            try:
                import matplotlib.pyplot as plt
                plt.figure(figsize=(8, 6))
                for tr in frame.data:
                    x = getattr(tr, 'x', None)
                    y = getattr(tr, 'y', None)
                    lbl = getattr(tr, 'name', None)
                    if x is None or y is None:
                        continue
                    plt.plot(list(x), list(y), marker='o', label=lbl)
                if any(getattr(t, 'name', None) for t in frame.data):
                    plt.legend()
                plt.xlabel('n_cpu')
                plt.ylabel('avg_time (s)')
                plt.title(f'Spectrum Size {frame_name}')
                plt.tight_layout()
                plt.savefig(out_jpg, dpi=150)
                plt.close()
                print(f'Wrote frame JPG via matplotlib fallback: {out_jpg}')
            except Exception:
                print(f'Could not export frame {frame_name} to JPG; skipping.')
    else:
        # No frames: try to export the single-state figure as JPG
        out_jpg = os.path.join(out_dir, f'comparison_{spectrum_range}.jpg')
        try:
            pio.write_image(fig, out_jpg, format='jpg')
            print(f'Wrote static JPG via kaleido: {out_jpg}')
        except Exception:
            try:
                import matplotlib.pyplot as plt
                plt.figure(figsize=(8, 6))
                for tr in fig.data:
                    x = getattr(tr, 'x', None)
                    y = getattr(tr, 'y', None)
                    lbl = getattr(tr, 'name', None)
                    if x is None or y is None:
                        continue
                    plt.plot(list(x), list(y), marker='o', label=lbl)
                if any(getattr(t, 'name', None) for t in fig.data):
                    plt.legend()
                plt.xlabel('n_cpu')
                plt.ylabel('avg_time (s)')
                plt.title(fig.layout.title.text if fig.layout and fig.layout.title else '')
                plt.tight_layout()
                plt.savefig(out_jpg, dpi=150)
                plt.close()
                print(f'Wrote static JPG via matplotlib fallback: {out_jpg}')
            except Exception:
                print('Could not export animated figure to JPG; HTML may be available.')


def save_all_plots(df, out_dir=None):
    """Save heatmaps (one per framework) and an animated 2D-line plot.

    This helper avoids running plotting on import and allows callers to
    control when and where plots are written.
    """
    if out_dir is None:
        out_dir = os.path.expanduser('~')

    for fw in sorted(set(df.framework)):
        plot_heatmap_for_framework(df, fw, out_dir=out_dir)

    plot_animated_lines(df, out_dir=out_dir)


def load_and_concat_pickles(paths=None, pickle_dir=None, pattern='parallel_benchmark_df_*.pkl'):
    """
    Load and concatenate multiple pandas pickles into a single DataFrame.

    Parameters
    ----------
    paths : str or list of str or None
        Specific file path or list of paths to load. If ``None``, the
        function will search ``pickle_dir`` for files matching ``pattern``.
    pickle_dir : str or None
        Directory to search for pickle files when ``paths`` is ``None``.
        Defaults to ``~/benchmark_parallel``.
    pattern : str
        Glob pattern to search for pickle files in ``pickle_dir``.

    Returns
    -------
    df : pandas.DataFrame or None
        Concatenated DataFrame, or ``None`` if no files were found/loaded.
    """
    if paths is None:
        if pickle_dir is None:
            pickle_dir = os.path.expanduser('~/benchmark_parallel')
        search_path = os.path.join(pickle_dir, pattern)
        files = sorted(glob.glob(search_path))
    else:
        if isinstance(paths, str):
            files = [paths]
        else:
            files = list(paths)

    if not files:
        print(f'No pickle files found using pattern: {paths or search_path}')
        return None

    dfs = []
    for p in files:
        try:
            dfp = pd.read_pickle(p)
            dfs.append(dfp)
            print(f'Loaded pickle: {p} -> {len(dfp)} rows')
        except Exception as err:
            print(f'Could not read pickle file {p}: {err}')

    if not dfs:
        print('No DataFrames were loaded from the provided pickles.')
        return None

    try:
        df_all = pd.concat(dfs, ignore_index=True, sort=False)
    except Exception as err:
        print(f'Could not concatenate DataFrames: {err}')
        return None

    return df_all


def load_pickles_and_plot(paths=None, pickle_dir=None, pattern='parallel_benchmark_df_*.pkl', out_dir=None):
    """
    Convenience helper: load multiple pickles, write a combined CSV, and
    create the heatmaps and animated plots via the existing plotting
    helpers in this module.

    Parameters
    ----------
    paths : str or list of str or None
        Specific pickle path(s) to load. If ``None``, ``pickle_dir`` and
        ``pattern`` are used to discover files.
    pickle_dir : str or None
        Directory to search for pickles when ``paths`` is ``None``.
    pattern : str
        Glob pattern to use when discovering pickles.
    out_dir : str or None
        Directory to write combined CSV and plot outputs. Defaults to
        ``~/benchmark_parallel``.

    Returns
    -------
    df : pandas.DataFrame or None
        The combined DataFrame, or ``None`` if loading failed.
    """
    df = load_and_concat_pickles(paths=paths, pickle_dir=pickle_dir, pattern=pattern)
    if df is None:
        return None

    if out_dir is None:
        out_dir = os.path.expanduser('~/benchmark_parallel')
    os.makedirs(out_dir, exist_ok=True)

    try:
        ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        combined_csv = os.path.join(out_dir, f'parallel_benchmark_combined_{ts}.csv')
        df.to_csv(combined_csv, index=False)
        print(f'Wrote combined CSV to: {combined_csv}')
    except Exception as err:
        print(f'Failed to write combined CSV: {err}')

    try:
        save_all_plots(df, out_dir=out_dir)
    except Exception as err:
        print(f'Plotting failed: {err}')

    return df


if __name__ == '__main__':
    repeat = 10  # Number of times to repeat each timing
    n_cpu_list = [1, 2, 4, 8, 12, 16]
    spectrum_size = [50, 100, 200, 500, 1000]  # Different spectrum sizes to test
    frameworks = ['futures', 'joblib', 'multiprocessing']
    records = []
    out_dir_default = os.path.expanduser('~')

    # Ensure output directory exists
    benchmark_dir = os.path.join(out_dir_default, 'benchmark_parallel')
    os.makedirs(benchmark_dir, exist_ok=True)

    for ss in spectrum_size:
        print(f'Spectrum size: {ss}')
        for n_cpu in n_cpu_list:
            print(f'Number of CPUs: {n_cpu}')
            for framework in frameworks:
                # Use a small number of repeats; timeit.number=repeat
                time = timeit.timeit(lambda: run_with_framework(n_cpu, ss, framework),
                                     number=repeat)

                # Compute average time per run
                avg = time / float(repeat)

                records.append({'framework': framework, 'n_cpu': n_cpu, 'avg_time': avg,
                                'spectrum_size': ss})

                print(f'Framework: {framework}')
                print(f'Total time for {repeat} runs: {time:.6f} s')
                print(f'Average time: {avg:.6f} s')
                print()
            print('---')
        print('----------------')

        # At the end of this spectrum-size iteration, save the results for
        # just this spectrum size as a pandas pickle so each size's raw
        # results are preserved independently.
        try:
            # Build a DataFrame only for this spectrum size
            df_ss = pd.DataFrame([r for r in records if r.get('spectrum_size') == ss])
            ss_path = os.path.join(benchmark_dir, f'parallel_benchmark_df_{ss}.pkl')
            df_ss.to_pickle(ss_path)
            print(f'Wrote per-spectrum-size DataFrame to: {ss_path}')
        except Exception as _err:
            msg = f'Could not write per-spectrum-size pickle for size {ss}: {_err}'
            print(msg)

    # Build DataFrame and plot
    df = pd.DataFrame(records)

    # Save the raw benchmark DataFrame as a CSV in the user's home
    # directory so results can be consumed easily by other tools.
    try:
        ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
        df_csv_path = os.path.join(benchmark_dir, f'parallel_benchmark_{ts}.csv')
        df.to_csv(df_csv_path, index=False)
        print(f'Wrote benchmark DataFrame CSV to: {df_csv_path}')
    except Exception as _err:
        msg = f'Could not write benchmark DataFrame to CSV: {_err}'
        print(msg)

    try:
        # Use save_all_plots which calls plot_animated_lines (which now
        # also writes the summary).
        save_all_plots(df, out_dir=benchmark_dir)
    except NameError:
        # df not present — nothing to do.
        pass
    except Exception as err:
        msg = f'save_all_plots failed: {err}'
        print(msg)
