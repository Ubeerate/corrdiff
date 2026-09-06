import os
import argparse
import xarray as xr
import numpy as np
import matplotlib
# Use non-interactive Agg backend to avoid GUI/Qt issues when saving figures
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from PIL import Image
from scipy.interpolate import RegularGridInterpolator

# Optional cartopy
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    CARTOPY_AVAILABLE = True
except Exception:
    CARTOPY_AVAILABLE = False

# NOTE: some Windows / Cartopy builds trigger C-level faults in this environment.
# Disable Cartopy rendering by default to ensure the script runs. Set to True
# manually if your env's Cartopy is stable.
CARTOPY_AVAILABLE = False


class SuperResolutionWind:
    """Super-resolution helper for u10/v10 wind fields on a regular lat/lon grid."""

    def __init__(self, input_file, sr_factor=2, time_index=0):
        self.input_file = input_file
        self.sr_factor = int(sr_factor)
        self.time_index = int(time_index)
        self.ds = None
        self.sr_ds = None
        self.has_time = False
        self.load_data()

    def load_data(self):
        print(f"📖 Loading {self.input_file}...")
        self.ds = xr.open_dataset(self.input_file)
        # Expect variables `u10` and `v10` and coords `latitude`, `longitude`
        if self.ds['u10'].ndim == 3:
            self.has_time = True
            time_dim = self.ds['u10'].dims[0]
            try:
                ntime = len(self.ds[time_dim])
            except Exception:
                ntime = self.ds['u10'].shape[0]
            print(f"✅ Original resolution: {len(self.ds.latitude)} × {len(self.ds.longitude)} (time: {ntime})")
            print(f"🔧 using time_index = {self.time_index}")
        else:
            self.has_time = False
            print(f"✅ Original resolution: {len(self.ds.latitude)} × {len(self.ds.longitude)}")

    def super_resolve(self):
        """Create a higher-resolution dataset using interpolation."""
        print(f"\n🔄 Running {self.sr_factor}x super-resolution...")
        lat = self.ds.latitude.values
        lon = self.ds.longitude.values

        if self.has_time and self.ds['u10'].ndim == 3:
            u10 = self.ds.u10[self.time_index].values
            v10 = self.ds.v10[self.time_index].values
        else:
            u10 = self.ds.u10.values
            v10 = self.ds.v10.values

        # build sr grid (keep endpoints)
        sr_lat = np.linspace(lat.min(), lat.max(), len(lat) * self.sr_factor - (self.sr_factor - 1))
        sr_lon = np.linspace(lon.min(), lon.max(), len(lon) * self.sr_factor - (self.sr_factor - 1))
        sr_lat_grid, sr_lon_grid = np.meshgrid(sr_lat, sr_lon, indexing='ij')

        # Interpolate using RegularGridInterpolator (robust for regular grids)
        interp_u = RegularGridInterpolator((lat, lon), u10, bounds_error=False, fill_value=None)
        interp_v = RegularGridInterpolator((lat, lon), v10, bounds_error=False, fill_value=None)
        pts = np.column_stack([sr_lat_grid.ravel(), sr_lon_grid.ravel()])
        u10_sr = interp_u(pts).reshape(sr_lat_grid.shape)
        v10_sr = interp_v(pts).reshape(sr_lat_grid.shape)

        # Build xarray Dataset for SR fields
        self.sr_ds = xr.Dataset(
            {
                'u10': (['latitude', 'longitude'], u10_sr),
                'v10': (['latitude', 'longitude'], v10_sr),
            },
            coords={'latitude': sr_lat, 'longitude': sr_lon}
        )

        print(f"✅ New resolution: {len(sr_lat)} × {len(sr_lon)}")
        return self.sr_ds

    def get_wind_speed_and_direction(self, ds=None):
        if ds is None:
            ds = self.sr_ds if self.sr_ds is not None else self.ds
        if ds['u10'].ndim == 3:
            u10 = ds['u10'][self.time_index].values
            v10 = ds['v10'][self.time_index].values
        else:
            u10 = ds['u10'].values
            v10 = ds['v10'].values
        wind_speed = np.sqrt(u10 ** 2 + v10 ** 2)
        wind_direction = (np.degrees(np.arctan2(u10, v10)) % 360)
        return wind_speed, wind_direction, u10, v10

    def plot_wind_detail(self, output_file):
        if self.sr_ds is None:
            print('⚠️ Run super_resolve() first')
            return
        wind_speed, wind_direction, u10, v10 = self.get_wind_speed_and_direction()

        def to_rgba(arr, cmap_name='RdYlBu_r'):
            cmap = plt.get_cmap(cmap_name)
            a = np.array(arr, dtype=float)
            vmin = np.nanmin(a)
            vmax = np.nanmax(a)
            if vmax == vmin:
                vmax = vmin + 1e-6
            normed = (a - vmin) / (vmax - vmin)
            rgba = cmap(normed)
            rgba8 = (rgba * 255).astype(np.uint8)
            return rgba8

        img1 = to_rgba(wind_speed, 'RdYlBu_r')
        img2 = to_rgba(u10, 'RdBu_r')
        img3 = to_rgba(v10, 'RdBu_r')
        img4 = to_rgba(wind_direction, 'hsv')

        h, w, _ = img1.shape
        mosaic = Image.new('RGBA', (w * 2, h * 2))
        mosaic.paste(Image.fromarray(img1), (0, 0))
        mosaic.paste(Image.fromarray(img2), (w, 0))
        mosaic.paste(Image.fromarray(img3), (0, h))
        mosaic.paste(Image.fromarray(img4), (w, h))
        mosaic.save(output_file)
        print(f"✅ Saved: {output_file}")

    def plot_comparison(self, output_file):
        if self.sr_ds is None:
            print('⚠️ Run super_resolve() first')
            return
        if self.ds['u10'].ndim == 3:
            u10_orig = self.ds['u10'][0].values
            v10_orig = self.ds['v10'][0].values
        else:
            u10_orig = self.ds['u10'].values
            v10_orig = self.ds['v10'].values
        wind_orig = np.sqrt(u10_orig ** 2 + v10_orig ** 2)
        wind_sr, _, u10_sr, v10_sr = self.get_wind_speed_and_direction()

        def to_rgba(arr, cmap_name='RdYlBu_r'):
            cmap = plt.get_cmap(cmap_name)
            a = np.array(arr, dtype=float)
            vmin = np.nanmin(a)
            vmax = np.nanmax(a)
            if vmax == vmin:
                vmax = vmin + 1e-6
            normed = (a - vmin) / (vmax - vmin)
            rgba = cmap(normed)
            rgba8 = (rgba * 255).astype(np.uint8)
            return rgba8

        img1 = to_rgba(wind_orig)
        img2 = to_rgba(wind_sr)
        h, w, _ = img1.shape
        mosaic = Image.new('RGBA', (w * 2, h))
        mosaic.paste(Image.fromarray(img1), (0, 0))
        mosaic.paste(Image.fromarray(img2), (w, 0))
        mosaic.save(output_file)
        print(f"✅ Saved: {output_file}")
        plt.close()

    def print_statistics(self):
        wind_speed, wind_direction, u10, v10 = self.get_wind_speed_and_direction()
        print('\n' + '=' * 40)
        print('Wind statistics')
        print(f"max: {wind_speed.max():.2f} m/s, mean: {wind_speed.mean():.2f} m/s")
        print('=' * 40)


def main():
    parser = argparse.ArgumentParser(description='Super-resolution wind tool')
    parser.add_argument('--sr-factor', type=int, default=2, choices=[1, 2, 3, 4])
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--input', type=str, default='taiwan_test_data.nc')
    parser.add_argument('--time-index', type=int, default=0)
    parser.add_argument('--out-dir', type=str, default='CorrDiff/outputs')

    args = parser.parse_args()
    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    sr = SuperResolutionWind(input_file=args.input, sr_factor=args.sr_factor, time_index=args.time_index)
    sr.super_resolve()
    detail_path = os.path.join(out_dir, f'wind_detail_sr{args.sr_factor}x.png')
    sr.plot_wind_detail(detail_path)
    if args.compare:
        compare_path = os.path.join(out_dir, f'wind_comparison_{args.sr_factor}x.png')
        sr.plot_comparison(compare_path)
    sr.print_statistics()


if __name__ == '__main__':
    main()
